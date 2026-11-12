"""What OneAdmin's Home reads. The figures come from the records and the price
list; nothing here changes anything."""

from collections import Counter

import frappe
from frappe import _lt
from frappe.utils import add_days, add_months, get_first_day, getdate, today

from onedesk.one_admin import earnings, fleet, health, home, ledger, operator, price_list, rollout

MONTHS = 12
GONE = ("Archived", "Dropped", "Failed")
FUNNEL_DAYS = 90
ERROR_DAYS = 30
MOST_ERRORS = 8
PAID = ("Paid", "Provisioning", "Done")
SERVING = ("Live", "Overdue")
STAGES = {"Started": _lt("Started"), "Checkout": _lt("Checkout"), "Paid": _lt("Paid"), "Live": _lt("Live")}


def months(count: int = MONTHS) -> list[str]:
	"""The first day of each of the last months, oldest first."""
	first = get_first_day(today())
	return [str(add_months(first, step - count + 1)) for step in range(count)]


def growth(joined: list, upto: list[str]) -> list[int]:
	"""How many had joined by the end of each month. Pure."""
	return [sum(1 for day in joined if str(day)[:7] <= month[:7]) for month in upto]


def _tenants() -> list:
	return frappe.get_all("Tenant", filters={"is_house": 0, "is_test": 0}, fields=["name", "workspace_name", "status", "offering", "creation"])


def _servers() -> list[dict]:
	return [{"server": one.server, "memory": one.memory_used, "disk": one.disk_used, "workspaces": one.workspaces, "capacity": one.capacity, "status": one.status, "cost": one.monthly_cost} for one in fleet.rows()]


def _paid(one) -> bool:
	return one.status in PAID or bool(one.tenant)


def funnel(asked: list, serving: set) -> list[dict]:
	"""How far each signup got: started, went to pay, paid, then serving its
	workspace. Each stage counts those that reached it. Pure."""
	paid = [one for one in asked if _paid(one)]
	return [
		{"stage": "Started", "signups": len(asked)},
		{"stage": "Checkout", "signups": sum(1 for one in asked if one.stripe_session or _paid(one))},
		{"stage": "Paid", "signups": len(paid)},
		{"stage": "Live", "signups": sum(1 for one in paid if one.tenant in serving)},
	]


def by_month(asked: list, upto: list[str]) -> list[dict]:
	"""Signups started and paid in each month. Pure."""
	return [
		{
			"month": month,
			"started": sum(1 for one in asked if str(one.creation)[:7] == month[:7]),
			"paid": sum(1 for one in asked if str(one.creation)[:7] == month[:7] and _paid(one)),
		}
		for month in upto
	]


def _signups(span: list[str], tenants: list) -> dict:
	asked = frappe.get_all("Account Request", filters={"creation": [">=", span[0]]}, fields=["status", "tenant", "stripe_session", "creation"])
	since = str(add_days(today(), -FUNNEL_DAYS))
	serving = {one.name for one in tenants if one.status in SERVING}
	recent = [one for one in asked if str(one.creation) >= since]
	month = [one for one in asked if str(one.creation) >= str(add_days(today(), -30))]
	return {"funnel": [{**one, "stage": str(STAGES[one["stage"]])} for one in funnel(recent, serving)], "signups": by_month(asked, span), "signups_now": len(month)}


def _errors(names: dict) -> dict:
	"""New kinds of error each day, and where the open ones are."""
	start = add_days(today(), -ERROR_DAYS + 1)
	rows = frappe.get_all("Workspace Error", filters={"first_seen": [">=", start]}, fields=["first_seen"])
	found = Counter(str(getdate(one.first_seen)) for one in rows)
	days = [str(add_days(start, step)) for step in range(ERROR_DAYS)]
	open_ = frappe.get_all("Workspace Error", filters={"status": "Open"}, fields=["tenant", "occurrences"])
	where = Counter()
	for one in open_:
		where[names.get(one.tenant, one.tenant)] += one.occurrences or 1
	return {
		"errors": [{"day": day, "errors": found.get(day, 0)} for day in days] if rows else [],
		"open_errors": len(open_),
		"error_places": [{"name": name, "errors": value} for name, value in where.most_common(MOST_ERRORS)],
	}


def _health() -> list[dict]:
	found = []
	for service in health.SERVICES:
		last = health._latest(service)
		found.append({"service": service, "label": frappe._(service), "state": last.state if last else health.NOT_SET_UP, "checked_at": last.checked_at if last else None})
	return found


def _plans() -> list[dict]:
	live, add_ons, sold = earnings._live()
	return earnings._by_plan(earnings.bills(live, add_ons, sold))


@frappe.whitelist()
@frappe.read_only()
def overview() -> dict:
	"""OneAdmin's Home: the figures, the charts behind them, and what needs the operator."""
	operator._may()
	tenants = _tenants()
	plans = _plans()
	servers = _servers()
	span = months()
	counted = [one for one in tenants if one.status not in GONE]
	joined = growth([getdate(one.creation) for one in counted], span)
	credits = ledger.by_month(span[0])
	spent = {str(row.month)[:7]: row.credits for row in credits}
	calls = {str(row.month)[:7]: row.calls for row in credits}
	start = add_months(today(), -1)
	names = {one.name: one.workspace_name or one.name for one in tenants}
	top = sorted(ledger.usage(start, today(), ["tenant"]), key=lambda row: row.get("credits") or 0, reverse=True)[:8]
	invoiced, invoiced_in = earnings._invoiced(span)
	return {
		**_signups(span, tenants),
		**_errors(names),
		"invoiced": invoiced,
		"invoiced_in": invoiced_in,
		"calls": [calls.get(month[:7], 0) for month in span],
		"health": _health(),
		"rollout": rollout.summary(),
		"currency": price_list.CURRENCY,
		"live": sum(1 for one in tenants if one.status == "Live"),
		"revenue": sum(one["revenue"] for one in plans),
		"cost": sum(one["cost"] or 0 for one in servers),
		"credits": [spent.get(month[:7], 0) for month in span],
		"months": span,
		"joined": joined,
		"status": [{"status": frappe._(name), "workspaces": count} for name, count in Counter(one.status for one in counted).items()],
		"plans": plans,
		"spenders": [{"name": names.get(row.get("tenant"), row.get("tenant")), "credits": row.get("credits") or 0} for row in top],
		"servers": servers,
		"needs": home.needs(),
	}
