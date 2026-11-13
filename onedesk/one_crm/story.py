"""OneCRM's Home, told as a story (page/onecrm, frontend/src/crm): the
headline figures with their months, how selling is going, where the open
opportunities stand, and where leads and sales come from. Frappe CRM's
dashboard over ERPNext's Lead and Opportunity, as the reader may see them, in
the company's currency. How it works is in the module's AGENTS.md.
"""

from collections import defaultdict
from datetime import date

import frappe
from frappe.utils import add_days, flt, getdate, today

from onedesk.one.company import company_currency, reader_company
from onedesk.one.rights import can
from onedesk.one.story import month_of, story_months
from onedesk.one_crm import chain, measure, stages

MONTHS = 12

AHEAD = 5

FEW = 8

FUNNEL = ("Opportunity", "Quotation", "Sales Order", "Sales Invoice", "Paid")


@frappe.whitelist()
@frappe.read_only()
def read() -> dict:
	"""Everything Home's story draws, each part None when the reader may not
	see it or there is nothing to draw."""
	company = reader_company()
	months = story_months()
	since = months[0]
	may = can("Opportunity")
	opportunities = measure.deals({"creation": [">=", since]}, fields=("creation",)) if may else []
	shut = measure.closed() if may else {}
	closed = _closed(shut, since) if may else []
	leads = _leads(since)
	return {
		"currency": company_currency(company),
		"months": [one.isoformat() for one in months],
		"cards": _cards(months, closed, leads, shut) if may else {},
		"sales": {
			"trend": _trend(months, leads, opportunities, closed),
			"forecast": _forecast(closed),
			"funnel": _funnel(opportunities),
		}
		if may
		else None,
		"pipeline": {
			"stages": _stages(),
			"owners": _owners(closed),
			"lost": _lost(closed),
		}
		if may
		else None,
		"sources": {
			"leads": _sources(leads) if leads is not None else [],
			"won": _won_by(closed, "utm_source"),
			"territories": _territories(),
		}
		if may
		else None,
	}


def _leads(since) -> list | None:
	if not can("Lead"):
		return None
	return frappe.get_list(
		"Lead",
		filters={"creation": [">=", since], "company": reader_company()},
		fields=["name", "creation", "status", "utm_source"],
		limit=0,
	)


def _closed(shut: dict, since) -> list[frappe._dict]:
	"""The opportunities won or lost since `since`, each with its outcome, the
	day it closed and its value."""
	names = [name for name, one in shut.items() if one.on >= getdate(since)]
	rows = measure.deals({"name": ["in", names or [""]]}, fields=("territory",))
	for row in rows:
		row.outcome, row.on, row.worth = shut[row.name].outcome, shut[row.name].on, measure.value(row)
	return rows


def _won(closed: list, months: list[date]) -> list[float]:
	"""What was won each month."""
	by = defaultdict(float)
	for one in closed:
		if one.outcome == "Won":
			by[month_of(one.on)] += one.worth
	return [by[month.isoformat()] for month in months]


def _cards(months, closed, leads, shut) -> dict:
	"""The headline figures, each with its months where it has them."""
	alive = measure.deals(measure.alive())
	won = _won(closed, months)
	since = getdate(add_days(today(), -measure.RATE_DAYS))
	recent = [one.outcome for one in closed if one.on >= since]
	cards = {
		"pipeline": {"value": sum(measure.value(one) for one in alive)},
		"weighted": {"value": sum(measure.value(one) * flt(one.probability) / 100 for one in alive)},
		"won": {"value": won[-1], "series": won},
		"rate": {"value": measure.rate(recent.count("Won"), recent.count("Lost"))},
	}
	if leads is not None:
		by = defaultdict(int)
		for one in leads:
			by[month_of(one.creation)] += 1
		series = [by[month.isoformat()] for month in months]
		cards["leads"] = {"value": series[-1], "series": series}
	worth = [one.worth for one in closed if one.outcome == "Won"]
	if worth:
		cards["average"] = {"value": sum(worth) / len(worth)}
	return cards


def _trend(months, leads, opportunities, closed) -> list[dict]:
	"""How many leads came in, opportunities were opened and won, each month."""
	count = {key: defaultdict(int) for key in ("leads", "opportunities", "won")}
	for one in leads or []:
		count["leads"][month_of(one.creation)] += 1
	for one in opportunities:
		count["opportunities"][month_of(one.creation)] += 1
	for one in closed:
		if one.outcome == "Won":
			count["won"][month_of(one.on)] += 1
	return [
		{"month": month.isoformat(), **{key: by[month.isoformat()] for key, by in count.items()}}
		for month in months
	]


def _forecast(closed) -> list[dict]:
	"""What was won each month, and what the open opportunities will bring in,
	each by its probability, in the month it is expected to close. One whose
	closing date has passed is late, not forecast (Opportunity Forecast has it
	as Overdue)."""
	months = story_months(back=MONTHS - AHEAD, ahead=AHEAD)
	day = getdate(today())
	won = dict(zip((one.isoformat() for one in months), _won(closed, months), strict=True))
	ahead = defaultdict(float)
	for one in measure.deals(measure.alive()):
		if one.expected_closing and getdate(one.expected_closing) >= day:
			ahead[month_of(one.expected_closing)] += measure.value(one) * flt(one.probability) / 100
	return [
		{"month": key, "won": won[key], "forecast": ahead[key]} for key in (one.isoformat() for one in months)
	]


def _funnel(opportunities) -> list[dict]:
	"""Of the opportunities opened in the twelve months, how many reached each
	paper: a quotation sent, a sales order, a sales invoice, and paid."""
	reached = defaultdict(int)
	for one in chain.follow([row.name for row in opportunities]).values():
		for step in chain.reached(one):
			reached[step] += 1
	shown = [step for step in FUNNEL if can("Sales Invoice" if step == "Paid" else step)]
	return [{"step": step, "count": reached[step]} for step in shown]


def _stages() -> list[dict]:
	"""What the open opportunities are worth in each stage, in stage order,
	On Hold included and marked."""
	by = defaultdict(lambda: {"count": 0, "value": 0.0})
	for one in measure.deals(
		{"status": ["in", measure.next_step.OPEN["Opportunity"]]}, fields=("sales_stage",)
	):
		by[one.sales_stage or ""]["count"] += 1
		by[one.sales_stage or ""]["value"] += measure.value(one)
	out = []
	for stage in stages.stages():
		if (stage.one_outcome or "Open") in stages.CLOSED or stage.name not in by:
			continue
		out.append({"stage": stage.name, "held": stage.one_outcome == stages.HOLD, **by.pop(stage.name)})
	if "" in by:
		out.append({"stage": None, "held": False, **by.pop("")})
	return out


def _name(user: str | None) -> str:
	return frappe.utils.get_fullname(user) if user else measure.not_recorded()


def _owners(closed) -> list[dict]:
	"""For each owner, what their open opportunities are worth and what they
	won in the twelve months, the most first."""
	by = defaultdict(lambda: {"open": 0.0, "won": 0.0})
	for one in measure.deals(measure.alive()):
		by[one.opportunity_owner]["open"] += measure.value(one)
	for one in closed:
		if one.outcome == "Won":
			by[one.opportunity_owner]["won"] += one.worth
	rows = [{"owner": owner, "name": _name(owner), **said} for owner, said in by.items()]
	return sorted(rows, key=lambda one: -(one["open"] + one["won"]))[:FEW]


def _lost(closed) -> list[dict]:
	"""Why opportunities were lost in the twelve months, a reason at a time.
	One lost for two reasons counts under both, as Won and Lost counts it."""
	lost = [one.name for one in closed if one.outcome == "Lost"]
	by = defaultdict(int)
	given = set()
	for row in frappe.get_all(
		"Opportunity Lost Reason Detail",
		filters={"parenttype": "Opportunity", "parent": ["in", lost or [""]]},
		fields=["parent", "lost_reason"],
	):
		by[row.lost_reason] += 1
		given.add(row.parent)
	unsaid = len(set(lost) - given)
	if unsaid:
		by[measure.not_recorded()] += unsaid
	return sorted(
		({"reason": reason, "count": count} for reason, count in by.items()), key=lambda one: -one["count"]
	)


def _sources(leads) -> list[dict]:
	"""For each source, how many leads came in and how many of them became an
	opportunity, the most first."""
	by = defaultdict(lambda: {"leads": 0, "converted": 0})
	for one in leads:
		source = one.utm_source or measure.not_recorded()
		by[source]["leads"] += 1
		by[source]["converted"] += one.status in ("Opportunity", "Quotation", "Converted")
	rows = [{"source": source, **said} for source, said in by.items()]
	return sorted(rows, key=lambda one: -one["leads"])[:FEW]


def _won_by(closed, field: str) -> list[dict]:
	"""What was won in the twelve months, by a field of the opportunity."""
	by = defaultdict(float)
	for one in closed:
		if one.outcome == "Won":
			by[one.get(field) or measure.not_recorded()] += one.worth
	return sorted(({"name": name, "won": value} for name, value in by.items()), key=lambda one: -one["won"])[
		:FEW
	]


def _territories() -> list[dict]:
	"""What the open opportunities are worth, by territory."""
	by = defaultdict(float)
	for one in measure.deals(measure.alive(), fields=("territory",)):
		by[one.territory or measure.not_recorded()] += measure.value(one)
	return sorted(
		({"territory": name, "value": value} for name, value in by.items() if value),
		key=lambda one: -one["value"],
	)[:FEW]

