"""Intake, stage 6: what each kind of document makes. Pure."""

import ast
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "onedesk" / "one_intake"


def _getdate(value):
	return value if isinstance(value, date) else date.fromisoformat(str(value)[:10])


def _load(path, space, names=None):
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, (ast.Import, ast.ImportFrom)):
			continue
		named = getattr(node, "name", None) or (getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None)
		if names is None or named in names:
			exec(ast.unparse(node), space)
	return space


ACT = _load(ROOT / "act.py", {"dataclass": dataclass, "field": field, "hashlib": hashlib, "json": json, "cint": lambda v: int(v or 0), "flt": lambda v, p=None: float(v or 0)}, {"KINDS", "FLOOR", "CHANGES", "Action", "level", "_filled", "_same"})
Action = ACT["Action"]
PLANS = _load(ROOT / "plans.py", {"Action": Action, "getdate": _getdate, "timedelta": timedelta})
STEPS = _load(ROOT / "steps.py", {"getdate": _getdate, "flt": lambda v, p=None: float(v or 0), "json": json}, {"holds", "passed"})

SAID = {
	"renew": "Renew the {0} of {1}", "document": "document", "sick_note": "From a sick note.", "arrived": "A document arrived",
	"arrived_for": "A document arrived for {0}", "nudged": "A reminder arrived: {0}", "appointment": "Appointment",
	"asks": {"Pay": "Pay", "Reply": "Reply", "Attend": "Attend", "Sign": "Sign", "Send": "Send", "Other": "Other"},
}
CTX = {"today": "2026-09-24", "person": "hr@acme.test", "said": SAID, "supplier_group": "Services", "customer_group": "Commercial", "territory": "Germany", "done_when": {}}
SELLER = {"role": "Sender", "party_name": "Stadtwerke Köln GmbH", "vat_id": "DE123456789"}
INVOICE = {"name": "r1", "kind": "Invoice", "verdict": "Action", "title": "Stadtwerke RE-1", "parties": [SELLER], "confidence": 90}


def kinds(actions):
	return [(one.kind, one.doctype) for one in actions]


# ------------------------------------------------------------------ parties


def test_an_invoice_from_somebody_new_makes_a_supplier():
	made = PLANS["parties"](INVOICE, CTX)
	assert kinds(made) == [("Create", "Supplier")]
	assert made[0].values == {"supplier_name": "Stadtwerke Köln GmbH", "supplier_group": "Services", "supplier_type": "Company", "tax_id": "DE123456789"}
	assert made[0].confidence == 0.9


def test_a_name_alone_makes_nobody():
	named = {**INVOICE, "parties": [{"role": "Sender", "party_name": "Stadtwerke"}]}
	assert PLANS["parties"](named, CTX) == []
	assert PLANS["parties"]({**INVOICE, "parties": [{**SELLER, "matched_doctype": "Supplier", "matched_name": "S"}]}, CTX) == [], "known already"
	assert PLANS["parties"]({**INVOICE, "verdict": "Advertising"}, CTX) == []
	assert PLANS["parties"](INVOICE, {**CTX, "history": 1}) == [], "history is read, never acted on"
	assert PLANS["parties"]({**INVOICE, "change": "Nothing New"}, CTX) == []


def test_an_order_makes_a_customer_through_the_lead_when_there_is_one():
	order = {**INVOICE, "kind": "Order", "parties": [{"role": "Sender", "party_name": "Maria Weber", "is_person": 1}]}
	made = PLANS["parties"](order, CTX)
	assert made[0].values["customer_type"] == "Individual"
	through = PLANS["parties"](order, {**CTX, "sender_lead": "CRM-LEAD-1"})
	assert through[0].flow == "onedesk.one_intake.planning.customer_from_lead" and through[0].values == {"lead": "CRM-LEAD-1"}


def test_an_inquiry_makes_a_lead_and_a_cv_an_applicant():
	inquiry = {**INVOICE, "kind": "Inquiry", "parties": [{"role": "Sender", "party_name": "Nordwind AG", "email": "anna@nordwind.example"}]}
	lead = PLANS["parties"](inquiry, {**CTX, "sender_name": "Anna Berg"})
	assert kinds(lead) == [("Create", "Lead")] and lead[0].values["company_name"] == "Nordwind AG" and lead[0].values["first_name"] == "Anna"
	cv = {**INVOICE, "kind": "CV", "parties": [{"role": "Holder", "party_name": "Maria Weber", "email": "maria@mail.example"}]}
	applicant = PLANS["parties"](cv, CTX)
	assert applicant[0].values == {"applicant_name": "Maria Weber", "email_id": "maria@mail.example"}, "no opening unless the mail named one"
	assert PLANS["parties"](cv, {**CTX, "sender_is_colleague": True}) == [], "a colleague forwarding a CV is not the candidate"


def test_our_own_sent_mail_makes_no_party():
	assert PLANS["parties"](INVOICE, {**CTX, "direction": "Sent"}) == []


# ------------------------------------------------------------------ the sender


def test_a_contact_is_made_once_and_a_bare_one_completed():
	ctx = {**CTX, "direction": "Received", "sender_email": "anna@nordwind.example", "sender_name": "Anna Berg", "sender_party": ("Supplier", "Nordwind AG")}
	made = PLANS["contact"](INVOICE, ctx)
	assert kinds(made) == [("Create", "Contact")]
	assert made[0].values["links"] == [{"link_doctype": "Supplier", "link_name": "Nordwind AG"}]
	bare = PLANS["contact"](INVOICE, {**ctx, "sender_contact": "anna", "sender_contact_bare": True, "sender_contact_links": []})
	assert kinds(bare) == [("Update", "Contact"), ("Add", "Contact")]
	assert bare[0].over == ("first_name",), "Frappe's placeholder name is filled, not proposed"
	assert PLANS["contact"](INVOICE, {**ctx, "sender_contact": "anna", "sender_contact_links": [("Supplier", "Nordwind AG")]}) == []
	assert PLANS["contact"](INVOICE, {**ctx, "sender_is_colleague": True}) == []
	assert PLANS["contact"]({**INVOICE, "verdict": "Spam"}, ctx) == [], "junk makes no contacts"


# ------------------------------------------------------------------ a person's documents

EMPLOYEE_CTX = {**CTX, "employee": "HR-EMP-1", "employee_name": "Ahmad Ali", "employee_document_numbers": [], "file_url": "/private/files/p.pdf"}
PASSPORT = {"kind": "Identity Document", "verdict": "Action", "document_type": "Passport", "number": "N1234567", "valid_until": "2031-03-01", "issued_on": "2021-03-02", "issuing_country": "Syria", "parties": []}


def test_a_passport_is_a_row_on_the_employee_and_a_task_before_it_runs_out():
	made = PLANS["employee_documents"](PASSPORT, EMPLOYEE_CTX)
	assert kinds(made) == [("Add", "Employee"), ("Create", "Task")]
	assert made[0].values["table"] == "one_documents" and made[0].values["row"]["number"] == "N1234567"
	assert made[1].values["exp_end_date"] == "2030-12-31", "sixty days before a passport runs out"
	assert made[1].values["subject"] == "Renew the Passport of Ahmad Ali"
	permit = PLANS["employee_documents"]({**PASSPORT, "document_type": "Residence Permit"}, EMPLOYEE_CTX)
	assert permit[1].values["exp_end_date"] == "2030-12-01", "ninety for a residence permit"
	assert PLANS["employee_documents"](PASSPORT, {**EMPLOYEE_CTX, "employee_document_numbers": ["N1234567"]}) == [], "the same passport twice"


def test_a_sick_note_is_a_leave_application_and_a_refusal_is_a_proposal():
	note = {"kind": "Sick Note", "verdict": "Action", "dates": [{"what": "Valid From", "date": "2026-09-22"}, {"what": "Valid Until", "date": "2026-09-25"}], "parties": []}
	made = PLANS["employee_documents"](note, {**EMPLOYEE_CTX, "sick_leave_type": "Sick Leave", "leave_approver": "boss@acme.test"})
	assert made[0].values["from_date"] == "2026-09-22" and made[0].values["to_date"] == "2026-09-25" and made[0].values["status"] == "Open"
	assert made[0].propose_on_error


def test_a_resignation_is_only_proposed_and_a_signed_offer_waits_for_a_person():
	resignation = {"kind": "Resignation", "verdict": "Action", "issued_on": "2026-09-20", "dates": [{"what": "Valid Until", "date": "2026-10-31"}]}
	made = PLANS["employee_documents"](resignation, EMPLOYEE_CTX)
	assert made[0].ends_employment and made[0].values == {"resignation_letter_date": "2026-09-20", "relieving_date": "2026-10-31"}
	level = ACT["level"](made[0], {}, {})
	assert level[0] == "Proposed"
	offer = PLANS["employee_documents"]({"kind": "Contract", "verdict": "Action"}, {**EMPLOYEE_CTX, "accepted_offer": "HR-OFF-1"})
	assert offer[0].propose and offer[0].flow.endswith("employee_from_offer")


def test_an_employees_receipt_is_their_expense_claim():
	receipt = {"kind": "Receipt", "verdict": "Action", "gross": 23.5, "currency": "EUR", "issued_on": "2026-09-21", "title": "Taxi to the airport"}
	ctx = {**CTX, "sender_employee": "HR-EMP-1", "expense_type": "Travel", "company_currency": "EUR"}
	made = PLANS["receipt"](receipt, ctx)
	assert made[0].values["expenses"][0] == {"expense_date": "2026-09-21", "expense_type": "Travel", "description": "Taxi to the airport", "amount": 23.5}
	assert PLANS["receipt"]({**receipt, "currency": "USD"}, ctx) == [], "never a rate OneAI made up"


# ------------------------------------------------------------------ tasks


REMINDER = {"name": "r2", "kind": "Reminder", "verdict": "Action", "title": "Mahnung", "summary": "Pay RE-1.", "sensitivity": "Ordinary", "asks": [{"what": "Pay", "detail": "RE-1", "by_date": "2026-10-01"}]}


def test_a_new_matter_with_asks_gets_one_task_with_a_step_per_ask():
	ctx = {**CTX, "about": ("Supplier", "Stadtwerke Köln GmbH"), "done_when": {"Reply": '{"reply_in": "t1"}'}}
	reading = {**REMINDER, "asks": [*REMINDER["asks"], {"what": "Reply", "detail": ""}]}
	made = PLANS["tasks"](reading, ctx)
	assert kinds(made) == [("Create", "Task")] and made[0].key == "task"
	assert made[0].values["one_steps"] == [{"step": "Pay: RE-1"}, {"step": "Reply", "done_when": '{"reply_in": "t1"}'}]
	assert made[0].values["exp_end_date"] == "2026-10-01" and made[0].values["assign_to"] == "hr@acme.test"


def test_a_sensitive_document_names_nothing_on_its_task():
	made = PLANS["tasks"]({**REMINDER, "sensitivity": "Medical", "title": "Befund Dr. Weber"}, {**CTX, "about_title": "Ahmad Ali"})
	assert made[0].values["subject"] == "A document arrived for Ahmad Ali" and "description" not in made[0].values


def test_a_later_document_nudges_moves_or_closes_the_matters_task():
	held = {"name": "TASK-1", "status": "Open", "priority": "Medium", "exp_end_date": "2026-10-15"}
	nudged = PLANS["tasks"]({**REMINDER, "change": "Nudge"}, {**CTX, "task": held})
	assert kinds(nudged) == [("Update", "Task"), ("Comment", "Task")]
	assert nudged[0].values == {"priority": "High", "exp_end_date": "2026-10-01"}
	closed = PLANS["tasks"]({**REMINDER, "change": "Closing"}, {**CTX, "task": held})
	assert closed[0].values == {"status": "Completed"}
	assert PLANS["tasks"]({**REMINDER, "change": "Nudge"}, {**CTX, "task": {**held, "status": "Completed"}}) == [], "a person's decision stands"
	assert PLANS["tasks"]({**REMINDER, "change": "Nothing New"}, CTX) == []


def test_our_own_mail_makes_tasks_only_of_what_it_promised():
	sent = {"kind": "Letter", "verdict": "Action", "asks": [{"what": "Other", "detail": "Send the offer", "by_date": "2026-09-26", "promise": 1}, {"what": "Sign", "detail": "the contract"}]}
	ctx = {**CTX, "direction": "Sent", "sender_user": "sales@acme.test"}
	assert PLANS["tasks"](sent, ctx) == [], "what we ask others is theirs to do"
	made = PLANS["promises"](sent, ctx)
	assert len(made) == 1 and made[0].values == {"subject": "Send the offer", "exp_end_date": "2026-09-26", "assign_to": "sales@acme.test"}


def test_an_appointment_is_an_event_for_whoever_it_is_for():
	appointment = {"kind": "Appointment", "verdict": "Action", "title": "Zahnarzt", "dates": [{"what": "Appointment", "date": "2026-10-02"}]}
	made = PLANS["event"](appointment, CTX)
	assert made[0].values["starts_on"] == "2026-10-02 09:00:00" and made[0].values["all_day"] == 1 and made[0].values["for"] == "hr@acme.test"


# ------------------------------------------------------------------ steps


def test_a_step_ticks_itself_by_the_record_it_waits_for():
	holds, passed = STEPS["holds"], STEPS["passed"]
	assert holds({"field": "outstanding_amount", "equals": 0}, 0.0)
	assert not holds({"field": "outstanding_amount", "equals": 0}, 12.5), "a cancelled payment opens it again"
	assert holds({"field": "status", "in": ["Approved", "Rejected"]}, "Rejected")
	assert passed({"after": "2026-09-20"}, "2026-09-24") and not passed({"after": "2026-09-24"}, "2026-09-24")


def test_a_placeholder_is_filled_rather_than_proposed():
	level = ACT["level"]
	placeholder = Action("Update", "Contact", "info", {"first_name": "Anna"}, over=("first_name",))
	assert level(placeholder, {}, {"first_name": "info"})[0] == "Done"
	assert level(Action("Update", "Contact", "info", {"first_name": "Anna"}), {}, {"first_name": "Annie"})[0] == "Proposed"
	assert level(Action("Update", "Task", "T", {"priority": "High"}), {}, {"priority": "Medium"}, marked=True)[0] == "Done", "OneAI's own task"


def test_planners_are_pure():
	source = (ROOT / "plans.py").read_text()
	assert "import frappe\n" not in source and "frappe." not in source.replace("from frappe.utils import getdate", "")
	for write in (".insert(", ".save(", "db.", "enqueue("):
		assert write not in source, f"plans.py writes with {write}; that is the door's"


def test_flows_that_check_the_signed_in_user_are_written_as_the_person():
	source = (ROOT / "plans.py").read_text()
	assert '"Leave Application"' in source and source.count("as_person=True") == 2
	act = (ROOT / "act.py").read_text()
	assert "with as_oneai(person if action.as_person else None):" in act


def test_a_document_teaches_its_parties_what_they_lack():
	reading = {"verdict": "Action", "parties": [
		{"role": "Sender", "matched_doctype": "Supplier", "matched_name": "S1", "score": 0.99, "vat_id": "DE123456789", "website": "stadtwerke.example", "phone": "+49 221 1"},
		{"role": "Mentioned", "matched_doctype": "Customer", "matched_name": "C1", "score": 0.5, "vat_id": "DE9"},
		{"role": "Recipient", "matched_doctype": "Company", "matched_name": "Us", "score": 1, "ours": "Company"},
	]}
	made = PLANS["enrich"](reading, {**CTX, "direction": "Received", "sender_contact": "Anna", "sender_contact_phones": []})
	assert [(one.kind, one.doctype, one.name) for one in made] == [("Update", "Supplier", "S1"), ("Add", "Contact", "Anna")]
	assert made[0].values == {"tax_id": "DE123456789", "website": "stadtwerke.example"}
	assert not made[0].over, "a value the supplier already has is proposed, never overwritten"
	assert PLANS["enrich"](reading, {**CTX, "direction": "Sent"}) == []
