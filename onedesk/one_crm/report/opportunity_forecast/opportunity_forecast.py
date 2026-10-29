"""What the open deals will bring in, month by month, and what already came.

A deal counts in the month it is expected to close. One whose closing date has
passed is Overdue, even inside this month, as Home's Today has it; an undated
one is its own row. Won is by the day the deal was won (`measure.closed`).
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, get_first_day, getdate, nowdate

from onedesk.one_crm import measure


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	first = get_first_day(filters.from_month or nowdate())
	months = [add_months(first, step) for step in range(int(filters.months or 6))]
	owner = {"opportunity_owner": filters.owner} if filters.owner else {}

	rows = {key: _row(label) for key, label in _keys(months)}
	for deal in measure.deals({**measure.alive(), **owner}):
		key = _key(deal.expected_closing, max(first, getdate(nowdate())), months)
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


def _key(expected, cutoff, months):
	if not expected:
		return "undated"
	if getdate(expected) < cutoff:
		return "overdue"
	month = get_first_day(getdate(expected))
	return month if month in months else None


def _row(label) -> dict:
	return {"month": label, "deals": 0, "value": 0.0, "weighted": 0.0, "won": 0.0}


def _columns() -> list[dict]:
	return [
		{"fieldname": "month", "label": _("Expected To Close"), "fieldtype": "Data", "width": 160},
		{"fieldname": "deals", "label": _("Open Opportunities"), "fieldtype": "Int", "width": 110},
		{"fieldname": "value", "label": _("Value"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "weighted", "label": _("Weighted Value"), "fieldtype": "Currency", "width": 150},
		{"fieldname": "won", "label": _("Won"), "fieldtype": "Currency", "width": 140},
	]
