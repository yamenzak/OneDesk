"""What OneAdmin's Billing Home reads: what the workspaces pay, what that
leaves against the margin floor, and what OneCredits did. Nothing here
changes anything."""

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, flt, today

from onedesk.one_admin import books, console, costs, fleet, ledger, margins, operator, price_list, quota

MODELS = 8


def bills(live: list, add_ons: list, sold: dict) -> list[dict]:
	"""What each live workspace pays a month in the price list's currency, plan and add-ons, and its plan. Pure."""
	extras = defaultdict(float)
	for one in add_ons:
		if one.offering in sold:
			extras[one.parent] += costs.listed(flt(sold[one.offering].amount), sold[one.offering].currency) * max(1, one.quantity or 0)
	made = []
	for one in live:
		plan = sold.get(one.offering)
		if plan:
			made.append({"tenant": one.name, "plan": plan.label, "amount": (costs.listed(flt(plan.amount), plan.currency) if plan.recurring else 0) + extras[one.name]})
	return made


def month_cost(amounts: list[float], server_usd: float, ai_usd: float, stored_gb: float, database_gb: float) -> dict[str, float]:
	"""What a month costs us, by what it goes to, in the price list's currency. Pure."""
	backups = database_gb * costs.R2_GB_MONTH * costs.BACKUP_COMPRESSION * costs.BACKUPS_KEPT
	return {
		"stripe": round(sum(costs.stripe_fee(one) for one in amounts), 2),
		"servers": costs.usd(server_usd),
		"cloudflare": round(sum(costs.CLOUDFLARE_FIXED.values()), 2),
		"oneai": costs.usd(ai_usd),
		"storage": round(stored_gb * costs.COST["storage_gb"] + backups, 2),
	}


def margin(revenue: float, spent: dict[str, float]) -> float | None:
	"""What is left of a month's revenue, as a percentage; None when nothing is billed. Pure."""
	return round((revenue - sum(spent.values())) / revenue * 100, 1) if revenue else None


def from_first(span: list[str], values: list[float]) -> int:
	"""Where the first month with anything in it stands in `span`. Pure."""
	return next((at for at, one in enumerate(values) if one), len(span))


def _live() -> tuple[list, list, dict]:
	sold = {one.name: one for one in frappe.get_all("Offering", fields=["name", "label", "amount", "currency", "recurring"])}
	live = frappe.get_all("Tenant", filters={"is_house": 0, "is_test": 0, "status": "Live"}, fields=["name", "offering", "storage_bytes", "database_bytes"])
	add_ons = frappe.get_all("Tenant Add-on", filters={"parenttype": "Tenant", "parent": ["in", [one.name for one in live] or [""]]}, fields=["parent", "offering", "quantity"])
	return live, add_ons, sold


def _by_plan(billed: list[dict]) -> list[dict]:
	plans = defaultdict(lambda: {"workspaces": 0, "revenue": 0.0})
	for one in billed:
		plans[one["plan"]]["workspaces"] += 1
		plans[one["plan"]]["revenue"] += one["amount"]
	return [{"plan": name, **held} for name, held in plans.items()]


def _months(rows: list, key: str, span: list[str]) -> list[float]:
	held = {str(row.month)[:7]: flt(row.get(key)) for row in rows}
	return [held.get(month[:7], 0.0) for month in span]


def _credits(span: list[str], used: list) -> list[dict]:
	"""OneCredits sold and used each month, from the first month with any."""
	sold_values = _months(ledger.sold_by_month(span[0]), "credits", span)
	used_values = _months(used, "credits", span)
	first = from_first(span, [sum(one) for one in zip(sold_values, used_values)])
	return [{"month": month, "sold": sold, "used": spent} for month, sold, spent in zip(span[first:], sold_values[first:], used_values[first:])]


def _ai(span: list[str], used: list) -> list[dict]:
	"""What model calls cost us each month, from the first month with any."""
	cost = _months(used, "usd", span)
	calls = _months(used, "calls", span)
	first = from_first(span, calls)
	return [{"month": month, "cost": dollars, "calls": called} for month, dollars, called in zip(span[first:], cost[first:], calls[first:])]


def _invoiced(span: list[str]) -> tuple[list[dict], str | None]:
	"""Paid Stripe invoices each month, from the first month with any."""
	rows, currency = books.by_month(span[0])
	values = _months(rows, "amount", span)
	first = from_first(span, values)
	return [{"month": month, "amount": amount} for month, amount in zip(span[first:], values[first:])], currency


def _models(start, end) -> list[dict]:
	found = [row for row in ledger.usage(start, end, ["why"]) if row.get("credits")]
	return [{"model": row.get("why") or _("Other"), "credits": row.get("credits")} for row in found[:MODELS]]


def _this_month(rows: list[dict], month: str, key: str) -> float:
	return next((row[key] for row in rows if row["month"] == month), 0)


@frappe.whitelist()
@frappe.read_only()
def overview() -> dict:
	"""Billing's Home: this month's figures, what they leave, and the charts behind them."""
	operator._may()
	span = console.months()
	live, add_ons, sold = _live()
	billed = bills(live, add_ons, sold)
	amounts = [one["amount"] for one in billed]
	revenue = sum(amounts)
	start, end = add_days(today(), -30), add_days(today(), 1)
	spent = month_cost(
		amounts,
		sum(one.monthly_cost or 0 for one in fleet.rows()),
		flt(ledger.usage(start, end, [])[0].get("usd")),
		sum(flt(one.storage_bytes) for one in live) / quota.GB,
		sum(flt(one.database_bytes) for one in live) / quota.GB,
	)
	used = ledger.by_month(span[0])
	credits = _credits(span, used)
	invoiced, invoiced_in = _invoiced(span)
	named = (("Stripe", spent["stripe"]), ("Servers", spent["servers"]), ("Cloudflare", spent["cloudflare"]), ("OneAI", spent["oneai"]), ("Storage", spent["storage"]))
	return {
		"currency": price_list.CURRENCY,
		"revenue": revenue,
		"margin": margin(revenue, spent),
		"floor": price_list.MARGIN_FLOOR * 100,
		"priced": [{"name": one.label, "margin": round(one.margin * 100, 1)} for one in margins.priced()],
		"spent": [{"cost": _(name), "amount": amount} for name, amount in named if amount],
		"invoiced": invoiced,
		"invoiced_in": invoiced_in,
		"credits": credits,
		"sold_now": _this_month(credits, span[-1], "sold"),
		"used_now": _this_month(credits, span[-1], "used"),
		"ai": _ai(span, used),
		"models": _models(start, end),
		"plans": _by_plan(billed),
	}
