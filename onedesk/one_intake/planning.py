"""Stage 6 of Intake on the site: what `plans.py` needs to know, and the flows
it names.

`run` is called once a matter is quiet (matters.act_now). It finds out who
the sender is, which employee a document is about and whether the matter
already has a task, asks the pure planners what to do, and hands each action
to the door. Parties come first; the reading's parties are then matched
again, so the supplier just made is the record the invoice is filed with
and the Contact is linked to.

The flows are the functions a planner names in `Action.flow`: a task that is
assigned to somebody, an event that shows on their calendar, a customer made
from a lead through ERPNext's own conversion, and an employee made from an
accepted job offer through HRMS's.

Also here: somebody we knew before they had a record. When a Supplier,
Customer, Lead, Contact, Employee or Job Applicant is made, the readings
that named one of its identifiers and matched nobody are matched to it, and
their documents linked (docs/INTAKE.md §7).
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, today

from onedesk.one_hr.hiring import AUTHOR
from onedesk.one_intake import act, identity, matters, plans
from onedesk.one_intake import identifiers as ids

#: What a task step says for each ask, and what ticks it by itself.
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
		from onedesk.one_intake import money

		_money(ctx, reading)
		wanted = money.plan(said, ctx)
	else:
		_payable(ctx, reading)
		wanted = plans.second(said, ctx)
	for action in wanted:
		action.key = matters.key(reading, action.key) if action.key.startswith(("task", "event", "leave", "expense", "resignation", "employee", "books")) else f"{reading.key[:90]}|{action.key}"
		act.apply(action, reading)
	frappe.db.commit()
	if which == "parties" and wanted:
		rematch(reading)
	if which == "money" and wanted:
		from onedesk.one_intake import drafts

		drafts.maybe_submit(reading)
	if which == "rest":
		_tell_closer(reading, ctx)
		_warn_iban(reading)


def rematch(reading) -> None:
	"""Match the reading's parties again, now that records were made."""
	from onedesk.one_intake import understand

	changed = False
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


# ------------------------------------------------------------------ what the planners are told


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
	}
	_sender(ctx, mail, structured)
	_about(ctx, reading)
	_employee(ctx, reading)
	_task(ctx, reading)
	return ctx


def _words(language: str) -> dict:
	"""What OneAI writes on records, in the workspace's language."""
	return {
		"renew": _("Renew the {0} of {1}", lang=language),
		"document": _("document", lang=language),
		"sick_note": _("From a sick note that arrived by mail.", lang=language),
		"arrived": _("A document arrived", lang=language),
		"arrived_for": _("A document arrived for {0}", lang=language),
		"nudged": _("A reminder arrived: {0}", lang=language),
		"appointment": _("Appointment", lang=language),
		"asks": {one: _(one, lang=language) for one in ("Pay", "Sign", "Reply", "Attend", "Send", "Cancel", "Decide", "Other")},
		"moved": _("Dated after the books locked up to {0}.", lang=language),
		"direct_debit": _("Paid by direct debit.", lang=language),
		"paid": _("Already paid.", lang=language),
		"no_original": _("The invoice this credits was not found.", lang=language),
		"unmatched": _("Some lines match no item.", lang=language),
		"see_document": _("See the attached document.", lang=language),
		"ask_for_invoice": _("Ask {1} for invoice {0}", lang=language),
		"maybe_fraud": _("A reminder for an invoice nobody here has. Ask for the invoice before paying anything.", lang=language),
		"decide_cancel": _("Decide whether to cancel the contract with {0} (last day {1})", lang=language),
		"unordered": _("Check the delivery from {0}: no order of ours was found for it", lang=language),
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
		# Frappe's own contact from mail: no links, named after the address.
		ctx["sender_contact_bare"] = not links and first.lower() == email.split("@")[0].lower()
		ctx["sender_contact_phones"] = frappe.get_all("Contact Phone", filters={"parent": contact, "parenttype": "Contact"}, pluck="phone")
	best = (identity.match([(ids.EMAIL, email)]) or [None])[0]
	if best:
		ctx["sender_party"] = (best["doctype"], best["name"])
		if best["doctype"] == "Lead":
			ctx["sender_lead"] = best["name"]
	ctx["sender_company"] = None


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
	ctx["employee_document_numbers"] = frappe.get_all("Employee Document", filters={"parent": found, "parenttype": "Employee"}, pluck="number")
	if reading.kind == "Sick Note":
		from hrms.hr.doctype.leave_application.leave_application import get_employee_leave_approver

		from onedesk.one_hr import ai as hr_ai

		ctx["sick_leave_type"] = hr_ai._leave_type("sick", frappe.get_all("Leave Type", pluck="name"))
		ctx["leave_approver"] = get_employee_leave_approver(found)


def _task(ctx: dict, reading) -> None:
	"""The task the matter already has, and what ticks each new step."""
	readings = frappe.get_all("Reading", filters={"matter": reading.matter}, pluck="name") if reading.matter else [reading.name]
	made = frappe.db.get_value(
		"Intake Action",
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


def _tell_closer(reading, ctx: dict) -> None:
	"""A person's decision is not undone by a message: the task they closed
	stays closed, and they are told the matter moved."""
	held = ctx.get("task")
	if not held or held.status not in ("Completed", "Cancelled") or reading.change in ("Nothing New", "Closing", None):
		return
	closer = held.modified_by
	if not closer or closer == AUTHOR:
		return
	from onedesk.one import notify

	notify.notify(
		"Arrived After Closing",
		closer,
		record=("Task", held.name),
		sender=AUTHOR,
		dedupe_on=["document_type", "document_name", "subject"],
		title=reading.title or "",
	)


# ------------------------------------------------------------------ money


def _money(ctx: dict, reading) -> None:
	"""What the money planners need: the party's record, what came before
	(the order, the invoice a credit note credits, one already booked), the
	items the lines are, our bank account, and the books' lock."""
	ctx["books"] = not cint(frappe.db.get_single_value("Intake Settings", "household")) and frappe.db.count("Company") > 0
	if not ctx["books"]:
		return
	company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {}, "name")
	ctx["locked"] = str(frappe.db.get_value("Company", company, "accounts_frozen_till_date") or "") or None
	parties = {row.matched_doctype: row.matched_name for row in reading.parties if row.matched_name and (row.score or 0) >= identity.CERTAIN and row.role in ("Sender", "Paid To", "Recipient")}
	ctx["supplier"] = parties.get("Supplier") or (reading.party_name if reading.party_doctype == "Supplier" else None)
	ctx["customer"] = parties.get("Customer") or (reading.party_name if reading.party_doctype == "Customer" else None)
	ctx["contract_party"] = ("Supplier", ctx["supplier"]) if ctx["supplier"] else (("Customer", ctx["customer"]) if ctx["customer"] else None)
	ctx["file"] = frappe.db.get_value("File", {"one_reading": reading.name}, "name") or (reading.source_name if reading.source_doctype == "File" else None)
	refs = {row.kind: row.value for row in reading.refs}
	named = [row.value for row in reading.refs]
	if ctx["supplier"]:
		if reading.number:
			ctx["existing_invoice"] = frappe.db.get_value("Purchase Invoice", {"supplier": ctx["supplier"], "bill_no": reading.number, "docstatus": ["<", 2], "owner": ["!=", AUTHOR]}, "name")
		if refs.get("Invoice"):
			ctx["original_invoice"] = frappe.db.get_value("Purchase Invoice", {"supplier": ctx["supplier"], "bill_no": refs["Invoice"], "docstatus": 1, "is_return": 0}, "name")
		ctx["purchase_order"] = next((one for one in named if frappe.db.exists("Purchase Order", {"name": one, "supplier": ctx["supplier"], "docstatus": 1})), None)
		ctx["items"] = _items(reading, ctx["supplier"], "Item Supplier", "supplier", "supplier_part_no")
		# A habit, read from history with no model: where this supplier's
		# bills were booked last time, else the company's default.
		ctx["expense_account"] = frappe.db.sql(
			"""select item.expense_account from `tabPurchase Invoice Item` item
			join `tabPurchase Invoice` bill on bill.name = item.parent
			where bill.supplier = %s and bill.docstatus = 1 and ifnull(item.expense_account, '') != ''
			order by bill.posting_date desc limit 1""",
			ctx["supplier"],
		)
		ctx["expense_account"] = ctx["expense_account"][0][0] if ctx["expense_account"] else frappe.db.get_value("Company", company, "default_expense_account")
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
	Item Customer Detail), our item code, or an item of exactly that name.
	A line that is none of these stays words, and a new stock item is never
	made from a document."""
	out = {}
	for index, line in enumerate(reading.lines):
		found = None
		if line.code:
			found = frappe.db.get_value(table, {field: party, code: line.code, "parenttype": "Item"}, "parent") or (line.code if frappe.db.exists("Item", line.code) else None)
		if not found and line.text:
			found = frappe.db.get_value("Item", {"item_name": line.text.strip(), "disabled": 0}, "name")
		if found:
			out[index] = found
	if not out and len(reading.lines) == 1 and table == "Item Supplier":
		# A habit: a supplier who bills one thing a month is billed for what
		# it was booked to last time.
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


def _payable(ctx: dict, reading) -> None:
	"""The pay step ticks itself when the invoice this matter booked is
	submitted and paid. A document paid by direct debit, or already paid,
	asks nobody to pay."""
	readings = frappe.get_all("Reading", filters={"matter": reading.matter}, pluck="name") if reading.matter else [reading.name]
	booked = frappe.db.get_value("Intake Action", {"reading": ["in", readings], "kind": "Create", "target_doctype": "Purchase Invoice", "level": "Done"}, "target_name")
	if booked:
		ctx["done_when"]["Pay"] = json.dumps({"doctype": "Purchase Invoice", "name": booked, "all": [{"field": "docstatus", "equals": 1}, {"field": "outstanding_amount", "equals": 0}]})
	ctx["nobody_pays"] = reading.paid_how in ("Direct Debit", "Already Paid") or reading.kind == "Receipt"


def _warn_iban(reading) -> None:
	"""A known supplier's document asking to be paid to an IBAN we do not have
	for them is exactly what invoice fraud looks like: the person OneAI reads
	for is told at once, in red, and the IBAN is never written over ours."""
	if not reading.iban or reading.party_doctype != "Supplier" or not reading.party_name:
		return
	known = [one.replace(" ", "").upper() for one in frappe.get_all("Bank Account", filters={"party_type": "Supplier", "party": reading.party_name}, pluck="iban") if one]
	if not known or reading.iban.replace(" ", "").upper() in known:
		return
	from onedesk.one import notify

	notify.notify(
		"New IBAN",
		reading.on_behalf_of,
		record=("Reading", reading.name),
		sender=AUTHOR,
		dedupe_on=["document_type", "document_name", "subject"],
		title=reading.title or "",
		supplier=reading.party_name,
	)


# ------------------------------------------------------------------ flows


def make_task(values: dict):
	"""A task, assigned to the person it is for unless an Assignment Rule
	shares tasks out. Its steps say what ticks them."""
	values = dict(values)
	who = values.pop("assign_to", None)
	doc = frappe.get_doc({"doctype": "Task", **values})
	doc.flags.ignore_permissions = True
	# OneTask gives a task nobody holds to its maker, who is OneAI here.
	doc.flags.one_assigned = True
	doc.insert()
	if who and not frappe.db.exists("Assignment Rule", {"document_type": "Task", "disabled": 0}):
		from frappe.desk.form import assign_to

		assign_to._add({"doctype": "Task", "name": doc.name, "assign_to": [who], "description": doc.subject}, ignore_permissions=True)
	from onedesk.one_intake import steps

	steps.changed()
	return doc


def make_event(values: dict):
	"""An event, on the calendar of whoever it is for."""
	values = dict(values)
	who = values.pop("for", None)
	doc = frappe.get_doc({"doctype": "Event", **values})
	doc.flags.ignore_permissions = True
	doc.insert()
	if who:
		frappe.share.add_docshare("Event", doc.name, who, write=1, share=1, flags={"ignore_share_permission": True})
	return doc


def customer_from_lead(values: dict):
	"""A customer made the way ERPNext makes one from a lead, so the lead's
	mail and comments go with it."""
	from erpnext.crm.doctype.lead.lead import make_customer

	doc = make_customer(values["lead"])
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def employee_from_offer(values: dict):
	"""An employee made the way HRMS's Create Employee button makes one."""
	from hrms.hr.doctype.job_offer.job_offer import make_employee

	doc = make_employee(values["job_offer"])
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def debit_note(values: dict):
	"""A credit note, as ERPNext's return against the invoice it credits."""
	from erpnext.accounts.doctype.purchase_invoice.mapper import make_debit_note

	values = dict(values)
	doc = make_debit_note(values.pop("against"))
	doc.update(values)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def invoice_from_order(values: dict):
	"""An invoice, as ERPNext bills a Purchase Order, so it is matched to the
	order and its receipt."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice

	values = dict(values)
	doc = make_purchase_invoice(values.pop("order"))
	doc.update(values)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def receipt_from_order(values: dict):
	"""A supplier's delivery note, as ERPNext receives a Purchase Order."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	values = dict(values)
	doc = make_purchase_receipt(values.pop("order"))
	doc.update({key: value for key, value in values.items() if value})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc


def payment_for(values: dict):
	"""A customer's payment advice, as ERPNext's payment against our invoice."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	doc = get_payment_entry("Sales Invoice", values["invoice"], party_amount=values.get("amount"))
	doc.reference_no = values.get("reference_no")
	doc.reference_date = values.get("reference_date")
	doc.flags.ignore_permissions = True
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


# ------------------------------------------------------------------ somebody we knew before


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
	frappe.enqueue("onedesk.one_intake.planning.link_back", queue="long", enqueue_after_commit=True, doctype=doc.doctype, name=doc.name, rows=[dict(one) for one in rows])


def link_back(doctype: str, name: str, rows: list[dict]) -> None:
	from onedesk.one_intake.act import Action

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
	One HR worked on is only flagged."""
	from onedesk.one_intake import mark

	if frappe.flags.one_intake_writing or not doc.email_id:
		return
	for other in frappe.get_all("Job Applicant", filters={"email_id": doc.email_id, "name": ["!=", doc.name]}, fields=["name", "job_title"]):
		if other.job_title and other.job_title != doc.job_title:
			continue
		if mark.is_marked("Job Applicant", other.name):
			frappe.enqueue("onedesk.one_intake.identity.fold", queue="short", enqueue_after_commit=True, doctype="Job Applicant", name=other.name, into=doc.name)
		elif doc.meta.has_field("one_duplicate_of"):
			doc.db_set({"one_duplicate_type": "Job Applicant", "one_duplicate_of": other.name, "one_duplicate_on": "email"}, update_modified=False)
		break

