"""What the open deals will bring in, month by month, and what already came.

A deal counts in the month it is expected to close, at its value and at its
value weighted by probability. A deal whose expected date has passed is not
dropped into a month that is over: it is its own row, Overdue, because that
is the answer somebody opened this to find. So is a deal with no date at all.
Won is by the day the deal was won (`measure.closed`), not the day it was
expected.
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, getdate, nowdate

from onedesk.one_crm import measure
from onedesk.one_crm import next as next_step


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	first = get_first_day(filters.from_month or nowdate())
	months = [add_months(first, step) for step in range(int(filters.months or 6))]
	owner = {"opportunity_owner": filters.owner} if filters.owner else {}

	rows = {key: _row(label) for key, label in _keys(months)}
	for deal in measure.deals({"status": ["in", next_step.OPEN["Opportunity"]], **owner}):
		key = _key(deal.expected_closing, first, months)
		if key:
			rows[key]["deals"] += 1
			rows[key]["value"] += measure.value(deal)
			rows[key]["weighted"] += measure.value(deal) * flt(deal.probability) / 100

	shut = measure.closed()
	for deal in measure.deals({"name": ["in", list(shut) or [""]], **owner}):
		one = shut[deal.name]
		month = get_first_day(one.on)
		if one.outcome == "Won" and month in months:
			rows[month]["won"] += measure.value(deal)

	return _columns(), list(rows.values())


def _keys(months):
	yield "overdue", _("Overdue")
	for month in months:
		yield month, month.strftime("%b %Y")
	yield "undated", _("No Closing Date")


def _key(expected, first, months):
	if not expected:
		return "undated"
	month = get_first_day(getdate(expected))
	if month < first:
		return "overdue"
	return month if month in months else None


def _row(label) -> dict:
	return {"month": label, "deals": 0, "value": 0.0, "weighted": 0.0, "won": 0.0}


def _columns() -> list[dict]:
	return [
		{"fieldname": "month", "label": _("Expected To Close"), "fieldtype": "Data", "width": 160},
		{"fieldname": "deals", "label": _("Open Deals"), "fieldtype": "Int", "width": 110},
		{"fieldname": "value", "label": _("Value"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "weighted", "label": _("Weighted Value"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "won", "label": _("Won"), "fieldtype": "Currency", "width": 140},
	]
