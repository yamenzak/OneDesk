"""OneAdmin ordering the next server, with one operator's click: the keys
`scripts/server.py hand-over` gave it, the newest release in the registry and
boxes.py. A box takes about 25 minutes, so this runs in the background and
the server joins Settings when Pilot answers. README, Servers."""

import frappe

from onedesk.one_admin import boxes, pilot, site, tell, vault

KEYS = "one_server_keys"
CAPACITY = 5


def next_name(held: list[str]) -> str:
	"""`box-` and the lowest number not taken. Pure."""
	number = 1
	while f"box-{number}" in held:
		number += 1
	return f"box-{number}"


def begin() -> None:
	"""Queue the order, once."""
	if not vault.get(KEYS):
		frappe.throw(frappe._("Server keys are not set."))
	frappe.enqueue("onedesk.one_admin.servers.build", queue="long", timeout=3 * 3600, job_id="one_admin_order_server", deduplicate=True)


def build() -> str:
	"""The box made and listed under Servers, open for new workspaces."""
	site.require_admin()
	keys = frappe.parse_json(vault.get(KEYS))
	settings = frappe.get_single("One Admin Settings")
	name = next_name([one.server for one in settings.get("servers") or []])
	region = keys.get("region") or boxes.REGION
	zone = keys["origin_zone"]
	cloudflare = boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"])

	def kept(made: dict) -> None:
		pilot.remember(name, made["access"]["client_id"], made["access"]["client_secret"], made["pilot_password"], made["tunnel"])

	try:
		made = boxes.new(keys, cloudflare, name, zone, settings.tenant_domain, zone, tell.operators(), boxes.latest_release(keys), region=region, on_made=kept)
	except Exception:
		frappe.log_error(title=f"Ordering {name} failed")
		raise
	settings.append("servers", {"server": name, "region": region, "eu": int(region.startswith("eu-")), "open": 1, "capacity": CAPACITY, "pilot_host": made["host"], "origin_host": made["origin"]})
	settings.save(ignore_permissions=True)
	return name
