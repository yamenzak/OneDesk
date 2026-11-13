"""What an invoice's and a bill's page say above their fields: what is still
owed and when it was due, and Record Payment, which settles it in one step
(paid.py); and what a customer's and a supplier's page say: what they owe or
are owed, what is late, what was billed this year against last, and their
billing month by month. See one/head.py.
"""

import json
from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import date_diff, flt, fmt_money, formatdate, getdate, today

from onedesk.one import figures, stages
from onedesk.one.company import company_currency, reader_company
from onedesk.one_book import paid

OWED = [["docstatus", "=", 1], ["is_return", "=", 0]]


def _owed(doc, value) -> str:
	"""What is still owed, in the currency ERPNext keeps it in: the party
	account's."""
	return fmt_money(flt(value), currency=doc.get("party_account_currency") or doc.currency)


def _due_on(doc):
	"""When the next part still owed falls due, as ERPNext's status reads it:
	the earliest unpaid row of the schedule, not the last (a retention held
	for a year). The invoice's own due date when it has no schedule. Pure over
	the record."""
	unpaid = [row.due_date for row in doc.get("payment_schedule") or [] if flt(row.outstanding) > 0]
	return min(unpaid) if unpaid else doc.due_date


def _late(doc) -> int | None:
	"""Days past due while something is owed; nought on the day. Pure over the
	record."""
	if flt(doc.outstanding_amount) <= 0 or not _due_on(doc):
		return None
	return date_diff(today(), _due_on(doc))


def outstanding(doc):
	late = _late(doc)
	tone = "quiet" if flt(doc.outstanding_amount) <= 0 else ("alarm" if late and late > 0 else None)
	return {"value": _owed(doc, doc.outstanding_amount), "tone": tone}


def due(doc):
	if not _due_on(doc):
		return None
	late = _late(doc)
	if late is None:
		return None
	when = formatdate(_due_on(doc))
	if late > 0:
		return {"value": when, "tone": "alarm"}
	if late == 0:
		return {"value": _("Today"), "tone": "waiting"}
	return _("{0} · in {1} days").format(when, -late)


def _party(doc) -> str:
	if doc.doctype == "Sales Invoice":
		return doc.customer_name or doc.customer
	return doc.supplier_name or doc.supplier


def _before(doc) -> tuple[list, list]:
	"""The orders and the deliveries or receipts the invoice bills."""
	if doc.doctype == "Sales Invoice":
		order, moved = "sales_order", "delivery_note"
	else:
		order, moved = "purchase_order", "purchase_receipt"
	rows = doc.get("items") or []
	return [row.get(order) for row in rows if row.get(order)], [
		row.get(moved) for row in rows if row.get(moved)
	]


def progress(doc):
	"""Ordered and delivered or received when it was, billed, paid: where the
	invoice stands, as Frappe Books' status pill says it, on a track."""
	if doc.docstatus != 1 or doc.is_return:
		return None
	orders, moved = _before(doc)
	selling = doc.doctype == "Sales Invoice"
	owed = flt(doc.outstanding_amount)
	late = _late(doc)
	if owed <= 0:
		note = _("All")
	elif late and late > 0:
		note = _("{0} late").format(stages.days(late))
	else:
		note = stages.share(
			(flt(doc.grand_total) - owed) / flt(doc.grand_total) * 100 if flt(doc.grand_total) else 0
		)
	return stages.track(
		orders and stages.step(_("Ordered"), "done"),
		(moved or doc.get("update_stock"))
		and stages.step(_("Delivered") if selling else _("Received"), "done"),
		stages.step(_("Billed"), "done", formatdate(doc.posting_date)),
		stages.step(_("Paid"), stages.at(owed <= 0, True, bool(late and late > 0)), note),
	)


def said(doc):
	"""Where the invoice stands, in a sentence: one thing a sentence."""
	party = _party(doc)
	selling = doc.doctype == "Sales Invoice"
	what = (
		_("A draft. Submit it to bill {0}.")
		if selling
		else _("A draft. Submit it to record what {0} billed.")
	)
	if found := stages.draft(doc, what.format(party)):
		return found
	if doc.is_return:
		text = _("A credit note to {0}.") if selling else _("A debit note from {0}.")
		return {"text": text.format(party), "colour": "gray"}
	owed = flt(doc.outstanding_amount)
	if owed <= 0:
		if doc.status in ("Credit Note Issued", "Debit Note Issued"):
			return {"text": _("Settled by a return."), "colour": "gray"}
		return {"text": _("Paid in full."), "colour": "green"}
	late = _late(doc)
	if late and late > 0:
		text = _("{0} late. {1} still owes {2}.") if selling else _("{0} late. {2} still to pay {1}.")
		return {"text": text.format(stages.days(late), party, _owed(doc, owed)), "colour": "red"}
	if late == 0:
		return {"text": _("{0} falls due today.").format(_owed(doc, owed)), "colour": "orange"}
	text = _("{0} still owed by {1}.") if selling else _("{0} still to pay {1}.")
	return {"text": text.format(_owed(doc, owed), party), "colour": "orange"}


def repeats(doc):
	"""A repeating invoice says how often, and when the next one is made."""
	if not doc.auto_repeat:
		return None
	found = frappe.db.get_value(
		"Auto Repeat", doc.auto_repeat, ["frequency", "next_schedule_date", "status"], as_dict=True
	)
	if not found:
		return None
	route = f"/desk/auto-repeat/{doc.auto_repeat}"
	if found.status == "Active" and found.next_schedule_date:
		return {
			"label": _("Repeats {0}").format(_(found.frequency)),
			"value": _("Next on {0}").format(formatdate(found.next_schedule_date)),
			"route": route,
		}
	return {"value": _(found.status), "tone": "quiet", "route": route}


BILLS = {"Customer": ("Sales Invoice", "customer"), "Supplier": ("Purchase Invoice", "supplier")}

COUNTED = {"docstatus": 1, "is_return": 0}


def _bills(party_doctype: str, party: str, since=None, fields=None) -> list | None:
	"""A party's invoices as the reader's list would give them, or None when
	the reader may not see that list at all."""
	doctype, field = BILLS[party_doctype]
	if not frappe.has_permission(doctype, "read"):
		return None
	filters = {field: party, "company": reader_company(), **COUNTED}
	if since:
		filters["posting_date"] = [">=", since]
	return frappe.get_list(
		doctype,
		filters=filters,
		fields=fields or ["posting_date", "base_grand_total"],
		limit_page_length=0,
	)


def _party_money(value) -> str:
	return fmt_money(flt(value), currency=company_currency())


def party_overdue(doc):
	"""What is past due, part by part as each invoice's payment schedule falls
	due (home.parts), as ERPNext's Overdue status and OneBook's Home read it."""
	from onedesk.one_book import home

	rows = _bills(doc.doctype, doc.name, fields=["name", "outstanding_amount", "conversion_rate", "due_date", "party_account_currency"])
	if not rows:
		return None
	owing = [row for row in rows if flt(row.outstanding_amount) > 0]
	schedule = home._schedule(BILLS[doc.doctype][0], [row.name for row in owing])
	day = getdate()
	late = [
		part
		for row in owing
		for part in home.parts(
			{
				"outstanding_amount": flt(row.outstanding_amount) * (flt(row.conversion_rate or 1) if row.party_account_currency and row.party_account_currency != company_currency() else 1),
				"own": flt(row.outstanding_amount),
				"due_date": row.due_date,
			},
			schedule.get(row.name),
		)
		if part["due_date"] and getdate(part["due_date"]) < day
	]
	if not late:
		return None
	oldest = max(date_diff(today(), part["due_date"]) for part in late)
	return {
		"value": _party_money(sum(part["outstanding_amount"] for part in late)),
		"label": _("Overdue · oldest {0} days").format(oldest),
		"tone": "alarm",
	}


def party_last_bill(doc):
	doctype, field = BILLS[doc.doctype]
	if not frappe.has_permission(doctype, "read"):
		return None
	found = frappe.get_list(
		doctype,
		filters={field: doc.name, "company": reader_company(), **COUNTED},
		fields=["name", "posting_date", "base_grand_total"],
		order_by="posting_date desc, creation desc",
		limit_page_length=1,
	)
	if not found:
		return {"value": _("None yet"), "tone": "quiet"}
	last = found[0]
	label = _("Last Sales Invoice") if doc.doctype == "Customer" else _("Last Purchase Invoice")
	return {
		"label": _("{0} · {1}").format(label, formatdate(last.posting_date)),
		"value": _party_money(last.base_grand_total),
		"route": f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{last.name}",
	}


def _billed(party_doctype: str, party: str, marked_day=None) -> dict | None:
	"""A party's billing over the last twelve months, one bar a month."""
	day = getdate()
	starts = figures.months(day)
	rows = _bills(party_doctype, party, since=starts[0])
	if not rows:
		return None
	values = figures.by_month(((getdate(row.posting_date), row.base_grand_total) for row in rows), day)
	marked = None
	if marked_day:
		marked_day = getdate(marked_day)
		marked = next(
			(
				i
				for i, one in enumerate(starts)
				if (one.year, one.month) == (marked_day.year, marked_day.month)
			),
			None,
		)
	doctype, field = BILLS[party_doctype]
	return {
		"labels": [formatdate(one, "MMM") for one in starts],
		"values": values,
		"currency": company_currency(),
		"said": _("{0} in 12 months").format(_party_money(sum(values))),
		"route": f"/desk/{frappe.scrub(doctype).replace('_', '-')}?{field}={party}",
		"marked": marked,
	}


def party_billed(doc):
	return _billed(doc.doctype, doc.name)


def invoice_party_billed(doc):
	"""On an invoice, its customer's or supplier's year, with this one's
	month in the hue and the others grey."""
	party = "Customer" if doc.doctype == "Sales Invoice" else "Supplier"
	return _billed(party, doc.get(BILLS[party][1]), marked_day=doc.posting_date)


def _bank_side(doc) -> str | None:
	"""The company's own account a payment moved money in or out of."""
	return doc.paid_to if doc.payment_type == "Receive" else doc.paid_from


def _payment_money(doc, value) -> str:
	currency = (
		doc.paid_to_account_currency if doc.payment_type == "Receive" else doc.paid_from_account_currency
	)
	return fmt_money(flt(value), currency=currency)


def payment_said(doc):
	"""Where a payment stands, in a sentence: one thing a sentence."""
	party = doc.party_name or doc.party
	if doc.payment_type == "Receive":
		what = _("A draft. Submit it to record the money received from {0}.").format(party)
		done = _("{0} received from {1}.").format(_payment_money(doc, doc.received_amount), party)
	elif doc.payment_type == "Pay":
		what = _("A draft. Submit it to record the money paid to {0}.").format(party)
		done = _("{0} paid to {1}.").format(_payment_money(doc, doc.paid_amount), party)
	else:
		what = _("A draft. Submit it to move the money.")
		done = _("{0} moved from {1} to {2}.").format(
			_payment_money(doc, doc.paid_amount), doc.paid_from, doc.paid_to
		)
	if found := stages.draft(doc, what):
		return found
	if flt(doc.unallocated_amount) > 0 and doc.payment_type != "Internal Transfer":
		left = fmt_money(flt(doc.unallocated_amount), currency=doc.party_account_currency)
		return {
			"text": " ".join([done, _("{0} is not set against an invoice yet.").format(left)]),
			"colour": "orange",
		}
	return {"text": done, "colour": "green"}


def payment_progress(doc):
	"""Paid or received when it was, then reconciled with the bank statement:
	only for money through a bank account, since cash has no statement."""
	if doc.docstatus != 1:
		return None
	moved = {"Receive": _("Received"), "Pay": _("Paid")}.get(doc.payment_type, _("Internal Transfer"))
	if frappe.get_cached_value("Account", _bank_side(doc), "account_type") != "Bank":
		return None
	return stages.track(
		stages.step(moved, "done", formatdate(doc.posting_date)),
		stages.step(
			_("Reconciled"),
			"done" if doc.clearance_date else "now",
			formatdate(doc.clearance_date) if doc.clearance_date else _("Not in a bank statement yet"),
		),
	)


def _journal_money(doc, value) -> str:
	return fmt_money(flt(value), currency=frappe.get_cached_value("Company", doc.company, "default_currency"))


def journal_said(doc):
	"""What the entry moved, in a sentence: from the account credited to the
	one debited when there are two, else across how many."""
	if found := stages.draft(doc, _("A draft. Submit it to post it to the books.")):
		return found
	rows = doc.get("accounts") or []
	debited = [row.account for row in rows if flt(row.debit) > 0]
	credited = [row.account for row in rows if flt(row.credit) > 0]
	amount = _journal_money(doc, doc.total_debit)
	if len(debited) == 1 and len(credited) == 1:
		text = _("{0} from {1} to {2}.").format(amount, credited[0], debited[0])
	else:
		text = _("{0} across {1} accounts.").format(amount, len({row.account for row in rows}))
	return {"text": text, "colour": "green"}


def journal_progress(doc):
	"""Posted when it was, then reconciled with the bank statement, when one
	of its lines is a bank account."""
	if doc.docstatus != 1:
		return None
	banked = any(
		frappe.get_cached_value("Account", row.account, "account_type") == "Bank"
		for row in doc.get("accounts") or []
	)
	if not banked:
		return None
	return stages.track(
		stages.step(_("Posted"), "done", formatdate(doc.posting_date)),
		stages.step(
			_("Reconciled"),
			"done" if doc.clearance_date else "now",
			formatdate(doc.clearance_date) if doc.clearance_date else _("Not in a bank statement yet"),
		),
	)


def journal_reference(doc):
	"""The document the entry is for: an asset, a payroll, an invoice."""
	from onedesk.one_book import journal

	found = journal.referenced(doc)
	if not found or not frappe.has_permission(found[0], "read", found[1]):
		return None
	return {
		"label": _(found[0]),
		"value": journal.named(*found),
		"route": f"/desk/{frappe.scrub(found[0]).replace('_', '-')}/{found[1]}",
	}


def _tool(bank_account: str) -> str:
	return f"/desk/bank-reconciliation-tool?bank_account={quote(bank_account or '')}"


def line_said(doc):
	"""A bank statement line, in a sentence: what came in or went out, and
	whether it is matched to a payment yet."""
	if found := stages.draft(doc, _("A draft. Submit it to reconcile it.")):
		return found
	inward = flt(doc.deposit) > 0
	amount = fmt_money(flt(doc.deposit) or flt(doc.withdrawal), currency=doc.currency)
	moved = (_("{0} in on {1}.") if inward else _("{0} out on {1}.")).format(amount, formatdate(doc.date))
	if doc.status == "Reconciled" or flt(doc.unallocated_amount) <= 0:
		return {"text": " ".join([moved, _("Matched in the books.")]), "colour": "green"}
	if flt(doc.allocated_amount) > 0:
		left = fmt_money(flt(doc.unallocated_amount), currency=doc.currency)
		return {"text": " ".join([moved, _("{0} still to match.").format(left)]), "colour": "orange"}
	return {"text": " ".join([moved, _("Not matched to a payment yet.")]), "colour": "orange"}


def line_match(doc):
	"""A payment with the line's reference that is not matched to it yet: the
	one the Bank Reconciliation Tool would suggest first."""
	if doc.docstatus != 1 or flt(doc.unallocated_amount) <= 0 or not (doc.reference_number or "").strip():
		return None
	if not frappe.has_permission("Payment Entry", "read"):
		return None
	ledger = frappe.db.get_value("Bank Account", doc.bank_account, "account") if doc.bank_account else None
	if not ledger:
		return None
	found = frappe.get_list(
		"Payment Entry",
		filters=[
			["reference_no", "=", doc.reference_number.strip()],
			["docstatus", "<", 2],
			["clearance_date", "is", "not set"],
			["Payment Entry", "paid_to" if flt(doc.deposit) > 0 else "paid_from", "=", ledger],
		],
		fields=["name", "title", "docstatus"],
		limit_page_length=1,
	)
	if not found:
		return None
	one = found[0]
	return {
		"value": one.title or one.name,
		"label": _("Payment Entry · Draft") if one.docstatus == 0 else _("Payment Entry"),
		"route": f"/desk/payment-entry/{one.name}",
		"tone": "waiting" if one.docstatus == 0 else None,
	}


def line_reconcile(doc):
	if doc.docstatus != 1 or flt(doc.unallocated_amount) <= 0:
		return None
	return {"value": _("Open"), "route": _tool(doc.bank_account)}


def account_balance(doc):
	"""What the books hold in the account today."""
	if not doc.account or not frappe.has_permission("GL Entry", "read"):
		return None
	held = frappe.get_list(
		"GL Entry",
		filters={"account": doc.account, "is_cancelled": 0},
		fields=[{"SUM": "debit_in_account_currency", "as": "debit"}, {"SUM": "credit_in_account_currency", "as": "credit"}],
	)
	value = flt(held[0].debit) - flt(held[0].credit) if held else 0
	currency = frappe.get_cached_value("Account", doc.account, "account_currency")
	return {
		"value": fmt_money(value, currency=currency),
		"route": f"/desk/query-report/General Ledger?account={quote(json.dumps([doc.account]))}",
	}


def account_unmatched(doc):
	"""How many statement lines are not matched to a payment yet."""
	if not frappe.has_permission("Bank Transaction", "read"):
		return None
	count = frappe.db.count(
		"Bank Transaction", {"bank_account": doc.name, "docstatus": 1, "status": "Unreconciled"}
	)
	if not count:
		return {"value": _("None"), "tone": "quiet"}
	return {"value": str(count), "tone": "waiting", "route": _tool(doc.name)}


def account_last_line(doc):
	"""The last day a statement line came in for, from an import or by hand."""
	if not frappe.has_permission("Bank Transaction", "read"):
		return None
	last = frappe.get_list(
		"Bank Transaction",
		filters={"bank_account": doc.name, "docstatus": 1},
		fields=["date"],
		order_by="date desc",
		limit_page_length=1,
	)
	if not last:
		return {"value": _("None yet"), "tone": "quiet"}
	return {
		"value": formatdate(last[0].date),
		"route": f"/desk/bank-transaction?bank_account={quote(doc.name)}",
	}


MEASURES = {
	"party.overdue": party_overdue,
	"party.last_bill": party_last_bill,
	"invoice.progress": progress,
	"invoice.said": said,
	"invoice.outstanding": outstanding,
	"invoice.due": due,
	"invoice.repeats": repeats,
	"payment.said": payment_said,
	"payment.progress": payment_progress,
	"journal.said": journal_said,
	"journal.progress": journal_progress,
	"journal.reference": journal_reference,
	"bank.line_said": line_said,
	"bank.line_match": line_match,
	"bank.line_reconcile": line_reconcile,
	"bank.balance": account_balance,
	"bank.unmatched": account_unmatched,
	"bank.last_line": account_last_line,
}


def _payable(doc) -> bool:
	return (
		doc.docstatus == 1
		and flt(doc.outstanding_amount) > 0
		and not doc.is_return
		and frappe.has_permission("Payment Entry", "create")
	)


def _asks(doc) -> list[dict]:
	"""How much, on what day, into or out of which account, and the bank's
	reference: the four a payment needs."""
	bank, cash = frappe.db.get_value("Company", doc.company, ["default_bank_account", "default_cash_account"])
	bill = doc.doctype == "Purchase Invoice"
	return [
		{
			"fieldtype": "Currency",
			"fieldname": "amount",
			"label": _("Paid Amount"),
			"options": "currency",
			"reqd": 1,
			"default": doc.outstanding_amount,
		},
		{"fieldtype": "Date", "fieldname": "on", "label": _("Posting Date"), "reqd": 1, "default": today()},
		{
			"fieldtype": "Link",
			"fieldname": "account",
			"label": _("Account Paid From") if bill else _("Account Paid To"),
			"options": "Account",
			"reqd": 1,
			"default": bank or cash,
			"filters": {"company": doc.company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		},
		{
			"fieldtype": "Data",
			"fieldname": "reference",
			"label": _("Cheque/Reference No"),
			"description": _("The cheque or transfer number. The invoice's number when left empty."),
		},
	]


def _record(doc, amount, account, on=None, reference=None) -> str:
	entry = paid.settle(doc.doctype, doc.name, amount, account, reference=reference, on=on)
	return _("Payment {0} recorded.").format(entry)


VERBS = {
	"invoice.record_payment": {
		"doctypes": list(paid.SETTLED),
		"label": _lt("Record Payment"),
		"action": _lt("Record"),
		"when": _payable,
		"fields": _asks,
		"run": _record,
	},
}

_BAND = [
	{"label": _lt("Progress"), "source": "Measure", "measure": "invoice.progress"},
	{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
	{
		"label": _lt("Outstanding Amount"),
		"source": "Measure",
		"measure": "invoice.outstanding",
		"shown_when": OWED,
	},
	{"label": _lt("Payment Due Date"), "source": "Measure", "measure": "invoice.due", "shown_when": OWED},
	{"label": _lt("Grand Total"), "source": "Field", "field": "grand_total"},
	{"label": _lt("Auto Repeat"), "source": "Measure", "measure": "invoice.repeats", "shown_when": OWED},
]

CHARTS = {
	"party.billed": {
		"doctypes": list(BILLS),
		"label": lambda doc: _("Billed") if doc.doctype == "Customer" else _("Bought"),
		"figures": party_billed,
	},
	"invoice.party_billed": {
		"doctypes": list(paid.SETTLED),
		"label": lambda doc: (
			_("Billed to {0}").format(doc.customer_name or doc.customer)
			if doc.doctype == "Sales Invoice"
			else _("Billed by {0}").format(doc.supplier_name or doc.supplier)
		),
		"figures": invoice_party_billed,
	},
}

RETURN_AGAINST = {
	"Sales Invoice": _lt("Return Against"),
	"Purchase Invoice": _lt("Return Against Purchase Invoice"),
}

HEADS = [
	{
		"doctype": doctype,
		"sentences": [{"measure": "invoice.said"}],
		"band": [
			*_BAND,
			{
				"label": RETURN_AGAINST[doctype],
				"source": "Field",
				"field": "return_against",
				"shown_when": [["is_return", "=", 1]],
			},
		],
		"verbs": [{"verb": "invoice.record_payment", "primary": 1}],
		"charts": [{"chart": "invoice.party_billed", "shown_when": [["docstatus", "=", 1]]}],
	}
	for doctype in paid.SETTLED
] + [
	{
		"doctype": "Bank Transaction",
		"sentences": [{"measure": "bank.line_said"}],
		"band": [
			{"label": _lt("Bank Account"), "source": "Field", "field": "bank_account"},
			{
				"label": _lt("Reference Number"),
				"source": "Field",
				"field": "reference_number",
				"hide_empty": 1,
			},
			{"label": _lt("Payment Entry"), "source": "Measure", "measure": "bank.line_match"},
			{"label": _lt("Bank Reconciliation Tool"), "source": "Measure", "measure": "bank.line_reconcile"},
		],
	},
	{
		"doctype": "Bank Account",
		"band": [
			{"label": _lt("Balance"), "source": "Measure", "measure": "bank.balance"},
			{"label": _lt("Unreconciled"), "source": "Measure", "measure": "bank.unmatched"},
			{"label": _lt("Last Bank Transaction"), "source": "Measure", "measure": "bank.last_line"},
		],
	},
	{
		"doctype": "Journal Entry",
		"sentences": [{"measure": "journal.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "journal.progress"},
			{"label": _lt("Reference Name"), "source": "Measure", "measure": "journal.reference"},
			{"label": _lt("Reference Number"), "source": "Field", "field": "cheque_no", "hide_empty": 1},
			{"label": _lt("Total Debit"), "source": "Field", "field": "total_debit"},
		],
	},
	{
		"doctype": "Payment Entry",
		"sentences": [{"measure": "payment.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "payment.progress"},
			{"label": _lt("Paid Amount"), "source": "Field", "field": "paid_amount"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Mode of Payment"), "source": "Field", "field": "mode_of_payment", "hide_empty": 1},
			{
				"label": _lt("Account Paid To"),
				"source": "Field",
				"field": "paid_to",
				"shown_when": [["payment_type", "=", "Receive"]],
			},
			{
				"label": _lt("Account Paid From"),
				"source": "Field",
				"field": "paid_from",
				"shown_when": [["payment_type", "=", "Pay"]],
			},
			{
				"label": _lt("Cheque/Reference No"),
				"source": "Field",
				"field": "reference_no",
				"hide_empty": 1,
			},
		],
	},
	{
		"doctype": "Supplier",
		"band": [
			{"label": _lt("Overdue"), "source": "Measure", "measure": "party.overdue"},
			{"label": _lt("Last Purchase Invoice"), "source": "Measure", "measure": "party.last_bill"},
			{
				"label": _lt("Open Orders"),
				"source": "Count",
				"of_doctype": "Purchase Order",
				"filters": [
					["supplier", "=", "{{ doc.name }}"],
					["docstatus", "=", 1],
					["status", "not in", ["Completed", "Closed"]],
				],
				"route": '/desk/purchase-order?supplier={{ doc.name }}&docstatus=1&status=["not in",["Completed","Closed"]]',
				"hide_empty": 1,
			},
		],
		"charts": [{"chart": "party.billed"}],
	},
]
