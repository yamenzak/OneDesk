"""The numbers OneCRM is measured by, and the one fact they all rest on.

When a deal was won or lost is the Milestone that recorded it reaching a stage
whose outcome is Won or Lost (`closed()`), never `modified`.
"""

from statistics import median

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_datetime, getdate, now_datetime

from onedesk.one.company import reader_company
from onedesk.one_crm import next as next_step
from onedesk.one_crm import stages

RATE_DAYS = 90

USUAL_DAYS = 365

FEWEST = 3


def closed(deals: list[str] | None = None) -> dict[str, frappe._dict]:
	"""Each closed deal's outcome and the day it closed, from its latest move
	into a Won or Lost stage."""
	outcomes = {one.name: one.one_outcome for one in stages.stages() if one.one_outcome in ("Won", "Lost")}
	if not outcomes:
		return {}
	filters = {
		"reference_type": "Opportunity",
		"track_field": "sales_stage",
		"value": ["in", list(outcomes)],
	}
	if deals is not None:
		if not deals:
			return {}
		filters["reference_name"] = ["in", deals]
	found = {}
	for row in frappe.get_all(
		"Milestone", filters=filters, fields=["reference_name", "value", "creation"], order_by="creation asc"
	):
		found[row.reference_name] = frappe._dict(outcome=outcomes[row.value], on=getdate(row.creation))
	return found


def deals(filters: dict | None = None, fields: tuple = ()) -> list[frappe._dict]:
	"""The deals the reader may see, the company's, with what every measure
	needs."""
	return frappe.get_list(
		"Opportunity",
		filters={"company": reader_company(), **(filters or {})},
		fields=[
			"name",
			"status",
			"opportunity_owner",
			"utm_source",
			"expected_closing",
			"probability",
			"base_opportunity_amount",
			"base_total",
			*fields,
		],
		limit=0,
	)


def alive() -> dict:
	"""The filters for the deals in the pipeline: open, and not on hold."""
	return {"status": ["in", next_step.OPEN["Opportunity"]], "sales_stage": ["not in", stages.held() or [""]]}


def value(deal) -> float:
	"""What a deal is worth in the company's currency: its value, or its items'."""
	return flt(deal.base_opportunity_amount) or flt(deal.base_total)


def rate(won: int, lost: int) -> float:
	"""Won as a share of won and lost, in percent. Pure."""
	return round(100 * won / (won + lost), 1) if won + lost else 0.0


def not_recorded() -> str:
	return _("Not Recorded")


def stays(moves) -> list[dict]:
	"""Each stay of a deal in a stage, from its Milestones: which deal, which
	stage, when it arrived and when it left — None while it is still there. Two
	moves in a row to the same stage are one stay. Pure.

	`moves` are rows with `reference_name`, `value` and `creation`, in order of
	deal and then time."""
	out = []
	for move in moves:
		last = out[-1] if out and out[-1]["deal"] == move["reference_name"] else None
		if last and last["stage"] == move["value"]:
			continue
		if last:
			last["left"] = move["creation"]
		out.append({"deal": move["reference_name"], "stage": move["value"], "came": move["creation"], "left": None})
	return out


def days(stay, now) -> float:
	"""How many days a stay lasted, or has lasted so far. Pure."""
	end = get_datetime(stay["left"]) if stay["left"] else now
	return (end - get_datetime(stay["came"])).total_seconds() / 86400


def usual(finished: list[float]) -> float | None:
	"""The usual length of a stay: the median, once there are FEWEST. Pure."""
	return round(median(finished), 1) if len(finished) >= FEWEST else None


def stuck(length: float, usual_days: float | None) -> bool:
	"""Whether a stay has gone on longer than is usual for its stage. Never for
	under a day: a stage deals usually leave within the hour is not one a deal
	is stuck in by lunchtime. Pure."""
	return usual_days is not None and length > max(usual_days, 1)


def every_stay(deals: list[str] | None = None) -> list[dict]:
	"""Every stay of the deals the reader may see, or of the ones named."""
	visible = set(frappe.get_list("Opportunity", pluck="name", limit=0))
	if deals is not None:
		visible &= set(deals)
	moves = frappe.get_all(
		"Milestone",
		filters={
			"reference_type": "Opportunity",
			"track_field": "sales_stage",
			"reference_name": ["in", list(visible) or [""]],
		},
		fields=["reference_name", "value", "creation"],
		order_by="reference_name asc, creation asc",
	)
	return stays(moves)


def usual_by_stage(all_stays: list[dict], since=None) -> dict[str, float | None]:
	"""What is usual for each stage, from the stays that ended since `since`."""
	since = get_datetime(since or add_days(now_datetime(), -USUAL_DAYS))
	now = now_datetime()
	finished = {}
	for stay in all_stays:
		if stay["left"] and get_datetime(stay["left"]) >= since:
			finished.setdefault(stay["stage"], []).append(days(stay, now))
	return {stage: usual(lengths) for stage, lengths in finished.items()}


def usual_for(stage: str | None) -> float | None:
	"""How long deals usually stay in one stage."""
	return usual_by_stage(every_stay()).get(stage) if stage else None
