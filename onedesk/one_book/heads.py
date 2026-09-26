"""What an invoice's and a bill's page say above their fields: what is still
owed and when it was due, and Record Payment, which settles it in one step
(paid.py); and what a customer's and a supplier's page say: what they owe or
are owed, what is late, what was billed this year against last, and their
billing month by month. See one/head.py.
"""

import frappe
from frappe import _, _lt
from frappe.utils import date_diff, flt, fmt_money, formatdate, getdate, today

from onedesk.one import figures
from onedesk.one_book import paid

#: What the band is on: a submitted invoice or bill that is not a return.
OWED = [["docstatus", "=", 1], ["is_return", "=", 0]]


def _money(doc, value) -> str:
	return fmt_money(flt(value), currency=doc.currency)


def _late(doc) -> int | None:
	"""Days past due while something is owed; nought on the day. Pure over the
	record."""
	if flt(doc.outstanding_amount) <= 0 or not doc.due_date:
		return None
	return date_diff(today(), doc.due_date)


def outstanding(doc):
	late = _late(doc)
	tone = "quiet" if flt(doc.outstanding_amount) <= 0 else ("alarm" if late and late > 0 else None)
	return {"value": _money(doc, doc.outstanding_amount), "tone": tone}


def due(doc):
	if not doc.due_date:
		return None
	when = formatdate(doc.due_date)
	late = _late(doc)
	if late is None:
		return {"label": _("Was Due"), "value": when, "tone": "quiet"}
	if late > 0:
		return {"value": _("{0} · {1} days late").format(when, late), "tone": "alarm"}
	if late == 0:
		return {"value": _("Today"), "tone": "waiting"}
	return _("{0} · in {1} days").format(when, -late)


def paid_so_far(doc):
	paid_now = flt(doc.grand_total) - flt(doc.outstanding_amount)
	return {"value": _money(doc, paid_now), "meter": {"value": paid_now, "of": flt(doc.grand_total)}}


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


# ------------------------------------------------------------------ a customer or a supplier

#: A party's invoices: which doctype, and the field on it that names them.
BILLS = {"Customer": ("Sales Invoice", "customer"), "Supplier": ("Purchase Invoice", "supplier")}

#: A party's invoices counted: submitted, and not a credit or debit note.
COUNTED = {"docstatus": 1, "is_return": 0}


def _currency(company: str | None = None) -> str:
	company = company or frappe.defaults.get_user_default("Company") or frappe.db.get_default("company")
	return frappe.get_cached_value("Company", company, "default_currency") or frappe.db.get_default(
		"currency"
	)


def _bills(party_doctype: str, party: str, since=None, fields=None) -> list | None:
	"""A party's invoices as the reader's list would give them, or None when
	the reader may not see that list at all."""
	doctype, field = BILLS[party_doctype]
	if not frappe.has_permission(doctype, "read"):
		return None
	filters = {field: party, **COUNTED}
	if since:
		filters["posting_date"] = [">=", since]
	return frappe.get_list(
		doctype,
		filters=filters,
		fields=fields or ["posting_date", "base_grand_total"],
		limit_page_length=0,
	)


def _party_money(value) -> str:
	return fmt_money(flt(value), currency=_currency())


def party_outstanding(doc):
	rows = _bills(doc.doctype, doc.name, fields=["outstanding_amount", "conversion_rate", "due_date"])
	if rows is None:
		return None
	owed = sum(flt(row.outstanding_amount) * flt(row.conversion_rate or 1) for row in rows)
	late = any(
		flt(row.outstanding_amount) > 0 and row.due_date and getdate(row.due_date) < getdate() for row in rows
	)
	return {
		"value": _party_money(owed),
		"tone": "quiet" if owed <= 0 else ("alarm" if late else None),
		"meter": _credit(doc, owed),
	}


def _credit(doc, owed: float) -> dict | None:
	"""How much of a customer's credit limit is used, where one is set."""
	if doc.doctype != "Customer":
		return None
	limit = max((flt(row.credit_limit) for row in doc.get("credit_limits") or []), default=0)
	return {"value": owed, "of": limit} if limit else None


def party_overdue(doc):
	rows = _bills(doc.doctype, doc.name, fields=["outstanding_amount", "conversion_rate", "due_date"])
	if not rows:
		return None
	late = [
		row
		for row in rows
		if flt(row.outstanding_amount) > 0 and row.due_date and getdate(row.due_date) < getdate()
	]
	if not late:
		return None
	oldest = max(date_diff(today(), row.due_date) for row in late)
	return {
		"value": _party_money(
			sum(flt(row.outstanding_amount) * flt(row.conversion_rate or 1) for row in late)
		),
		"label": _("Overdue · oldest {0} days").format(oldest),
		"tone": "alarm",
	}


def party_this_year(doc):
	"""Billed since the first of January, against the same days last year."""
	day = getdate()
	start = day.replace(month=1, day=1)
	before = figures.same_day_last_year(start)
	rows = _bills(doc.doctype, doc.name, since=before)
	if rows is None:
		return None
	now = sum(flt(row.base_grand_total) for row in rows if getdate(row.posting_date) >= start)
	then = sum(
		flt(row.base_grand_total)
		for row in rows
		if before <= getdate(row.posting_date) <= figures.same_day_last_year(day)
	)
	return {
		"value": _party_money(now),
		"tone": None if now else "quiet",
		"delta": {"change": figures.change(now, then), "against": _("since last year")},
	}


def party_last_bill(doc):
	doctype, field = BILLS[doc.doctype]
	if not frappe.has_permission(doctype, "read"):
		return None
	found = frappe.get_list(
		doctype,
		filters={field: doc.name, **COUNTED},
		fields=["name", "posting_date", "base_grand_total"],
		order_by="posting_date desc, creation desc",
		limit_page_length=1,
	)
	if not found:
		return {"value": _("None yet"), "tone": "quiet"}
	last = found[0]
	# The day goes in the label: beside an amount in a right-to-left currency
	# the two run into each other.
	label = _("Last Invoice") if doc.doctype == "Customer" else _("Last Bill")
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
		"currency": _currency(),
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


MEASURES = {
	"party.outstanding": party_outstanding,
	"party.overdue": party_overdue,
	"party.this_year": party_this_year,
	"party.last_bill": party_last_bill,
	"invoice.outstanding": outstanding,
	"invoice.due": due,
	"invoice.paid": paid_so_far,
	"invoice.repeats": repeats,
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
			"label": _("Amount"),
			"options": "currency",
			"reqd": 1,
			"default": doc.outstanding_amount,
		},
		{"fieldtype": "Date", "fieldname": "on", "label": _("Paid On"), "reqd": 1, "default": today()},
		{
			"fieldtype": "Link",
			"fieldname": "account",
			"label": _("Paid From") if bill else _("Paid Into"),
			"options": "Account",
			"reqd": 1,
			"default": bank or cash,
			"filters": {"company": doc.company, "is_group": 0, "account_type": ["in", ["Bank", "Cash"]]},
		},
		{
			"fieldtype": "Data",
			"fieldname": "reference",
			"label": _("Reference"),
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
	{"label": _lt("Outstanding"), "source": "Measure", "measure": "invoice.outstanding", "shown_when": OWED},
	{"label": _lt("Due"), "source": "Measure", "measure": "invoice.due", "shown_when": OWED},
	{"label": _lt("Paid"), "source": "Measure", "measure": "invoice.paid", "shown_when": OWED},
	{"label": _lt("Total"), "source": "Field", "field": "grand_total", "shown_when": OWED},
	{"label": _lt("Repeats"), "source": "Measure", "measure": "invoice.repeats", "shown_when": OWED},
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

HEADS = [
	{
		"doctype": doctype,
		"band": _BAND,
		"verbs": [{"verb": "invoice.record_payment", "primary": 1}],
		"charts": [{"chart": "invoice.party_billed", "shown_when": [["docstatus", "=", 1]]}],
	}
	for doctype in paid.SETTLED
] + [
	{
		"doctype": "Customer",
		"band": [
			{"label": _lt("Owes Us"), "source": "Measure", "measure": "party.outstanding"},
			{"label": _lt("Overdue"), "source": "Measure", "measure": "party.overdue"},
			{"label": _lt("Billed This Year"), "source": "Measure", "measure": "party.this_year"},
			{"label": _lt("Last Invoice"), "source": "Measure", "measure": "party.last_bill"},
			{
				"label": _lt("Open Orders"),
				"source": "Count",
				"of_doctype": "Sales Order",
				"filters": [
					["customer", "=", "{{ doc.name }}"],
					["docstatus", "=", 1],
					["status", "not in", ["Completed", "Closed"]],
				],
				"route": '/desk/sales-order?customer={{ doc.name }}&docstatus=1&status=["not in",["Completed","Closed"]]',
				"hide_empty": 1,
			},
		],
		"charts": [{"chart": "party.billed"}],
	},
	{
		"doctype": "Supplier",
		"band": [
			{"label": _lt("We Owe"), "source": "Measure", "measure": "party.outstanding"},
			{"label": _lt("Overdue"), "source": "Measure", "measure": "party.overdue"},
			{"label": _lt("Bought This Year"), "source": "Measure", "measure": "party.this_year"},
			{"label": _lt("Last Bill"), "source": "Measure", "measure": "party.last_bill"},
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
