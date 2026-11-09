"""What OneAdmin's Home reads. The figures come from the records and the price
list; nothing here changes anything."""

from collections import Counter

import frappe
from frappe.utils import add_months, get_first_day, getdate, today

from onedesk.one_admin import fleet, home, ledger, operator, price_list

MONTHS = 12
GONE = ("Archived", "Dropped", "Failed")


def months(count: int = MONTHS) -> list[str]:
	"""The first day of each of the last months, oldest first."""
	first = get_first_day(today())
	return [str(add_months(first, step - count + 1)) for step in range(count)]


def growth(joined: list, upto: list[str]) -> list[int]:
	"""How many had joined by the end of each month. Pure."""
	return [sum(1 for day in joined if str(day)[:7] <= month[:7]) for month in upto]


def _tenants() -> list:
	return frappe.get_all("Tenant", filters={"is_house": 0}, fields=["name", "workspace_name", "status", "offering", "creation"])


def _revenue(tenants: list) -> tuple[float, str, dict]:
	"""What live workspaces pay a month, at their plan's price, and how many are on each plan."""
	live = [one.offering for one in tenants if one.status == "Live" and one.offering]
	sold = frappe.get_all("Offering", filters={"name": ["in", live or [""]]}, fields=["name", "label", "amount", "currency", "recurring"])
	by = {one.name: one for one in sold}
	total = sum(by[one].amount for one in live if one in by and by[one].recurring)
	plans = Counter(by[one].label for one in live if one in by)
	return total, next((one.currency for one in sold), price_list.CURRENCY), plans


def _servers() -> list[dict]:
	return [{"server": one.server, "memory": one.memory_used, "disk": one.disk_used, "workspaces": one.workspaces, "cost": one.monthly_cost} for one in fleet.rows()]


@frappe.whitelist()
@frappe.read_only()
def overview() -> dict:
	"""OneAdmin's Home: the figures, the charts behind them, and what needs the operator."""
	operator._may()
	tenants = _tenants()
	revenue, currency, plans = _revenue(tenants)
	servers = _servers()
	span = months()
	counted = [one for one in tenants if one.status not in GONE]
	joined = growth([getdate(one.creation) for one in counted], span)
	credits = ledger.by_month(span[0])
	spent = {str(row.month)[:7]: row.credits for row in credits}
	start = add_months(today(), -1)
	names = {one.name: one.workspace_name or one.name for one in tenants}
	top = sorted(ledger.usage(start, today(), ["tenant"]), key=lambda row: row.get("credits") or 0, reverse=True)[:8]
	return {
		"currency": currency,
		"live": sum(1 for one in tenants if one.status == "Live"),
		"revenue": revenue,
		"cost": sum(one["cost"] or 0 for one in servers),
		"credits": [spent.get(month[:7], 0) for month in span],
		"months": span,
		"joined": joined,
		"status": [{"status": frappe._(name), "workspaces": count} for name, count in Counter(one.status for one in counted).items()],
		"plans": [{"plan": name, "workspaces": count} for name, count in plans.items()],
		"spenders": [{"name": names.get(row.get("tenant"), row.get("tenant")), "credits": row.get("credits") or 0} for row in top],
		"servers": servers,
		"needs": home.needs(),
	}
