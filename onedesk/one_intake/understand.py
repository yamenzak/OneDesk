"""Stage 3 of Intake: what a document is, who it is about, and what it asks.

Deterministic first. An e-invoice, a bank statement, a contact card and an
invitation already say all of it as data, and are understood with no model.
Everything else is looked at once, cheaply, to tell junk from something to
read (the first look), and then read once into a fixed shape (the reading).
Every fact the model returns is checked against the document's own text
(facts.py) before it is kept, and every party is matched to a record through
the Identifier registry (identity.py).

A model is asked only where somebody switched OneAI on, and never about
history: what was there before the switch is read for its words only.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, now_datetime, today

from onedesk.one_intake import facts, identity
from onedesk.one_intake import identifiers as ids

LOOK = "intake_look"
READ = "intake_read"

#: What the model is shown of a long document. The first pages of a letter
#: say what it is; a forty-page contract's terms are for search, not for this.
MOST_TEXT = 40_000
MOST_LOOK = 1500

VERDICTS = ("Spam", "Phishing", "Advertising", "Newsletter", "Notification", "Information", "Action")
READ_IN_FULL = ("Information", "Action")
KINDS = (
	"Invoice", "Credit Note", "Receipt", "Reminder", "Tax Assessment", "Contract", "Offer", "Order",
	"Order Confirmation", "Delivery Note", "Payment Advice", "Bank Statement", "Payslip", "Sick Note",
	"Medical Report", "Identity Document", "Certificate", "CV", "Appointment", "Letter From an Authority",
	"Notice of Change", "Contact Card", "Inquiry", "Resignation", "Letter", "Other",
)  # fmt: skip
ROLES = ("Sender", "Recipient", "Holder", "Patient", "Employee", "Paid To", "Mentioned")
DATES = ("Due", "Deadline", "Appointment", "Valid From", "Valid Until", "Period Start", "Period End", "Service", "Other")
ASKS = ("Pay", "Sign", "Reply", "Attend", "Send", "Cancel", "Decide", "Other")
REFERENCES = ("Invoice", "Order", "Customer", "Contract", "Case", "Tax", "Policy", "Other")
PAID = {"transfer": "Transfer", "direct debit": "Direct Debit", "already paid": "Already Paid"}

#: How sensitive a kind is at least, whatever the model said.
SENSITIVE = {"Payslip": "Pay", "Sick Note": "Medical", "Medical Report": "Medical", "Identity Document": "Personal", "CV": "Personal", "Resignation": "Personal"}
LEVELS = ("Ordinary", "Personal", "Legal", "Pay", "Medical")

#: What a line was spent on, for Spending.
CATEGORIES = ("Groceries", "Fuel", "Pharmacy", "Clothing", "Household", "Children", "Insurance", "Utilities", "Dining", "Travel", "Office", "Other")


def run(name: str) -> None:
	"""Understand one Reading that has been read."""
	reading = frappe.get_doc("Reading", name)
	# Read, or waiting at understanding for credits or a passing failure.
	if reading.state not in ("Read", "Waiting for Credits", "Queued") or not reading.read_on:
		return
	if not (reading.text or reading.structured):
		return
	structured = json.loads(reading.structured) if reading.structured else {}
	said = known(structured)
	dropped: list[str] = []
	if said is None:
		if not reading.on_behalf_of or reading.history:
			return
		try:
			reading.verdict = look(reading, structured)
			if reading.verdict not in READ_IN_FULL:
				_done(reading)
				return
			said, dropped = facts.check(ask(reading, structured), _checked_text(reading, structured), identity.country())
		except Exception as raised:
			from onedesk.one_intake import pipeline

			pipeline._failed(reading, raised)
			return
	apply(reading, said, dropped, structured)
	_done(reading)


def _checked_text(reading, structured: dict) -> str:
	"""What a reading is checked against: the document, and for a message its
	headers too, which the model was shown and which say who wrote."""
	mail = structured.get("forwarded") or structured.get("mail") or {}
	head = " ".join(str(mail.get(key) or "") for key in ("from_name", "from_email", "to", "cc", "subject", "date")) if mail else ""
	return f"{head}\n{reading.text or ''}"


def _done(reading) -> None:
	"""Understood: placed in its matter, saved, and acted on now or once the
	matter has been quiet (matters.py)."""
	from onedesk.one_intake import matters

	reading.state = "Understood"
	reading.understood_on = now_datetime()
	try:
		matters.place(reading)
	except Exception:
		frappe.log_error(title=f"Intake could not place {reading.name}")
		reading.matter, reading.change, reading.act_after = reading.matter or reading.name, reading.change or "New", now_datetime()
	reading.flags.ignore_permissions = True
	reading.save()
	frappe.db.commit()
	if reading.act_after and reading.act_after <= now_datetime():
		matters.act_now(reading.name)


# ------------------------------------------------------------------ without a model


def known(structured: dict) -> dict | None:
	"""A document that is already data, as a reading. Pure."""
	if structured.get("invoice"):
		return from_invoice(structured["invoice"])
	if structured.get("statement"):
		statement = structured["statement"]
		dates = [{"date": statement.get(key), "what": what, "found": 1} for key, what in (("from", "Period Start"), ("to", "Period End")) if statement.get(key)]
		return {"kind": "Bank Statement", "title": "", "dates": dates, "money": {"currency": statement.get("currency")}, "confidence": 1}
	if structured.get("events"):
		event = structured["events"][0]
		return {
			"kind": "Appointment",
			"title": event.get("summary") or "",
			"dates": [{"date": (event.get("starts") or "")[:10], "what": "Appointment", "about": event.get("summary"), "found": 1}],
			"asks": [{"what": "Attend", "detail": event.get("location") or event.get("summary"), "by": (event.get("starts") or "")[:10]}],
			"parties": [{"role": "Sender", "email": event.get("organiser")}] if event.get("organiser") else [],
			"confidence": 1,
		}
	if structured.get("cards"):
		return {
			"kind": "Contact Card",
			"title": structured["cards"][0].get("name") or "",
			"parties": [
				{
					"role": "Sender",
					"name": card.get("organisation") or card.get("name"),
					"person_name": card.get("name"),
					"person": bool(card.get("name")) and not card.get("organisation"),
					"email": (card.get("emails") or [None])[0],
					"phone": (card.get("phones") or [None])[0],
					"website": (card.get("websites") or [None])[0],
				}
				for card in structured["cards"]
			],
			"confidence": 1,
		}
	return None


def from_invoice(invoice: dict) -> dict:
	"""An e-invoice as a reading, field by field. Pure."""
	totals, pay, seller, buyer = (invoice.get(key) or {} for key in ("totals", "payment", "seller", "buyer"))
	payable = totals.get("payable") if totals.get("payable") is not None else totals.get("gross")
	means = pay.get("means")
	dates = [{"date": invoice["due"], "what": "Due", "found": 1}] if invoice.get("due") else []
	if invoice.get("period"):
		start, end = invoice["period"]
		dates += [{"date": value, "what": what, "found": 1} for value, what in ((start, "Period Start"), (end, "Period End")) if value]
	return {
		"kind": "Credit Note" if invoice.get("kind") == "credit note" else "Invoice",
		"title": f"{seller.get('name') or ''} {invoice.get('number') or ''}".strip(),
		"number": invoice.get("number"),
		"issued": invoice.get("issued"),
		"dates": dates,
		"money": {
			"currency": invoice.get("currency"),
			"net": totals.get("net"),
			"tax": totals.get("tax"),
			"gross": payable,
			"iban": pay.get("iban"),
			"reference": pay.get("reference"),
			"paid_how": means,
		},
		"lines": [
			{"text": line.get("name"), "qty": line.get("qty"), "unit_price": line.get("price"), "amount": line.get("amount"), "tax_rate": line.get("tax_rate"), "code": line.get("code")}
			for line in invoice.get("lines") or []
		],
		"references": [one for one in ({"kind": "Order", "value": invoice.get("order")}, {"kind": "Other", "value": invoice.get("buyer_reference")}) if one["value"]],
		"parties": [_party("Sender", seller), _party("Recipient", buyer)],
		"asks": [{"what": "Pay", "detail": invoice.get("number"), "by": invoice.get("due")}]
		if payable and invoice.get("kind") != "credit note" and means != "direct debit"
		else [],
		"sensitivity": "Ordinary",
		"confidence": 1,
	}


def _party(role: str, said: dict) -> dict:
	address = ", ".join(one for one in (said.get("street"), " ".join(filter(None, (said.get("postcode"), said.get("city")))), said.get("country")) if one)
	return {
		"role": role,
		"name": said.get("name"),
		"vat_id": said.get("vat_id"),
		"tax_number": said.get("tax_id"),
		"register": said.get("register"),
		"email": said.get("email"),
		"phone": said.get("phone"),
		"address": address or None,
	}


# ------------------------------------------------------------------ with a model


def look(reading, structured: dict) -> str:
	"""The first look: junk, or something to read. Mail a machine sent in bulk
	is a newsletter with no model asked."""
	if cint(reading.automatic) or (structured.get("mail") or {}).get("automatic"):
		return "Newsletter"
	mail = structured.get("forwarded") or structured.get("mail") or {}
	head = f"From: {mail.get('from_name') or ''} <{mail.get('from_email') or ''}>\nSubject: {mail.get('subject') or reading.title or ''}\n" if mail else f"File: {reading.title or ''}\n"
	answer = _ask(LOOK, f"{head}\n---\n{(reading.text or '')[:MOST_LOOK]}\n---", reading.name)
	verdict = str((answer or {}).get("verdict") or "").strip().title()
	return verdict if verdict in VERDICTS else "Information"


def ask(reading, structured: dict) -> dict:
	"""The reading, in the fixed shape the `intake_read` action asks for."""
	mail = structured.get("forwarded") or structured.get("mail") or {}
	context = [
		f"Workspace language: {frappe.db.get_single_value('System Settings', 'language') or 'en'}",
		f"Workspace country: {identity.country()}",
		f"Today: {today()}",
		f"Read as: {reading.how or ''}",
	]
	if mail:
		context += [f"From: {mail.get('from_name') or ''} <{mail.get('from_email') or ''}>", f"Subject: {mail.get('subject') or ''}", f"Sent: {mail.get('date') or ''}"]
	else:
		context.append(f"File name: {reading.title or ''}")
	taught = _lessons_for(mail)
	if taught:
		context.append(taught)
	text = (reading.text or "")[:MOST_TEXT]
	cut = "\n(The document goes on; this is its beginning.)" if len(reading.text or "") > MOST_TEXT else ""
	return _ask(READ, "\n".join(context) + f"\n\nThe document:\n---\n{text}\n---{cut}", reading.name) or {}


def _lessons_for(mail: dict) -> str:
	"""What people corrected for the sender before, when the sender is known."""
	from onedesk.one_intake import lessons

	sender = ids.email(mail.get("from_email")) if mail else None
	best = (identity.match([(ids.EMAIL, sender)]) or [None])[0] if sender else None
	return lessons.told(best["doctype"], best["name"]) if best else ""


def _ask(action: str, text: str, reference: str) -> dict | None:
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	return read(run.once(action, text, reference=reference))


# ------------------------------------------------------------------ keeping it


def apply(reading, said: dict, dropped: list[str], structured: dict) -> None:
	"""Put a reading into the Reading's fields and tables, and match its parties."""
	money = said.get("money") or {}
	kind = said.get("kind") if said.get("kind") in KINDS else "Other"
	reading.update(
		{
			"kind": kind,
			"summary": (said.get("summary") or "")[:1000] or None,
			"number": said.get("number"),
			"issued_on": said.get("issued"),
			"currency": _currency(money.get("currency")),
			"net": money.get("net"),
			"tax": money.get("tax"),
			"gross": money.get("gross"),
			"paid_how": PAID.get(str(money.get("paid_how") or "").lower()),
			"iban": ids.iban(money.get("iban")),
			"payment_reference": money.get("reference"),
			"sensitivity": sensitivity(kind, said.get("sensitivity")),
			"confidence": min(100, max(0, flt(said.get("confidence")) * 100)) if said.get("confidence") is not None else None,
			"dropped": "\n".join(dropped) or None,
			"unsure": int(bool(dropped) or flt(said.get("confidence"), 1) < 0.6),
		}
	)
	if said.get("title"):
		reading.title = said["title"][:140]
	document = said.get("document") or {}
	if kind in ("Identity Document", "Certificate") and document:
		reading.document_type = _document_type(document.get("type"))
		reading.issuing_country = _country(document.get("country"))
		reading.valid_until = document.get("expires")
		if document.get("expires"):
			said.setdefault("dates", []).append({"date": document["expires"], "what": "Valid Until", "found": 1})
	reading.set("dates", [
		{"date": one["date"], "what": one.get("what") if one.get("what") in DATES else "Other", "about": (one.get("about") or "")[:140], "found": cint(one.get("found", 1))}
		for one in said.get("dates") or [] if one.get("date") and not one.get("counted")
	] + counted(reading, said))
	reading.notice_period = (said.get("notice") or "")[:140] or None
	reading.keep_until = kept_until(reading)
	reading.noted = json.dumps(said.get("facts") or [], ensure_ascii=False) if said.get("facts") else None
	reading.set("asks", [
		{"what": one.get("what") if one.get("what") in ASKS else "Other", "detail": (one.get("detail") or "")[:140], "by_date": one.get("by") or None, "of_whom": (one.get("of") or "")[:140]}
		for one in said.get("asks") or []
	] + [
		{"what": "Other", "detail": (one.get("what") or "")[:140], "by_date": one.get("by") or None, "promise": 1}
		for one in said.get("promises") or [] if one.get("what")
	])
	shop = next((one.get("name") for one in said.get("parties") or [] if one.get("role") in ("Sender", "Paid To") and one.get("name")), None)
	reading.set("lines", [
		{
			"text": (one.get("text") or "")[:140], "qty": one.get("qty"), "unit_price": one.get("unit_price"), "amount": one.get("amount"),
			"tax_rate": one.get("tax_rate"), "code": one.get("code"),
			"category": one.get("category") if one.get("category") in CATEGORIES else learned(shop, one.get("text")),
		}
		for one in said.get("lines") or []
	])
	reading.set("refs", [
		{"kind": one.get("kind") if one.get("kind") in REFERENCES else "Other", "value": str(one["value"])[:140], "compact": facts.compact(one["value"])[:140]}
		for one in said.get("references") or [] if one.get("value")
	])
	parties = list(said.get("parties") or [])
	mail = structured.get("forwarded") or structured.get("mail") or {}
	if mail.get("from_email") and mail.get("direction") != "Sent" and not any((one.get("email") or "").lower() == mail["from_email"] for one in parties):
		parties.insert(0, {"role": "Sender", "name": mail.get("from_name"), "email": mail["from_email"], "person": True})
	reading.set("parties", [matched(one) for one in parties if one.get("name") or one.get("email")])


def counted(reading, said: dict) -> list[dict]:
	"""Deadlines the document gives as a period, counted here by the law's
	rules rather than by the model (deadlines.py)."""
	from frappe.utils import getdate

	from onedesk.one_intake import deadlines

	out = []
	for one in said.get("dates") or []:
		if not one.get("counted") and one.get("date"):
			continue
		posted = getdate(said.get("issued")) if said.get("issued") else None
		arrived = getdate(reading.creation) if reading.creation else None
		result = deadlines.count(one.get("about"), posted, said.get("kind"), identity.country(), _holidays(), arrived)
		if result:
			out.append({"date": result["date"], "what": one.get("what") if one.get("what") in DATES else "Deadline", "about": (one.get("about") or "")[:140], "found": 0, "counted_from": result["counted_from"], "rule": rule(result)[:140]})
	return out


def kept_until(reading):
	"""The day the law lets a business's document go (keep.py); a household
	keeps no books."""
	from frappe.utils import getdate

	from onedesk.one_intake import keep

	if frappe.db.get_single_value("Intake Settings", "household"):
		return None
	dated = reading.issued_on or reading.creation or today()
	return keep.until(reading.kind, identity.country(), getdate(dated))


def rule(result: dict) -> str:
	"""How a deadline was counted, in the workspace's language."""
	units = {"days": _("{0} days"), "weeks": _("{0} weeks"), "months": _("{0} months"), "years": _("{0} years")}
	one = {"days": _("one day"), "weeks": _("one week"), "months": _("one month"), "years": _("one year")}
	period = one[result["unit"]] if result["number"] == 1 else units[result["unit"]].format(result["number"])
	start = _("Posted, so received four days later (§ 122 AO)") if result["posted"] else _("From the day it arrived")
	said = _("{0}, plus {1}").format(start, period)
	return _("{0}, moved to the next working day").format(said) if result["moved"] else said


def _holidays() -> set:
	company = frappe.defaults.get_global_default("company")
	holiday_list = frappe.db.get_value("Company", company, "default_holiday_list") if company else None
	return set(frappe.get_all("Holiday", filters={"parent": holiday_list}, pluck="holiday_date")) if holiday_list else set()


def learned(shop: str | None, text: str | None) -> str | None:
	"""A line's category from the shop's own history, with no model: the same
	line bought there before, else what that shop's lines usually are."""
	if not shop:
		return None
	parents = frappe.get_all("Reading Party", filters={"party_name": shop, "role": ["in", ("Sender", "Paid To")]}, pluck="parent", limit=200)
	if not parents:
		return None
	rows = frappe.get_all("Reading Line", filters={"parent": ["in", parents], "category": ["is", "set"]}, fields=["text", "category"], limit=500)
	same = [row.category for row in rows if text and (row.text or "").strip().lower() == text.strip().lower()]
	pool = same or [row.category for row in rows]
	return max(set(pool), key=pool.count) if pool else None


def matched(party: dict) -> dict:
	"""One party as a Reading Party row, matched to a record where its
	identifiers point at one, and set aside where it is ourselves."""
	row = {
		"role": party.get("role") if party.get("role") in ROLES else "Mentioned",
		"party_name": (party.get("name") or party.get("person_name") or "")[:140] or None,
		"is_person": int(bool(party.get("person"))),
		"email": ids.email(party.get("email")),
		"phone": party.get("phone"),
		"website": party.get("website"),
		"vat_id": ids.vat(party.get("vat_id")),
		"tax_number": party.get("tax_number"),
		"iban": ids.iban(party.get("iban")),
		"register": party.get("register"),
		"document_number": ids.document(party.get("document_number")),
		"birth_date": party.get("birth_date") or None,
		"address": party.get("address"),
	}
	pairs = pairs_of(row)
	row["ours"] = {"company": "Company", "colleague": "Colleague"}.get(identity.ours(pairs) or "", "")
	if not row["ours"]:
		best = (identity.match(pairs) or [None])[0]
		if best:
			row.update({"matched_doctype": best["doctype"], "matched_name": best["name"], "score": round(best["score"], 2)})
	return row


def pairs_of(row: dict) -> list[tuple[str, str]]:
	return ids.found(
		[
			(ids.EMAIL, row.get("email")),
			(ids.PHONE, row.get("phone")),
			(ids.WEBSITE, row.get("website")),
			(ids.VAT, row.get("vat_id")),
			("Tax ID", row.get("tax_number")),
			(ids.IBAN, row.get("iban")),
			(ids.REGISTER, row.get("register")),
			(ids.DOCUMENT, row.get("document_number")),
		],
		identity.country(),
	)


def sensitivity(kind: str, said: str | None) -> str:
	"""The more sensitive of what the kind is and what the model said. Pure."""
	said = str(said or "").title()
	floor = SENSITIVE.get(kind, "Ordinary")
	said = said if said in LEVELS else "Ordinary"
	return max(said, floor, key=LEVELS.index)


def _currency(code) -> str | None:
	code = str(code or "").strip().upper()[:3]
	return code if code and frappe.db.exists("Currency", code) else None


def _country(code) -> str | None:
	code = str(code or "").strip()
	if not code:
		return None
	return frappe.db.get_value("Country", {"code": code.lower()}, "name") or frappe.db.get_value("Country", code, "name")


def _document_type(said) -> str | None:
	said = str(said or "").strip()
	return said if said and frappe.db.exists("Identification Document Type", said) else None
