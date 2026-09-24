"""Intake, stage 7: money and goods, as drafts a person submits. Pure."""

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
MONEY = _load(ROOT / "money.py", {"_Action": ACT["Action"], "getdate": _getdate, "timedelta": timedelta})
STEPS = _load(ROOT / "steps.py", {"getdate": _getdate, "flt": lambda v, p=None: float(v or 0), "json": json}, {"holds", "passed"})

SAID = {
	"moved": "Dated after the books locked up to {0}.", "direct_debit": "Paid by direct debit.", "paid": "Already paid.",
	"no_original": "The invoice this credits was not found.", "unmatched": "Some lines match no item.", "see_document": "See the document.",
	"ask_for_invoice": "Ask {1} for invoice {0}", "maybe_fraud": "Ask for the invoice before paying anything.",
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
	tree = ast.parse((ROOT.parent / "hooks.py").read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
			keys = [key.value for key in node.value.keys if isinstance(key, ast.Constant)]
			assert len(keys) == len(set(keys)), f"{node.targets[0].id} names {sorted({k for k in keys if keys.count(k) > 1})} twice"
			for value in node.value.values:
				if isinstance(value, ast.Dict):
					inner = [key.value for key in value.keys if isinstance(key, ast.Constant)]
					assert len(inner) == len(set(inner)), f"{node.targets[0].id} repeats {sorted({k for k in inner if inner.count(k) > 1})}"
