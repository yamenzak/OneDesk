"""The numbers OneCRM is measured by, and the one fact they all rest on.

**When a deal was won or lost** is the Milestone that recorded it reaching a
stage whose outcome is Won or Lost (`stages.py`). ERPNext's dashboards use
`modified`, which is the last time anybody touched the deal: a deal won in
March and corrected in May was "won in May". Every report and card here reads
`closed()` instead.

The four figures on Home are Custom number cards, so each is worked out here
through the reader's own permissions and opens the report behind it.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, get_first_day, getdate, nowdate

from onedesk.one_crm import next as next_step
from onedesk.one_crm import stages

#: How far back the win rate on Home looks.
RATE_DAYS = 90


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
	"""The deals the reader may see, with what every measure needs."""
	return frappe.get_list(
		"Opportunity",
		filters=filters or {},
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


def value(deal) -> float:
	"""What a deal is worth in the company's currency: its value, or its items'."""
	return flt(deal.base_opportunity_amount) or flt(deal.base_total)


# ------------------------------------------------------------------ Home


def _card(amount, route: str, fieldtype: str = "Currency") -> dict:
	return {"value": amount, "fieldtype": fieldtype, "route": ["query-report", route]}


@frappe.whitelist()
@frappe.read_only()
def pipeline(filters: str | None = None) -> dict:
	"""What the open deals are worth."""
	open_ = deals({"status": ["in", next_step.OPEN["Opportunity"]]})
	return _card(sum(value(one) for one in open_), "Deal Forecast")


@frappe.whitelist()
@frappe.read_only()
def weighted(filters: str | None = None) -> dict:
	"""What the open deals are worth, each by its probability."""
	open_ = deals({"status": ["in", next_step.OPEN["Opportunity"]]})
	return _card(sum(value(one) * flt(one.probability) / 100 for one in open_), "Deal Forecast")


@frappe.whitelist()
@frappe.read_only()
def won_this_month(filters: str | None = None) -> dict:
	"""What was won since the first of the month."""
	start = get_first_day(nowdate())
	shut = closed()
	mine = {one.name: one for one in deals({"name": ["in", list(shut) or [""]]})}
	return _card(
		sum(value(mine[name]) for name, one in shut.items() if one.outcome == "Won" and one.on >= start and name in mine),
		"Won and Lost",
	)


@frappe.whitelist()
@frappe.read_only()
def win_rate(filters: str | None = None) -> dict:
	"""Of the deals closed in the last RATE_DAYS days, the share that was won."""
	since = getdate(add_days(nowdate(), -RATE_DAYS))
	visible = set(frappe.get_list("Opportunity", pluck="name", limit=0))
	recent = [one.outcome for name, one in closed().items() if one.on >= since and name in visible]
	return _card(rate(recent.count("Won"), recent.count("Lost")), "Won and Lost", fieldtype="Percent")


def rate(won: int, lost: int) -> float:
	"""Won as a share of won and lost, in percent. Pure."""
	return round(100 * won / (won + lost), 1) if won + lost else 0.0


def not_recorded() -> str:
	return _("Not Recorded")
