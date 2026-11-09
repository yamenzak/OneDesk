"""What OneAdmin's own screens read. The figures come from the records and the
price list; nothing here changes anything."""

import frappe

from onedesk.one_admin import fleet, home, operator, price_list


def _monthly_revenue() -> tuple[float, str]:
	"""What live workspaces pay a month, at their plan's price."""
	live = frappe.get_all("Tenant", filters={"status": "Live", "is_house": 0, "offering": ["is", "set"]}, pluck="offering")
	amounts = frappe.get_all("Offering", filters={"name": ["in", live or [""]], "recurring": 1}, fields=["name", "amount", "currency"])
	price = {one.name: one.amount for one in amounts}
	return sum(price.get(one, 0) for one in live), next((one.currency for one in amounts), price_list.CURRENCY)


def _servers() -> list[dict]:
	return [
		{
			"name": one.name,
			"server": one.server,
			"provider": one.provider,
			"region": one.region,
			"status": one.status,
			"workspaces": one.workspaces,
			"capacity": one.capacity,
			"memory": one.memory_used,
			"disk": one.disk_used,
			"cost": one.monthly_cost,
			"own": one.tenant,
			"release": (frappe.parse_json(one.benches or "[]") or [{}])[-1].get("release", "")[:8],
		}
		for one in fleet.rows()
	]


@frappe.whitelist()
@frappe.read_only()
def overview() -> dict:
	"""OneAdmin's first screen."""
	operator._may()
	revenue, currency = _monthly_revenue()
	servers = _servers()
	needs = home.needs()
	return {
		"live": frappe.db.count("Tenant", {"status": "Live", "is_house": 0}),
		"revenue": revenue,
		"currency": currency,
		"cost": sum(one["cost"] or 0 for one in servers),
		"needs": needs,
		"servers": servers,
	}


@frappe.whitelist()
@frappe.read_only()
def servers() -> list[dict]:
	"""Every server, on any provider."""
	operator._may()
	return _servers()
