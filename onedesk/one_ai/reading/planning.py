"""Stage 6 of Intake on the site: what `plans.py` needs to know, and the flows
it names.

`run` is called once a matter is quiet (matters.act_now), asks the pure
planners what to do, and hands each action to the door.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, today

from onedesk.one_ai.reading import act, identity, matters, plans, tell
from onedesk.one_ai.reading import identifiers as ids
from onedesk.one_hr.hiring import AUTHOR

DONE_WHEN = {"Reply": "reply", "Send": "reply", "Attend": "after"}


def run(name: str, which: str) -> None:
	"""One pass of planning for one understood reading: "parties", "money"
	or "rest"."""
	reading = frappe.get_doc("Reading", name)
	if not reading.on_behalf_of or cint(reading.history) or reading.state != "Understood":
		return
	said = _said(reading)
	ctx = context(reading, said)
	if which == "parties":
		wanted = plans.parties(said, ctx)
	elif which == "money":
		from onedesk.one_ai.reading import money

		_money(ctx, reading)
		wanted = money.plan(said, ctx)
	else:
		_payable(ctx, reading)
		ctx["project"] = _project_named(reading) if _supplier(reading) or reading.kind in PROJECT_KINDS else None
		wanted = plans.second(said, ctx)
	made = []
	for action in wanted:
		action.key = matters.key(reading, action.key) if action.key.startswith(("task", "event", "leave", "expense", "resignation", "employee", "books")) else f"{reading.key[:90]}|{action.key}"
		made.append(act.apply(action, reading))
	frappe.db.commit()
	if which == "parties" and wanted:
		rematch(reading, _made_for(reading, said, made))
	if which == "money" and wanted:
		from onedesk.one_ai.reading import drafts

		drafts.maybe_submit(reading)
	if which == "rest":
		tell.arrived_after_closing(reading, ctx)
		_hold_iban(reading)


def _made_for(reading, said: dict, made: list) -> bool:
	"""The counterpart is the record just made for it, which also learns how
	the document reached it, so the next one from there is matched to it."""
	done = [frappe.db.get_value("Reading Action", name, ["kind", "level", "target_doctype", "target_name"], as_dict=True) for name in made if name]
	record = next((one for one in done if one and one.kind == "Create" and one.level == "Done" and one.target_name), None)
	party = plans.counterpart(said)
	row = next((one for one in reading.parties if party and one.idx == party.get("idx")), None)
	if not record or not row or (row.matched_doctype, row.matched_name) == (record.target_doctype, record.target_name):
		return False
	row.matched_doctype, row.matched_name, row.score = record.target_doctype, record.target_name, 1
	origin = f"{reading.doctype}/{reading.name}"
	for kind, field in ((ids.EMAIL, "email"), (ids.PHONE, "phone"), (ids.IBAN, "iban")):
		if row.get(field):
			identity.learn(kind, row.get(field), record.target_doctype, record.target_name, origin)
	return True


def rematch(reading, changed: bool = False) -> None:
	"""Match the reading's parties again, now that records were made."""
	from onedesk.one_ai.reading import understand

	for row in reading.parties:
		if row.matched_name or row.ours:
			continue
		again = understand.matched({key: row.get(key) for key in ("role", "party_name", "is_person", "email", "phone", "website", "vat_id", "tax_number", "iban", "register", "document_number", "birth_date", "address")} | {"name": row.party_name})
		if again.get("matched_name"):
			row.matched_doctype, row.matched_name, row.score = again["matched_doctype"], again["matched_name"], again.get("score")
			changed = True
	if changed:
		belongs = [(row.matched_doctype, row.matched_name) for row in reading.parties if row.matched_name and (row.score or 0) >= identity.CERTAIN]
		if belongs and not reading.party_name:
			reading.party_doctype, reading.party_name = belongs[0]
		reading.flags.ignore_permissions = True
		reading.save()
		frappe.db.commit()


def _said(reading) -> dict:
	said = reading.as_dict(convert_dates_to_str=True)
	for one in said.get("parties") or []:
		one["org_domain"] = ids.organisation_domain(one.get("email")) if one.get("email") else None
	return said


def context(reading, said: dict) -> dict:
	structured = json.loads(reading.structured or "{}")
	mail = structured.get("forwarded") or structured.get("mail") or {}
	language = frappe.db.get_single_value("System Settings", "language") or "en"
	ctx: dict = {
		"today": today(),
		"person": reading.on_behalf_of,
		"history": cint(reading.history),
		"direction": (structured.get("mail") or {}).get("direction"),
		"why_made": _("Made from {0}.", lang=language).format(reading.title or ""),
		"said": _words(language),
		"supplier_group": _leaf("Supplier Group", "Buying Settings", "supplier_group"),
		"customer_group": _leaf("Customer Group", "Selling Settings", "customer_group"),
		"territory": _leaf("Territory", "Selling Settings", "territory"),
		"applicant_source": "Email" if frappe.db.exists("Job Applicant Source", "Email") else None,
		"done_when": {},
		"subject": (mail.get("subject") or "").strip(),
	}
	_sender(ctx, mail, structured)
	ctx["people"] = _people(ctx, mail, said)
	ctx["referred"] = _referred(reading)
	ctx["carrier"] = carrier(reading)
	_about(ctx, reading)
	_employee(ctx, reading)
	_task(ctx, reading)
	return ctx


def _words(language: str) -> dict:
	"""What OneAI writes on records, in the workspace's language."""
	return {
		"renew": _("Renew the {0} of {1}", lang=language),
		"document": _("document", lang=language),
		"sick_note": _("From a sick note, which arrived by mail.", lang=language),
		"arrived": _("A document arrived", lang=language),
		"arrived_for": _("A document arrived for {0}", lang=language),
		"nudged": _("Reminder: {0}", lang=language),
		"appointment": _("Appointment", lang=language),
		"asks": {one: _(one, lang=language) for one in ("Pay", "Sign", "Reply", "Attend", "Send", "Cancel", "Decide", "Other")},
		"moved": _("Dated after the books closed on {0}.", lang=language),
		"direct_debit": _("Paid by direct debit.", lang=language),
		"paid": _("Already paid.", lang=language),
		"no_original": _("The invoice this credits was not found.", lang=language),
		"unmatched": _("Some lines match no item.", lang=language),
		"see_document": _("See the attached document.", lang=language),
		"ask_for_invoice": _("Ask {1} for invoice {0}", lang=language),
		"maybe_fraud": _("Reminder for an unknown invoice. Ask for the invoice before paying.", lang=language),
		"decide_cancel": _("Decide whether to cancel the contract with {0} (last day {1})", lang=language),
		"unordered": _("Check the unordered delivery from {0}", lang=language),
		"timesheet": _("From their timesheet.", lang=language),
	}


def _leaf(doctype: str, settings: str, field: str) -> str | None:
	chosen = frappe.db.get_single_value(settings, field)
	if chosen:
		return chosen
	return frappe.db.get_value(doctype, {"is_group": 0}, "name", order_by="creation asc")


def _sender(ctx: dict, mail: dict, structured: dict) -> None:
	email = ids.email(mail.get("from_email"))
	ctx["sender_email"], ctx["sender_name"] = email, (mail.get("from_name") or "").strip() or None
	if not email:
		return
	user = frappe.db.get_value("User", {"name": email, "user_type": "System User", "enabled": 1}, "name")
	ctx["sender_is_colleague"] = bool(user)
	ctx["sender_colleague"] = user
	if ctx.get("direction") == "Sent":
		ctx["sender_user"] = user or frappe.db.get_value("User", {"email": email}, "name")
	if user:
		ctx["sender_employee"] = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
		if ctx["sender_employee"]:
			from onedesk.one_hr import ai as hr_ai

			ctx["expense_approver"] = frappe.db.get_value("Employee", ctx["sender_employee"], "expense_approver")
			ctx["expense_type"] = hr_ai.kind("", "", frappe.get_all("Expense Claim Type", pluck="name"))
			company = frappe.db.get_value("Employee", ctx["sender_employee"], "company")
			ctx["company_currency"] = frappe.db.get_value("Company", company, "default_currency") if company else None
		return
	contact = frappe.db.get_value("Contact Email", {"email_id": email, "parenttype": "Contact"}, "parent")
	if contact:
		ctx["sender_contact"] = contact
		links = frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "parent": contact}, fields=["link_doctype", "link_name"])
		ctx["sender_contact_links"] = [(one.link_doctype, one.link_name) for one in links]
		first = frappe.db.get_value("Contact", contact, "first_name") or ""
		ctx["sender_contact_bare"] = not links and first.lower() == email.split("@")[0].lower()
		ctx["sender_contact_phones"] = frappe.get_all("Contact Phone", filters={"parent": contact, "parenttype": "Contact"}, pluck="phone")
	best = (identity.match([(ids.EMAIL, email)]) or [None])[0]
	if best:
		ctx["sender_party"] = (best["doctype"], best["name"])
		converted = best["doctype"] == "Lead" and frappe.db.get_value("Customer", {"lead_name": best["name"]}, "name")
		if converted:
			ctx["sender_party"] = ("Customer", converted)
		elif best["doctype"] == "Lead":
			ctx["sender_lead"] = best["name"]
	ctx["sender_company"] = None


#: Records a document may name by our own id.
OURS_NAMED = (
	"Purchase Order",
	"Sales Order",
	"Sales Invoice",
	"Purchase Invoice",
	"Quotation",
	"Supplier Quotation",
	"Request for Quotation",
	"Material Request",
	"Delivery Note",
	"Purchase Receipt",
	"Project",
	"Task",
	"Issue",
	"Opportunity",
	"Contract",
)

#: The other side's own numbers, where we keep them: the customer's order
#: number on our sales order, the supplier's invoice number on their bill.
THEIRS_NAMED = (("Sales Order", "po_no"), ("Sales Invoice", "po_no"), ("Purchase Invoice", "bill_no"))


def _referred(reading) -> list[tuple[str, str]]:
	"""The records a document names by number: ours by their id, and the
	other side's by the number we keep of theirs."""
	found = []
	for ref in reading.get("refs") or []:
		value = (ref.value or "").strip()
		if len(value) < 4:
			continue
		for doctype in OURS_NAMED:
			if frappe.db.exists(doctype, value):
				found.append((doctype, value))
		for doctype, field in THEIRS_NAMED:
			if frappe.get_meta(doctype).has_field(field):
				found += [(doctype, one) for one in frappe.get_all(doctype, filters={field: value, "docstatus": ["<", 2]}, pluck="name", limit=3)]
	return list(dict.fromkeys(found))[:10]


def carrier(reading) -> dict | None:
	"""What a link files: the message a mail reading is, or the file a
	document or an attachment came in, as filing files it."""
	if reading.source_doctype == "Communication" and not reading.part_of:
		return {"message": reading.source_name}
	held = frappe.db.get_value("File", {"one_reading": reading.name}, "name") or (
		reading.source_name if reading.source_doctype == "File" else None
	)
	return {"file": held, "reading": reading.name} if held else None


MENTIONS = ("Sender", "Recipient", "Mentioned", "Paid To")

PARTY_KINDS = ("Supplier", "Customer", "Lead", "Prospect")


def _people(ctx: dict, mail: dict, said: dict) -> list[dict]:
	"""Everyone in a message who could be reached: the addresses it went to
	and was copied to, and the people it names with an email or a phone,
	each with the Contact that already holds them and the organisation their
	address belongs to. Not the sender, whom `_sender` covers, and not us."""
	from email.utils import getaddresses

	land = identity.country()
	found: list[dict] = []
	heads = getaddresses([str(mail.get("to") or ""), str(mail.get("cc") or "")])
	persons = [
		one for one in said.get("parties") or [] if one.get("is_person") and one.get("role") in MENTIONS and not one.get("ours")
	]
	named = {ids.email(one.get("email")): one for one in persons if ids.email(one.get("email"))}
	for name, address in heads:
		found.append({"name": name, "email": ids.email(address), "phone": None})
	for one in persons:
		found.append(
			{
				"name": one.get("person_name") or one.get("party_name"),
				"email": ids.email(one.get("email")),
				"phone": ids.phone(one.get("phone"), land),
				"job_title": one.get("job_title"),
				"company": one.get("company"),
			}
		)
	out, seen = [], {ctx.get("sender_email")}
	for one in found:
		keys = [key for key in (one["email"], one["phone"]) if key]
		if not keys or seen & set(keys):
			continue
		also = named.get(one["email"]) or {}
		one = {**one, "phone": one["phone"] or ids.phone(also.get("phone"), land), "job_title": one.get("job_title") or also.get("job_title"), "company": one.get("company") or also.get("company")}
		keys = [key for key in (one["email"], one["phone"]) if key]
		seen |= set(keys)
		pairs = [(ids.EMAIL, one["email"])] if one["email"] else []
		pairs += [(ids.PHONE, one["phone"])] if one["phone"] else []
		if identity.ours(pairs + ([(ids.DOMAIN, ids.domain(one["email"]))] if one["email"] else [])):
			continue
		held = next((name for kind, value in pairs for doctype, name in identity.holders(kind, value) if doctype == "Contact"), None)
		org = None
		if one["email"] and ids.organisation_domain(one["email"]):
			held_by = [
				found for found in identity.match([(ids.DOMAIN, ids.organisation_domain(one["email"]))]) if found["doctype"] in PARTY_KINDS
			]
			org = (held_by[0]["doctype"], held_by[0]["name"]) if len(held_by) == 1 else None
		person = {**one, "contact": held, "org": org}
		if held:
			person["emails"] = frappe.get_all("Contact Email", filters={"parent": held, "parenttype": "Contact"}, pluck="email_id")
			person["phones"] = [ids.phone(number, land) for number in frappe.get_all("Contact Phone", filters={"parent": held, "parenttype": "Contact"}, pluck="phone")]
			person["links"] = [(link.link_doctype, link.link_name) for link in frappe.get_all("Dynamic Link", filters={"parenttype": "Contact", "parent": held}, fields=["link_doctype", "link_name"])]
		out.append(person)
	return out[:MOST_PEOPLE]


MOST_PEOPLE = 20


def _about(ctx: dict, reading) -> None:
	"""The record a matter's task is about: the matter's first record."""
	belongs = matters.records_of(reading.matter) if reading.matter else []
	if not belongs and reading.party_name:
		belongs = [(reading.party_doctype, reading.party_name)]
	if belongs:
		ctx["about"] = belongs[0]
		meta = frappe.get_meta(belongs[0][0])
		title = meta.get_title_field()
		ctx["about_title"] = frappe.db.get_value(*belongs[0], title) if title and title != "name" else belongs[0][1]
	if not ctx.get("sender_party") and reading.party_name:
		ctx["sender_party"] = (reading.party_doctype, reading.party_name)
	file = frappe.db.get_value("File", {"one_reading": reading.name}, "file_url") or (
		frappe.db.get_value("File", reading.source_name, "file_url") if reading.source_doctype == "File" else None
	)
	ctx["file_url"] = file


def _employee(ctx: dict, reading) -> None:
	"""The employee a document is about: the one it names, or the one who
	sent their own document in."""
	found = next(
		(row.matched_name for row in reading.parties if row.matched_doctype == "Employee" and (row.score or 0) >= identity.CERTAIN and row.role in ("Holder", "Patient", "Employee", "Sender")),
		None,
	)
	applicant = next((row.matched_name for row in reading.parties if row.matched_doctype == "Job Applicant" and (row.score or 0) >= identity.CERTAIN), None)
	if not found and ctx.get("sender_employee") and reading.kind in ("Identity Document", "Certificate", "Sick Note", "Resignation"):
		found = ctx["sender_employee"]
	if applicant:
		ctx["accepted_offer"] = frappe.db.get_value("Job Offer", {"job_applicant": applicant, "status": "Accepted", "docstatus": 1}, "name")
		ctx["employee_of_applicant"] = frappe.db.get_value("Employee", {"job_applicant": applicant}, "name")
	if not found:
		return
	ctx["employee"] = found
	ctx["employee_name"] = frappe.db.get_value("Employee", found, "employee_name")
	held = frappe.get_all("Employee Document", filters={"parent": found, "parenttype": "Employee"}, fields=["name", "number", "document_type"])
	ctx["employee_document_numbers"] = [one.number for one in held]
	ctx["employee_documents_by_type"] = {one.document_type: one.name for one in held}
	if reading.kind == "Sick Note":
		from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

		from onedesk.one_hr import ai as hr_ai

		ctx["sick_leave_type"] = hr_ai._leave_type("sick", frappe.get_all("Leave Type", pluck="name"))
		ctx["leave_approver"] = get_employee_leave_approver(found)


def _task(ctx: dict, reading) -> None:
	"""The task the matter already has, and what ticks each new step."""
	readings = frappe.get_all("Reading", filters={"matter": reading.matter}, pluck="name") if reading.matter else [reading.name]
	made = frappe.db.get_value(
		"Reading Action",
		{"reading": ["in", readings], "kind": "Create", "target_doctype": "Task", "level": "Done", "key": ["like", "%|task"]},
		"target_name",
	)
	if made and frappe.db.exists("Task", made):
		ctx["task"] = frappe.db.get_value("Task", made, ["name", "status", "priority", "exp_end_date", "modified_by"], as_dict=True)
	thread = frappe.db.get_value("Communication", reading.source_name, "one_thread") if reading.source_doctype == "Communication" else None
	if thread:
		ctx["done_when"]["Reply"] = json.dumps({"reply_in": thread})
		ctx["done_when"]["Send"] = json.dumps({"reply_in": thread, "attached": 1})
	for one in reading.asks:
		if one.what == "Attend" and one.by_date:
			ctx["done_when"]["Attend"] = json.dumps({"after": str(one.by_date)})


def _money(ctx: dict, reading) -> None:
	"""What the money planners need: the party's record, what came before
	(the order, the invoice a credit note credits, one already booked), the
	items the lines are, our bank account, and the books' lock."""
	ctx["books"] = not cint(frappe.db.get_single_value("Reading Settings", "household")) and frappe.db.count("Company") > 0
	if not ctx["books"]:
		return
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	ctx["locked"] = str(frappe.db.get_value("Company", company, "accounts_frozen_till_date") or "") or None
	parties = _parties(reading)
	ctx["supplier"] = _supplier(reading)
	ctx["customer"] = parties.get("Customer") or (reading.party_name if reading.party_doctype == "Customer" else None)
	ctx["contract_party"] = ("Supplier", ctx["supplier"]) if ctx["supplier"] else (("Customer", ctx["customer"]) if ctx["customer"] else None)
	ctx["project"] = _project_named(reading) if ctx["supplier"] else None
	if ctx["customer"] and reading.kind == "Change Request":
		named = _project_named(reading)
		ctx["project"] = named if named and frappe.db.get_value("Project", named, "customer") == ctx["customer"] else None
	ctx["file"] = frappe.db.get_value("File", {"one_reading": reading.name}, "name") or (reading.source_name if reading.source_doctype == "File" else None)
	refs = {row.kind: row.value for row in reading.refs}
	named = [row.value for row in reading.refs]
	if ctx["supplier"]:
		if reading.number:
			ctx["existing_invoice"] = frappe.db.get_value("Purchase Invoice", {"supplier": ctx["supplier"], "bill_no": reading.number, "docstatus": ["<", 2], "owner": ["!=", AUTHOR]}, "name")
		if refs.get("Invoice"):
			ctx["original_invoice"] = frappe.db.get_value("Purchase Invoice", {"supplier": ctx["supplier"], "bill_no": refs["Invoice"], "docstatus": 1, "is_return": 0}, "name")
		ctx["purchase_order"] = next((one for one in named if frappe.db.exists("Purchase Order", {"name": one, "supplier": ctx["supplier"], "docstatus": 1})), None)
		company = (
			(ctx["purchase_order"] and frappe.db.get_value("Purchase Order", ctx["purchase_order"], "company"))
			or (ctx["project"] and frappe.db.get_value("Project", ctx["project"], "company"))
			or frappe.db.get_value("Purchase Invoice", {"supplier": ctx["supplier"], "docstatus": 1}, "company", order_by="posting_date desc")
			or company
		)
		ctx["company"] = company
		ctx["locked"] = str(frappe.db.get_value("Company", company, "accounts_frozen_till_date") or "") or None
		ctx["items"] = _items(reading, ctx["supplier"], "Item Supplier", "supplier", "supplier_part_no")
		ctx["expense_account"] = frappe.db.sql(
			"""select item.expense_account from `tabPurchase Invoice Item` item
			join `tabPurchase Invoice` bill on bill.name = item.parent
			where bill.supplier = %s and bill.company = %s and bill.docstatus = 1 and ifnull(item.expense_account, '') != ''
			order by bill.posting_date desc limit 1""",
			(ctx["supplier"], company),
		)
		ctx["expense_account"] = ctx["expense_account"][0][0] if ctx["expense_account"] else frappe.db.get_value("Company", company, "default_expense_account")
		ctx["purchase_taxes"] = _taxes_by_rate(company)
	if ctx["customer"]:
		ctx["customer_items"] = _items(reading, ctx["customer"], "Item Customer Detail", "customer_name", "ref_code")
		ctx["sales_invoice"] = next((one for one in named if frappe.db.exists("Sales Invoice", {"name": one, "customer": ctx["customer"], "docstatus": 1})), None)
	statement = json.loads(reading.structured or "{}").get("statement") or {}
	if statement:
		ctx["bank_account"] = frappe.db.get_value("Bank Account", {"iban": statement.get("account_iban"), "is_company_account": 1}, "name") if statement.get("account_iban") else None
		ctx["statement_currency"] = statement.get("currency")
		ctx["statement_lines"] = [
			{
				"date": one.get("date"),
				"amount": one.get("amount"),
				"text": one.get("text"),
				"reference": one.get("reference"),
				"party": one.get("party"),
				"iban": one.get("party_iban"),
				"key": frappe.generate_hash(json.dumps([statement.get("account_iban"), one.get("date"), one.get("amount"), one.get("reference"), one.get("text"), index], default=str), 12),
			}
			for index, one in enumerate(statement.get("entries") or [])
		]
	named_invoice = refs.get("Invoice")
	if named_invoice:
		ctx["invoice_known"] = bool(
			frappe.db.exists("Purchase Invoice", {"bill_no": named_invoice})
			or frappe.db.exists("Reading", {"number": named_invoice, "name": ["!=", reading.name], "kind": ["in", ("Invoice", "Credit Note")]})
		)
	ctx["sender_title"] = next((row.party_name for row in reading.parties if row.role == "Sender" and row.party_name), "")


def _items(reading, party: str, table: str, field: str, code: str) -> dict:
	"""Which item each line is: the party's own code for it (Item Supplier,
	Item Customer Detail), our item code, an item of exactly that name, or
	the one item whose name the line's words say.
	A line that is none of these stays words, and a new stock item is never
	made from a document."""
	out = {}
	for index, line in enumerate(reading.lines):
		found = None
		if line.code:
			found = frappe.db.get_value(table, {field: party, code: line.code, "parenttype": "Item"}, "parent") or (line.code if frappe.db.exists("Item", line.code) else None)
		if not found and line.text:
			found = frappe.db.get_value("Item", {"item_name": line.text.strip(), "disabled": 0}, "name")
		if not found and line.text:
			found = _named_in(line.text)
		if found:
			out[index] = found
	if not out and len(reading.lines) == 1 and table == "Item Supplier":
		last = frappe.db.sql(
			"""select item.item_code from `tabPurchase Invoice Item` item
			join `tabPurchase Invoice` bill on bill.name = item.parent
			where bill.supplier = %s and bill.docstatus = 1 and ifnull(item.item_code, '') != ''
			group by item.parent having count(*) = 1 order by max(bill.posting_date) desc limit 1""",
			party,
		)
		if last:
			out[0] = last[0][0]
	return out


def _named_in(text: str) -> str | None:
	"""The one item whose whole name, of two words or more, the line's words
	say ("Scaffolding hire for the villa facade" is Scaffolding Hire). None
	when no item or several do."""
	words = " {} ".format(" ".join("".join(c if c.isalnum() else " " for c in text).split()))
	found = frappe.db.sql(
		"""select name from `tabItem` where disabled = 0 and item_name like '%% %%'
		and %s like concat('%% ', item_name, ' %%') limit 2""",
		words,
		pluck=True,
	)
	return found[0] if len(found) == 1 else None


def _payable(ctx: dict, reading) -> None:
	"""The pay step ticks itself when the invoice this matter booked is
	submitted and paid. A document paid by direct debit, or already paid,
	asks nobody to pay."""
	readings = frappe.get_all("Reading", filters={"matter": reading.matter}, pluck="name") if reading.matter else [reading.name]
	booked = frappe.db.get_value("Reading Action", {"reading": ["in", readings], "kind": "Create", "target_doctype": "Purchase Invoice", "level": "Done"}, "target_name")
	if booked:
		ctx["done_when"]["Pay"] = json.dumps({"doctype": "Purchase Invoice", "name": booked, "all": [{"field": "docstatus", "equals": 1}, {"field": "outstanding_amount", "equals": 0}]})
	ctx["nobody_pays"] = reading.paid_how in ("Direct Debit", "Already Paid") or reading.kind == "Receipt"


def _hold_iban(reading) -> None:
	"""A known supplier's document asking to be paid to an IBAN we do not have
	for them is exactly what invoice fraud looks like. Its draft bill is held
	(drafts.red) and the IBAN is never written over ours; here the bill is also
	marked wrong, with why, so it waits for the person like anything else OneAI
	could not settle, and Documents Waiting says so (tell.waiting)."""
	if not reading.iban or reading.party_doctype != "Supplier" or not reading.party_name:
		return
	known = [one.replace(" ", "").upper() for one in frappe.get_all("Bank Account", filters={"party_type": "Supplier", "party": reading.party_name}, pluck="iban") if one]
	if not known or reading.iban.replace(" ", "").upper() in known:
		return
	made = frappe.db.get_value("Reading Action", {"reading": reading.name, "kind": "Create", "target_doctype": "Purchase Invoice", "level": "Done"}, "name")
	if made:
		why = _("The IBAN isn't on file for {0}. Confirm it by phone before paying.").format(reading.party_name)
		frappe.db.set_value("Reading Action", made, {"audit": "Wrong", "audit_why": why}, update_modified=False)


def make_task(values: dict):
	"""A task, given by the workspace's Assignment Rules where one takes it,
	and otherwise to the person it is for. Its steps say what ticks them."""
	values = dict(values)
	who = values.pop("assign_to", None)
	doc = frappe.get_doc({"doctype": "Task", **values})
	doc.flags.ignore_permissions = True
	doc.flags.one_assigned = True
	doc.insert()
	held = frappe.db.exists("ToDo", {"reference_type": "Task", "reference_name": doc.name, "status": "Open"})
	if who and not held:
		from frappe.desk.form import assign_to

		assign_to._add({"doctype": "Task", "name": doc.name, "assign_to": [who], "description": doc.subject}, ignore_permissions=True)
	from onedesk.one_ai.reading import steps

	steps.changed()
	return doc


def make_event(values: dict):
	"""An event, on the calendar of whoever it is for: one of its
	participants, as OneCalendar adds anybody (one_calendar/events.invite)."""
	from onedesk.one_calendar import events

	values = dict(values)
	who = values.pop("for", None)
	doc = frappe.get_doc({"doctype": "Event", **values})
	if who:
		events.invite(doc, [who])
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def customer_from_lead(values: dict):
	"""A customer made the way ERPNext makes one from a lead, so the lead's
	mail and comments go with it. Made as the person, since ERPNext then
	saves the lead's contact as whoever is signed in."""
	from erpnext.crm.doctype.lead.mapper import make_customer

	doc = mapped(make_customer, values["lead"])
	doc.insert()
	return doc


def employee_from_offer(values: dict):
	"""An employee made the way HRMS's Create Employee button makes one."""
	from hrms.hr.doctype.job_offer.job_offer import make_employee

	doc = mapped(make_employee, values["job_offer"])
	doc.insert()
	return doc


def mapped(make, *args, **kwargs):
	"""A record from ERPNext's own door (a mapper), which reads the source as
	whoever is signed in. OneAI's user holds no roles, so it maps as the
	person OneAI acts for, and the record is still written as OneAI."""
	writer = frappe.session.user
	frappe.set_user(frappe.flags.one_intake_for or writer)
	try:
		doc = make(*args, **kwargs)
	finally:
		frappe.set_user(writer)
	doc.flags.ignore_permissions = True
	return doc


def debit_note(values: dict):
	"""A credit note, as ERPNext's return against the invoice it credits."""
	from erpnext.accounts.doctype.purchase_invoice.mapper import make_debit_note

	values = dict(values)
	doc = mapped(make_debit_note, values.pop("against"))
	doc.update(values)
	doc.insert()
	return doc


def invoice_from_order(values: dict):
	"""An invoice, as ERPNext bills a Purchase Order, so it is matched to the
	order and its receipt. The order's payment row comes with it, dated from
	the order, so where the order agreed no terms the bill's own due date is
	the one kept."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice

	values = dict(values)
	doc = mapped(make_purchase_invoice, values.pop("order"))
	if values.get("due_date") and not doc.payment_terms_template:
		doc.set("payment_schedule", [])
	doc.update(values)
	doc.insert()
	return doc


def receipt_from_order(values: dict):
	"""A supplier's delivery note, as ERPNext receives a Purchase Order, for
	what the note says came when it says (`delivered`, by item)."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	values = dict(values)
	doc = mapped(make_purchase_receipt, values.pop("order"))
	delivered = values.pop("delivered", None)
	if delivered:
		left = dict(delivered)
		for row in doc.items:
			take = min(flt(row.qty), flt(left.get(row.item_code)))
			left[row.item_code] = flt(left.get(row.item_code)) - take
			row.qty = take
		doc.set("items", [row for row in doc.items if flt(row.qty) > 0])
	doc.update({key: value for key, value in values.items() if value})
	doc.insert()
	return doc


def payment_for(values: dict):
	"""A customer's payment advice, as ERPNext's payment against our invoice."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	doc = mapped(get_payment_entry, "Sales Invoice", values["invoice"], party_amount=values.get("amount"))
	doc.reference_no = values.get("reference_no")
	doc.reference_date = values.get("reference_date")
	doc.insert()
	return doc


def bank_line(values: dict):
	"""A statement's line, as a Bank Transaction ERPNext can reconcile. It is
	submitted, since a bank line is not a posting and reconciliation reads
	only submitted ones."""
	doc = frappe.get_doc({"doctype": "Bank Transaction", **values})
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	return doc


FOUND = {ids.EMAIL: "email", ids.VAT: "vat_id", ids.IBAN: "iban", ids.DOCUMENT: "document_number"}


def backlink(doc, method=None) -> None:
	"""after_insert of a party: the readings that named it before it existed
	are matched to it, and their documents linked."""
	if doc.doctype not in ("Supplier", "Customer", "Lead", "Contact", "Employee", "Job Applicant") or frappe.flags.in_import or frappe.flags.in_migrate or frappe.flags.in_install:
		return
	pairs = ids.found(identity.said(doc), identity.country())
	rows = []
	for kind, value in pairs:
		field = FOUND.get(kind)
		if field:
			rows += frappe.get_all("Reading Party", filters={field: value, "matched_name": ["is", "not set"], "ours": ["in", ("", None)]}, fields=["name", "parent"])
	if not rows:
		return
	frappe.enqueue("onedesk.one_ai.reading.planning.link_back", queue="long", enqueue_after_commit=True, doctype=doc.doctype, name=doc.name, rows=[dict(one) for one in rows])


def link_back(doctype: str, name: str, rows: list[dict]) -> None:
	from onedesk.one_ai.reading.act import Action

	for one in rows:
		frappe.db.set_value("Reading Party", one["name"], {"matched_doctype": doctype, "matched_name": name, "score": identity.CERTAIN}, update_modified=False)
		reading = frappe.get_doc("Reading", one["parent"])
		target = frappe.db.get_value("File", {"one_reading": reading.name}, "name") or reading.source_name
		if reading.source_doctype == "Communication" and not reading.part_of:
			action = Action("Link", doctype, name, {"message": reading.source_name}, key=f"{reading.key[:90]}|back|{doctype}|{name}", sure=True)
		else:
			action = Action("Link", doctype, name, {"file": target, "reading": reading.name}, key=f"{reading.key[:90]}|back|{doctype}|{name}", sure=True)
		act.apply(action, reading)
	frappe.db.commit()


def carried(doc, method=None) -> None:
	"""Customer after_insert: a customer made from a lead keeps the lead's
	documents, as ERPNext keeps its mail and comments."""
	if not doc.get("lead_name"):
		return
	for one in frappe.get_all("File Link", filters={"for_doctype": "Lead", "for_name": doc.lead_name}, fields=["file", "reading"]):
		if not frappe.db.exists("File Link", {"file": one.file, "for_doctype": "Customer", "for_name": doc.name}):
			frappe.get_doc({"doctype": "File Link", "file": one.file, "for_doctype": "Customer", "for_name": doc.name, "reading": one.reading}).insert(ignore_permissions=True)


def applicant_arrived(doc, method=None) -> None:
	"""Job Applicant after_insert, by the form or a person: an application
	OneAI made from a mail for the same person, with no opening or this one,
	and nobody has touched, is folded into this one, which keeps its values.
	OneHR worked on is only flagged."""
	from onedesk.one_ai.reading import mark

	if frappe.flags.one_intake_writing or not doc.email_id:
		return
	for other in frappe.get_all("Job Applicant", filters={"email_id": doc.email_id, "name": ["!=", doc.name]}, fields=["name", "job_title"]):
		if other.job_title and other.job_title != doc.job_title:
			continue
		if mark.is_marked("Job Applicant", other.name):
			frappe.enqueue("onedesk.one_ai.reading.identity.fold", queue="short", enqueue_after_commit=True, doctype="Job Applicant", name=other.name, into=doc.name)
		elif doc.meta.has_field("one_duplicate_of"):
			doc.db_set({"one_duplicate_type": "Job Applicant", "one_duplicate_of": other.name, "one_duplicate_on": "email"}, update_modified=False)
		break


def _taxes_by_rate(company: str) -> dict[float, str]:
	"""The company's purchase tax templates by the rate they charge on the
	net, the default first where two charge the same."""
	rows = frappe.db.sql(
		"""select t.name, sum(c.rate) as rate from `tabPurchase Taxes and Charges Template` t
		join `tabPurchase Taxes and Charges` c on c.parent = t.name and c.parenttype = 'Purchase Taxes and Charges Template'
		where t.company = %s and t.disabled = 0 and c.charge_type = 'On Net Total' and c.add_deduct_tax = 'Add'
		group by t.name, t.is_default order by t.is_default desc, t.name""",
		company,
		as_dict=True,
	)
	found = {}
	for row in rows:
		if row.rate:
			found.setdefault(round(float(row.rate), 2), row.name)
	return found


def _parties(reading) -> dict:
	"""The records the document's sender, payee or recipient surely are."""
	return {row.matched_doctype: row.matched_name for row in reading.parties if row.matched_name and (row.score or 0) >= identity.CERTAIN and row.role in ("Sender", "Paid To", "Recipient")}


def _supplier(reading) -> str | None:
	return _parties(reading).get("Supplier") or (reading.party_name if reading.party_doctype == "Supplier" else None)


PROJECT_KINDS = ("Site Log", "Timesheet", "Change Request")


def _project_named(reading) -> str | None:
	"""The open project the document names, from what it says and its lines."""
	from onedesk.one_project import intake

	said = " ".join(filter(None, [reading.title, reading.summary, reading.text, *[row.get("text") for row in reading.lines]]))
	return intake.named(said)
