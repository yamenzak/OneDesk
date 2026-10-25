"""Intake, stage 7: money and goods, as drafts a person submits. Pure."""

import ast
import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent / "onedesk" / "one_ai" / "reading"


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
DEADLINES = SimpleNamespace(**_load(ROOT / "deadlines.py", {"calendar": __import__("calendar"), "re": __import__("re"), "date": date, "timedelta": timedelta}))
MONEY = _load(ROOT / "money.py", {"_Action": ACT["Action"], "getdate": _getdate, "timedelta": timedelta, "deadlines": DEADLINES})
STEPS = _load(ROOT / "steps.py", {"getdate": _getdate, "flt": lambda v, p=None: float(v or 0), "json": json}, {"holds", "passed"})

SAID = {
	"moved": "Dated after the books locked up to {0}.", "direct_debit": "Paid by direct debit.", "paid": "Already paid.",
	"no_original": "The invoice this credits was not found.", "unmatched": "Some lines match no item.", "see_document": "See the document.",
	"ask_for_invoice": "Ask {1} for invoice {0}", "maybe_fraud": "Ask for the invoice before paying anything.",
	"decide_cancel": "Decide whether to cancel the contract with {0} (last day {1})",
}
CTX = {"books": True, "today": "2026-09-24", "said": SAID, "supplier": "Stadtwerke Köln GmbH", "person": "boss@acme.test"}
INVOICE = {
	"kind": "Invoice", "verdict": "Action", "number": "RE-1", "issued_on": "2026-09-01", "currency": "EUR", "net": 70.76, "gross": 84.2, "title": "Strom August",
	"dates": [{"what": "Due", "date": "2026-09-30"}],
	"lines": [{"text": "Strom August", "qty": 250, "unit_price": 0.28304, "amount": 70.76}],
}


def test_an_invoice_from_a_known_supplier_is_a_draft_with_its_lines():
	made = MONEY["purchase"](INVOICE, CTX)
	assert [(one.kind, one.doctype) for one in made] == [("Create", "Purchase Invoice")]
	values = made[0].values
	assert values["supplier"] == "Stadtwerke Köln GmbH" and values["bill_no"] == "RE-1" and values["due_date"] == "2026-09-30"
	assert values["items"] == [{"qty": 1, "rate": 70.76, "description": "250 × 0.28304 Strom August", "item_name": "Strom August", "uom": "Nos"}], "a price in tenths of a cent is booked at what the line cost"
	assert made[0].propose_on_error and not made[0].propose
	with_item = MONEY["purchase"](INVOICE, {**CTX, "items": {0: "ELECTRICITY"}})
	assert with_item[0].values["items"][0]["item_code"] == "ELECTRICITY" and "item_name" not in with_item[0].values["items"][0]


def test_a_bill_charges_the_tax_its_document_charges():
	rates = {5.0: "VAT 5%", 19.0: "VAT 19%"}
	assert MONEY["taxed_by"]({"net": 11100, "tax": 555}, rates) == "VAT 5%"
	assert MONEY["taxed_by"]({"net": 70.76, "tax": None}, rates) is None
	assert MONEY["taxed_by"]({"net": 100, "tax": 7}, rates) is None, "no template charges 7%"
	taxed = MONEY["purchase"]({**INVOICE, "tax": 13.44}, {**CTX, "purchase_taxes": rates})
	assert taxed[0].values["taxes_and_charges"] == "VAT 19%"
	assert "taxes_and_charges" not in MONEY["purchase"](INVOICE, {**CTX, "purchase_taxes": {5.0: "VAT 5%"}})[0].values


def test_nothing_is_booked_twice_or_by_a_household():
	assert MONEY["purchase"](INVOICE, {**CTX, "existing_invoice": "ACC-PINV-1", "file": "f1"})[0].kind == "Link", "somebody booked it first"
	assert MONEY["purchase"](INVOICE, {**CTX, "books": False}) == []
	assert MONEY["purchase"](INVOICE, {**CTX, "supplier": None}) == [], "an unknown issuer is never booked"
	assert MONEY["purchase"](INVOICE, {**CTX, "sender_is_colleague": True}) == [], "a colleague's receipt is their expense claim"
	assert MONEY["purchase"]({**INVOICE, "verdict": "Phishing"}, CTX) == []


def test_how_it_was_paid_is_said_and_a_locked_period_moves_the_date():
	debit = MONEY["purchase"]({**INVOICE, "paid_how": "Direct Debit"}, CTX)
	assert debit[0].values["remarks"] == "Paid by direct debit."
	locked = MONEY["purchase"](INVOICE, {**CTX, "locked": "2026-09-30"})
	assert locked[0].values["posting_date"] == "2026-10-01" and locked[0].values["remarks"].startswith("Dated after")
	assert MONEY["posting_day"]("2026-09-24", "2026-06-30") == ("2026-09-24", False)


def test_an_invoice_on_an_order_is_billed_from_the_order():
	made = MONEY["purchase"](INVOICE, {**CTX, "purchase_order": "PUR-ORD-1"})
	assert made[0].flow.endswith("invoice_from_order") and made[0].values["order"] == "PUR-ORD-1"


def test_a_credit_note_is_a_return_against_what_it_credits():
	credit = {**INVOICE, "kind": "Credit Note"}
	against = MONEY["purchase"](credit, {**CTX, "original_invoice": "ACC-PINV-7"})
	assert against[0].flow.endswith("debit_note") and against[0].values["against"] == "ACC-PINV-7"
	alone = MONEY["purchase"](credit, CTX)
	assert alone[0].propose and alone[0].values["is_return"] == 1 and alone[0].values["items"][0]["qty"] == -1


def test_an_order_is_a_sales_order_and_unknown_lines_make_it_a_proposal():
	order = {"kind": "Order", "verdict": "Action", "number": "B-77", "issued_on": "2026-09-20", "lines": [{"text": "Desk", "qty": 12, "unit_price": 199.0}, {"text": "Lamp", "qty": 12}]}
	ctx = {**CTX, "customer": "Nordwind AG", "customer_items": {0: "DESK-01", 1: "LAMP-01"}}
	made = MONEY["sales_order"](order, ctx)
	assert not made[0].propose and made[0].values["items"] == [{"item_code": "DESK-01", "qty": 12.0, "rate": 199.0}, {"item_code": "LAMP-01", "qty": 12.0}]
	assert made[0].values["delivery_date"] == "2026-10-01" and made[0].values["po_no"] == "B-77"
	partial = MONEY["sales_order"](order, {**ctx, "customer_items": {0: "DESK-01"}})
	assert partial[0].propose and partial[0].why == "Some lines match no item."


def test_a_statement_is_bank_transactions_and_nothing_else():
	lines = [{"date": "2026-09-02", "amount": -84.2, "text": "Stadtwerke RE-1", "key": "a"}, {"date": "2026-09-03", "amount": 1200.0, "text": "Nordwind", "key": "b"}]
	made = MONEY["bank"]({"kind": "Bank Statement", "verdict": ""}, {**CTX, "bank_account": "Main - Bank", "statement_lines": lines})
	assert [one.values["withdrawal"] for one in made] == [84.2, 0] and [one.values["deposit"] for one in made] == [0, 1200.0]
	assert all(one.sure for one in made)
	assert MONEY["bank"]({"kind": "Bank Statement"}, {**CTX, "statement_lines": lines}) == [], "not our account"


def test_a_contract_says_when_it_must_be_cancelled_and_somebody_decides():
	reading = {
		"kind": "Contract", "verdict": "Action", "notice_period": "drei Monate zum Vertragsende",
		"dates": [{"what": "Valid From", "date": "2026-01-01"}, {"what": "Valid Until", "date": "2026-12-31"}],
	}  # fmt: skip
	made = MONEY["contract"](reading, {**CTX, "contract_party": ("Supplier", "Stadtwerke Köln GmbH")})
	assert made[0].values["one_cancel_by"] == "2026-09-30"
	assert made[0].values["end_date"] == "2026-12-31"
	task = made[1]
	assert task.doctype == "Task" and "2026-09-30" in task.values["subject"]
	assert task.values["exp_end_date"] == "2026-09-24", "a month before, but never in the past"
	assert task.key == "task|contract"
	without = MONEY["contract"]({**reading, "notice_period": None}, {**CTX, "contract_party": ("Supplier", "X")})
	assert len(without) == 1 and "one_cancel_by" not in without[0].values


def test_a_reminder_for_an_invoice_nobody_has_is_a_warning():
	reminder = {"kind": "Reminder", "verdict": "Action", "change": "New", "refs": [{"kind": "Invoice", "value": "RE-404"}]}
	made = MONEY["never_received"](reminder, {**CTX, "sender_title": "Unbekannt GmbH"})
	assert made[0].values["subject"] == "Ask Unbekannt GmbH for invoice RE-404" and made[0].values["priority"] == "High"
	assert MONEY["never_received"](reminder, {**CTX, "invoice_known": True}) == []
	assert MONEY["never_received"]({**reminder, "change": "Nudge"}, CTX) == [], "placed with its invoice"


def test_pay_ticks_when_the_invoice_is_submitted_and_paid():
	holds = STEPS["holds"]
	when = {"all": [{"field": "docstatus", "equals": 1}, {"field": "outstanding_amount", "equals": 0}]}
	assert holds(when, {"docstatus": 1, "outstanding_amount": 0.0})
	assert not holds(when, {"docstatus": 1, "outstanding_amount": 20.0}), "an instalment is not paid"
	assert not holds(when, {"docstatus": 0, "outstanding_amount": 0.0}), "a draft is not paid"


def test_money_is_pure_and_nothing_is_submitted_by_it():
	source = (ROOT / "money.py").read_text()
	assert "frappe." not in source.replace("from frappe.utils import getdate", "")
	assert ".submit(" not in source
	drafts = (ROOT / "drafts.py").read_text()
	assert 'doc.check_permission("submit")' in drafts, "Submit all submits as the person pressing it"
	assert '"submit_einvoices"' in drafts


def test_every_money_draft_is_written_as_the_person():
	made = MONEY["plan"](INVOICE, CTX)
	assert made and all(one.as_person for one in made)


def test_no_hook_table_names_a_doctype_twice():
	"""A second key for the same doctype in a hooks dict silently replaces the
	first, and every hook under it stops running."""
	tree = ast.parse((ROOT.parents[1] / "hooks.py").read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
			keys = [key.value for key in node.value.keys if isinstance(key, ast.Constant)]
			assert len(keys) == len(set(keys)), f"{node.targets[0].id} names {sorted({k for k in keys if keys.count(k) > 1})} twice"
			for value in node.value.values:
				if isinstance(value, ast.Dict):
					inner = [key.value for key in value.keys if isinstance(key, ast.Constant)]
					assert len(inner) == len(set(inner)), f"{node.targets[0].id} repeats {sorted({k for k in inner if inner.count(k) > 1})}"


def test_a_suppliers_timesheet_is_a_draft_bill_on_its_project_not_its_order():
	timesheet = {**INVOICE, "kind": "Timesheet", "lines": [{"text": "Fitters", "qty": 24, "unit_price": 95, "amount": 2280}]}
	made = MONEY["purchase"](timesheet, {**CTX, "said": {**SAID, "timesheet": "From their timesheet."}, "project": "PROJ-1", "purchase_order": "PO-1"})
	assert [(one.kind, one.doctype) for one in made] == [("Create", "Purchase Invoice")]
	values = made[0].values
	assert values["project"] == "PROJ-1" and values["remarks"] == "From their timesheet." and "order" not in values
	assert values["items"][0]["qty"] == 24 and values["items"][0]["rate"] == 95 and values["items"][0]["project"] == "PROJ-1"


def test_a_customers_request_for_extra_work_is_a_quotation_on_their_project():
	request = {"kind": "Change Request", "verdict": "Action", "lines": [{"text": "Glass balustrade", "qty": 6}, {"text": "Painting"}]}
	ctx = {**CTX, "customer": "Mansour & Sons", "project": "PROJ-1", "customer_items": {0: "BAL-GL"}}
	made = MONEY["extra_work"](request, ctx)
	assert [(one.kind, one.doctype) for one in made] == [("Create", "Quotation")]
	values = made[0].values
	assert values["party_name"] == "Mansour & Sons" and values["project"] == "PROJ-1" and values["one_extra_work"] == 1
	assert values["items"] == [{"item_code": "BAL-GL", "qty": 6.0}]
	assert made[0].propose, "a line that is no item waits for a person"
	assert MONEY["extra_work"](request, {**ctx, "project": None}) == [], "not their project, or none named"


DELIVERY = {"kind": "Delivery Note", "verdict": "Information", "number": "DN-778", "lines": [{"text": "Aluminium profile 6063", "qty": 50}]}


def test_a_suppliers_delivery_note_is_a_draft_receipt_against_its_order():
	made = MONEY["goods"](DELIVERY, {**CTX, "purchase_order": "PO-1"})
	assert [(one.kind, one.doctype) for one in made] == [("Create", "Purchase Receipt")]
	assert made[0].values == {"order": "PO-1", "supplier_delivery_note": "DN-778"}
	assert made[0].flow == "onedesk.one_ai.reading.planning.receipt_from_order" and made[0].propose_on_error
	assert MONEY["goods"](DELIVERY, CTX) == [], "no order, no receipt"
	assert MONEY["goods"]({**DELIVERY, "kind": "Invoice"}, {**CTX, "purchase_order": "PO-1"}) == []
	assert MONEY["goods"](DELIVERY, {**CTX, "purchase_order": "PO-1", "books": False}) == []


def test_a_delivery_nobody_ordered_is_a_task_to_check_it():
	MONEY["task_in"] = lambda project, day: project
	said = {**SAID, "unordered": "Check a delivery from {0} nobody ordered"}
	made = MONEY["unordered"](DELIVERY, {**CTX, "said": said, "project": "PROJ-1"})
	assert [(one.kind, one.doctype) for one in made] == [("Create", "Task")]
	values = made[0].values
	assert values["subject"] == "Check a delivery from Stadtwerke Köln GmbH nobody ordered"
	assert values["one_about_doctype"] == "Supplier" and values["one_about"] == "Stadtwerke Köln GmbH"
	assert values["assign_to"] == "boss@acme.test" and values["project"] == "PROJ-1" and values["exp_end_date"] == "2026-09-24"
	assert MONEY["unordered"](DELIVERY, {**CTX, "said": said, "purchase_order": "PO-1"}) == [], "an ordered delivery is a receipt"
	assert MONEY["unordered"](DELIVERY, {**CTX, "said": said, "supplier": None}) == [], "an unknown sender is not a supplier"
	assert MONEY["unordered"]({**DELIVERY, "change": "Reminder"}, {**CTX, "said": said}) == [], "only the first word about it"


def test_a_suppliers_offer_is_a_supplier_quotation_when_every_line_is_an_item():
	offer = {
		"kind": "Offer", "verdict": "Action",
		"dates": [{"what": "Valid Until", "date": "2026-10-31"}],
		"lines": [{"text": "Profile 6063", "qty": 100, "unit_price": 42.5}, {"text": "EPDM seal", "qty": 20, "amount": 60}],
	}
	made = MONEY["quotation"](offer, {**CTX, "items": {0: "ALU-6063", 1: "SEAL-EPDM"}})
	assert [(one.kind, one.doctype) for one in made] == [("Create", "Supplier Quotation")]
	values = made[0].values
	assert values["supplier"] == "Stadtwerke Köln GmbH" and values["valid_till"] == "2026-10-31" and values["transaction_date"] == "2026-09-24"
	assert values["items"] == [{"item_code": "ALU-6063", "qty": 100.0, "rate": 42.5}, {"item_code": "SEAL-EPDM", "qty": 20.0, "rate": 3.0}], "a line with only its total is priced for one"
	assert made[0].as_person, "written as the person OneAI acts for"
	assert MONEY["quotation"](offer, {**CTX, "items": {0: "ALU-6063"}}) == [], "a line that is no item leaves it to a person"
	assert MONEY["quotation"]({**offer, "lines": []}, {**CTX, "items": {}}) == []
	assert MONEY["quotation"](offer, {**CTX, "supplier": None, "items": {0: "ALU-6063", 1: "SEAL-EPDM"}}) == []
