"""How long deals stay in each stage, and how long they take to be won.

A stay counts in the period if it ended there; a deal still in a stage counts
under In It Now, and under Longer Than Usual once it has been there longer
than the stage's usual and more than a day (`measure.stuck`). What is usual is the median of the stays that ended in
the period, and needs `measure.FEWEST` of them. The last row is from a deal
coming in to its being won, for the deals won in the period.
"""

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, now_datetime, nowdate

from onedesk.one_crm import measure, stages


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	end = getdate(filters.to_date or nowdate())
	start = getdate(filters.from_date) if filters.from_date else add_days(end, -measure.USUAL_DAYS)
	owned = frappe.get_list(
		"Opportunity",
		filters={"opportunity_owner": filters.owner} if filters.owner else {},
		fields=["name", "status"],
		limit=0,
	)
	every = measure.every_stay([one.name for one in owned])
	now = now_datetime()

	def ended_in(stay):
		return stay["left"] and start <= get_datetime(stay["left"]).date() <= end

	rows = []
	for stage in stages.stages():
		if (stage.one_outcome or "Open") in stages.CLOSED:
			continue
		finished = [measure.days(stay, now) for stay in every if stay["stage"] == stage.name and ended_in(stay)]
		now_in = [measure.days(stay, now) for stay in every if stay["stage"] == stage.name and not stay["left"]]
		usual = measure.usual(finished)
		rows.append(
			{
				"stage": stage.name,
				"deals": len(finished),
				"usual": usual,
				"longest": round(max(finished), 1) if finished else None,
				"now": len(now_in),
				"stuck": sum(1 for length in now_in if measure.stuck(length, usual)),
			}
		)

	won = _to_win(every, {one.name for one in owned}, start, end)
	rows.append(
		{
			"stage": _("To Win"),
			"deals": len(won),
			"usual": measure.usual(won),
			"longest": round(max(won), 1) if won else None,
			"bold": 1,
		}
	)
	return _columns(), rows


def _to_win(every, owned, start, end) -> list[float]:
	"""Days from a deal's first stage to its winning, for deals won in the period."""
	won_stages = {one.name for one in stages.stages() if one.one_outcome == "Won"}
	lengths = []
	for name, one in measure.closed(list(owned)).items():
		if one.outcome != "Won" or not start <= one.on <= end:
			continue
		mine = [stay for stay in every if stay["deal"] == name]
		wins = [get_datetime(stay["came"]) for stay in mine if stay["stage"] in won_stages]
		if wins:
			lengths.append((max(wins) - get_datetime(mine[0]["came"])).total_seconds() / 86400)
	return lengths


def _columns() -> list[dict]:
	return [
		{"fieldname": "stage", "label": _("Sales Stage"), "fieldtype": "Data", "width": 180},
		{"fieldname": "deals", "label": _("Deals"), "fieldtype": "Int", "width": 90},
		{"fieldname": "usual", "label": _("Usual Days"), "fieldtype": "Float", "precision": 1, "width": 120},
		{"fieldname": "longest", "label": _("Longest Days"), "fieldtype": "Float", "precision": 1, "width": 120},
		{"fieldname": "now", "label": _("In It Now"), "fieldtype": "Int", "width": 100},
		{"fieldname": "stuck", "label": _("Longer Than Usual"), "fieldtype": "Int", "width": 150},
	]
