"""What an invoice's and a bill's page say above their fields: what is still
owed and when it was due, and Record Payment, which settles it in one step
(paid.py). See one/head.py.
"""

import frappe
from frappe import _, _lt
from frappe.utils import date_diff, flt, fmt_money, formatdate, today

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
	return _money(doc, flt(doc.grand_total) - flt(doc.outstanding_amount))


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


MEASURES = {
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

HEADS = [
	{"doctype": doctype, "band": _BAND, "verbs": [{"verb": "invoice.record_payment", "primary": 1}]}
	for doctype in paid.SETTLED
]
