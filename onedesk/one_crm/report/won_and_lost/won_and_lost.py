"""What was won and lost, and why, by month, owner, source or reason.

A deal is counted on the day it was won or lost (`measure.closed`). By Lost
Reason, a deal lost for two reasons is counted under both, so that column's
rows add up to more than the lost deals; the other groupings do not.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from onedesk.one_crm import measure

#: What a row can be, and how a deal is put in one.
BY = ("Month", "Deal Owner", "Source", "Lost Reason")


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	by = filters.group_by if filters.group_by in BY else "Month"
	start = getdate(filters.from_date) if filters.from_date else None
	end = getdate(filters.to_date) if filters.to_date else None

	shut = {
		name: one
		for name, one in measure.closed().items()
		if (not start or one.on >= start) and (not end or one.on <= end)
	}
	reasons = _reasons(list(shut)) if by == "Lost Reason" else {}
	rows = {}
	for deal in measure.deals({"name": ["in", list(shut) or [""]]}):
		one = shut[deal.name]
		for group in _groups(by, deal, one, reasons):
			row = rows.setdefault(group, {"group": group, "won": 0, "won_value": 0.0, "lost": 0, "lost_value": 0.0})
			side = "won" if one.outcome == "Won" else "lost"
			row[side] += 1
			row[f"{side}_value"] += measure.value(deal)
	for row in rows.values():
		row["rate"] = measure.rate(row["won"], row["lost"])
	return _columns(by), sorted(rows.values(), key=lambda row: str(row["group"]))


def _groups(by, deal, one, reasons) -> list[str]:
	if by == "Month":
		return [one.on.strftime("%Y-%m")]
	if by == "Deal Owner":
		return [deal.opportunity_owner or measure.not_recorded()]
	if by == "Source":
		return [deal.utm_source or measure.not_recorded()]
	if one.outcome == "Won":
		return []
	return reasons.get(deal.name) or [measure.not_recorded()]


def _reasons(deals: list[str]) -> dict[str, list[str]]:
	found = {}
	for row in frappe.get_all(
		"Opportunity Lost Reason Detail",
		filters={"parenttype": "Opportunity", "parent": ["in", deals or [""]]},
		fields=["parent", "lost_reason"],
	):
		found.setdefault(row.parent, []).append(row.lost_reason)
	return found


def _columns(by) -> list[dict]:
	return [
		{"fieldname": "group", "label": _(by), "fieldtype": "Data", "width": 180},
		{"fieldname": "won", "label": _("Won"), "fieldtype": "Int", "width": 80},
		{"fieldname": "won_value", "label": _("Won Value"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "lost", "label": _("Lost"), "fieldtype": "Int", "width": 80},
		{"fieldname": "lost_value", "label": _("Lost Value"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "rate", "label": _("Win Rate (%)"), "fieldtype": "Percent", "width": 120},
	]
