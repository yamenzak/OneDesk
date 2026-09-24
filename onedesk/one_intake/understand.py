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
	"Notice of Change", "Contact Card", "Letter", "Other",
)  # fmt: skip
ROLES = ("Sender", "Recipient", "Holder", "Patient", "Employee", "Paid To", "Mentioned")
DATES = ("Due", "Deadline", "Appointment", "Valid From", "Valid Until", "Period Start", "Period End", "Service", "Other")
ASKS = ("Pay", "Sign", "Reply", "Attend", "Send", "Cancel", "Decide", "Other")
REFERENCES = ("Invoice", "Order", "Customer", "Contract", "Case", "Tax", "Policy", "Other")
PAID = {"transfer": "Transfer", "direct debit": "Direct Debit", "already paid": "Already Paid"}

#: How sensitive a kind is at least, whatever the model said.
SENSITIVE = {"Payslip": "Pay", "Sick Note": "Medical", "Medical Report": "Medical", "Identity Document": "Personal", "CV": "Personal"}
LEVELS = ("Ordinary", "Personal", "Legal", "Pay", "Medical")


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
			said, dropped = facts.check(ask(reading, structured), reading.text or "", identity.country())
		except Exception as raised:
			from onedesk.one_intake import pipeline

			pipeline._failed(reading, raised)
			return
	apply(reading, said, dropped, structured)
	_done(reading)


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
		for one in said.get("dates") or [] if one.get("date")
	])
	reading.set("asks", [
		{"what": one.get("what") if one.get("what") in ASKS else "Other", "detail": (one.get("detail") or "")[:140], "by_date": one.get("by") or None, "of_whom": (one.get("of") or "")[:140]}
		for one in said.get("asks") or []
	])
	reading.set("lines", [
		{"text": (one.get("text") or "")[:140], "qty": one.get("qty"), "unit_price": one.get("unit_price"), "amount": one.get("amount"), "tax_rate": one.get("tax_rate"), "code": one.get("code")}
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
