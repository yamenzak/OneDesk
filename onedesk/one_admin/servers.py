"""OneAdmin's servers: ordering the next box, and telling a box what to do.

A box's agent (deploy/server/agent.py) reads signed instructions from R2 and
answers `reported`, so no port opens. A server holds up to two benches, each a
release. A box takes about 25 minutes, so ordering runs in the background and
the server joins Settings when Pilot answers. README, Servers.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import urlparse

import boto3
import frappe

from onedesk.one_admin import boxes, faults, fleet, pilot, quota, site, tell, vault

KEYS = "one_server_keys"
CAPACITY = 5
FIRST = "main"
MISSES = 3
FILLING = 0.7
DISK_LIMIT = 85
MEMORY_LIMIT = 92
REPOSITORY = boxes.REPOSITORY


def after_a_check(misses: int, answered: bool) -> tuple[int, str | None]:
	"""How many checks in a row a server has missed, and what to say: `down`
	once, on reaching `MISSES`, and `back` when it answers again. Pure."""
	if answered:
		return 0, "back" if misses >= MISSES else None
	return misses + 1, "down" if misses + 1 == MISSES else None


def status_of(answered: bool, held: int, capacity: int) -> str:
	"""What a server's list says of it. Pure."""
	if not answered:
		return "Down"
	if capacity and held >= capacity:
		return "Full"
	return "Filling Up" if capacity and held >= FILLING * capacity else "Up"


def used(read: dict) -> dict:
	"""How full a box says it is, from Pilot's metrics. Pure."""
	return {"memory_used": read.get("memory_percent") or 0, "disk_used": read.get("disk_percent") or 0} if read else {}


def watch() -> None:
	"""Every five minutes, on the admin site: each server is asked if it is
	up, through its tunnel and lock, and the operators told if that changes."""
	if not site.is_admin():
		return
	held = quota.held_on_servers()
	for row in fleet.rows():
		if not row.pilot_host:
			continue
		try:
			read = pilot.call(row.server, "GET", "/metrics") or {}
		except faults.Refused:
			read = {}
		answered = bool(read)
		count = held.get(row.server, 0)
		frappe.db.set_value("Workspace Server", row.name, {"status": status_of(answered, count, row.capacity), "workspaces": count, **used(read)}, update_modified=False)
		key = f"one_admin_server_misses_{row.server}"
		misses, said = after_a_check(frappe.utils.cint(frappe.db.get_default(key)), answered)
		frappe.db.set_default(key, str(misses))
		if said:
			tell.server_changed(row.server, said)
		if said == "down" and not _own_address(row):
			_restart(row)


def _restart(row) -> None:
	"""One reboot for a box that stopped answering. The operators are already told."""
	try:
		boxes.reboot(_keys(), row.server, row.region or boxes.REGION)
	except Exception:
		frappe.log_error(title=f"Rebooting {row.server}")


def remove(server: str) -> None:
	"""A server kept for a workspace that has gone: the box, its Cloudflare
	entries and its row."""
	keys = _keys()
	row = fleet.row_of(server)
	if row.tenant and frappe.db.get_value("Tenant", row.tenant, "status") not in ("Archived", "Dropped"):
		frappe.throw(frappe._("{0} is still in use.").format(server))
	zone = keys["origin_zone"]
	made = {"tunnel": pilot.held(server)["tunnel"], "host": row.pilot_host, "origin_zone": zone}
	boxes.drop(keys, boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"]), server, made, zone, row.region or boxes.REGION)
	frappe.delete_doc("Workspace Server", server, ignore_permissions=True, force=True)
	pilot.forget(server)


def limits_body(url: str, token: str) -> dict:
	"""What a box's Pilot is told to warn about, and where. Pure."""
	return {
		"resource_limits": {"cpu_usage_limit": 0, "memory_usage_limit": MEMORY_LIMIT, "disk_space_limit": DISK_LIMIT},
		"webhook_endpoints": [{"url": url, "token": token, "events": ["resource_limit_breached"]}],
	}


def listen(server: str) -> None:
	"""A box's Pilot starts warning this site when its disk or memory runs short."""
	url = f"{frappe.utils.get_url()}/api/method/onedesk.one_admin.servers.pressure?server={server}"
	pilot.call(server, "PATCH", "/settings", json=limits_body(url, pilot.held(server)["agent"]))


def crossed(said: dict) -> str:
	"""What a Pilot warning says, in our words. Pure."""
	names = {"disk_space_limit": "Disk", "memory_usage_limit": "Memory"}
	found = [(names.get(one.get("limit")), one.get("reading")) for one in (said.get("context") or {}).get("breached_limits") or []]
	return ", ".join(f"{name} {round(reading)}%" for name, reading in found if name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def pressure() -> dict:
	"""A box's Pilot says it is short of disk or memory. Believed only when
	signed with that box's own secret."""
	site.require_admin()
	body = frappe.request.get_data(as_text=True)
	server = frappe.request.args.get("server") or ""
	secret = pilot.held(server).get("agent") or ""
	if not secret or not hmac.compare_digest(f"sha256={signed(secret, body)}", frappe.get_request_header("X-Pilot-Signature-256") or ""):
		raise frappe.PermissionError
	said = crossed(json.loads(body))
	if said:
		tell.server_short(server, said)
	return {"ok": True}


def next_name(held: list[str]) -> str:
	"""`box-` and the lowest number not taken. Pure."""
	number = 1
	while f"box-{number}" in held:
		number += 1
	return f"box-{number}"


def signed(secret: str, body: str) -> str:
	"""Pure."""
	return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def benches(row) -> list[dict]:
	"""A server's benches, oldest first. Each is a release."""
	return frappe.parse_json(row.benches or "[]") or [{"bench": FIRST, "state": "ready"}]


def newest_ready(rows: list[dict]) -> str:
	"""The bench new workspaces go on. Pure."""
	return next((one["bench"] for one in reversed(rows) if one.get("state") == "ready"), FIRST)


def current(row) -> str:
	return newest_ready(benches(row))


def row_of(server: str):
	return fleet.row_of(server)


def _save(row, value: list[dict]) -> None:
	frappe.db.set_value("Workspace Server", row.name, "benches", frappe.as_json(value))


def _keys() -> dict:
	"""What was handed over, with the AWS key from Settings."""
	return {
		**frappe.parse_json(vault.get(KEYS)),
		"aws_access_key_id": frappe.db.get_single_value("One Admin Settings", "aws_access_key_id"),
		"aws_secret_access_key": vault.get("aws_secret_access_key"),
	}


def _r2(keys: dict):
	return boto3.client("s3", endpoint_url=keys["r2_endpoint"], region_name="auto", aws_access_key_id=keys["assets_write_key"], aws_secret_access_key=keys["assets_write_secret"])


def _key(server: str, ident: str) -> str:
	return f"servers/{server}/{ident}.json"


def instruct(server: str, kind: str, **body) -> str:
	"""An instruction for a box's agent, signed with that box's secret."""
	keys = _keys()
	ident = f"{int(time.time() * 1000)}-{kind}"
	text = json.dumps({"id": ident, "kind": kind, **body})
	held = json.dumps({"body": text, "signature": signed(pilot.held(server)["agent"], text)})
	_r2(keys).put_object(Bucket=keys["assets_bucket"], Key=_key(server, ident), Body=held.encode())
	return ident


def _own_address(row) -> list[str]:
	"""This site's own address, when this is the box it runs on: the tunnel's
	list is written whole, and OneAdmin is not under the workspaces' wildcard."""
	if frappe.db.get_value("Tenant", {"is_house": 1}, "server") != row.server:
		return []
	return [urlparse(frappe.utils.get_url()).hostname]


def prepare(row, release: str) -> None:
	"""The box builds this release as a second bench, reachable at its own
	Pilot address behind the box's lock."""
	keys = _keys()
	about = boxes.release_of(keys, release)
	name = f"r{release[:8]}"
	host = f"pilot-{row.server}-{name}.{keys['origin_zone']}"
	rows = benches(row)
	tenant_domain = frappe.get_cached_value("One Admin Settings", None, "tenant_domain")
	others = [one["host"] for one in rows if one.get("host")]
	cloudflare = boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"])
	cloudflare.add_bench(f"one-{row.server}", pilot.held(row.server)["tunnel"], [row.pilot_host, *others, host, *_own_address(row), row.origin_host, f"*.{tenant_domain}"], host, keys["origin_zone"], tell.operators())
	_save(row, [*rows, {"bench": name, "release": release, "host": host, "state": "preparing"}])
	instruct(row.server, "prepare", bench=name, release=release, frappe=about["frappe"], erpnext=about["erpnext"], hrms=about["hrms"], repository=REPOSITORY, branch="main", host=host)


def begin(tenant: str | None = None) -> None:
	"""Queue the order, once. A named workspace gets a server of its own."""
	if not vault.get(KEYS) or not vault.get("aws_secret_access_key"):
		frappe.throw(frappe._("Server keys are not set."))
	frappe.enqueue("onedesk.one_admin.servers.build", queue="long", timeout=3 * 3600, job_id=f"one_admin_order_server_{tenant or 'shared'}", deduplicate=True, tenant=tenant)


def costs_of(tenant: str | None) -> int:
	return 44 if tenant else 24


def build(tenant: str | None = None) -> str:
	"""The box made and listed under Servers, open for new workspaces."""
	site.require_admin()
	keys = _keys()
	settings = frappe.get_single("One Admin Settings")
	name = next_name([one.server for one in fleet.rows()])
	region = keys.get("region") or boxes.REGION
	zone = keys["origin_zone"]
	release = boxes.latest_release(keys)
	cloudflare = boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"])

	def kept(made: dict) -> None:
		pilot.remember(name, made["access"]["client_id"], made["access"]["client_secret"], made["pilot_password"], made["tunnel"], made["agent"])

	try:
		made = boxes.new(keys, cloudflare, name, zone, settings.tenant_domain, zone, tell.operators(), release, region=region, bundle=boxes.OWN_BUNDLE if tenant else boxes.BUNDLE, on_made=kept, admin_url=frappe.utils.get_url())
	except Exception:
		frappe.log_error(title=f"Ordering {name} failed")
		raise
	doc = frappe.get_doc(
		{
			"doctype": "Workspace Server",
			"server": name,
			"region": region,
			"eu": int(region.startswith("eu-")),
			"open": 0 if tenant else 1,
			"capacity": 1 if tenant else CAPACITY,
			"tenant": tenant,
			"pilot_host": made["host"],
			"origin_host": made["origin"],
			"benches": frappe.as_json([{"bench": FIRST, "release": release, "state": "ready"}]),
			"provider": "AWS",
			"monthly_cost": costs_of(tenant),
		}
	)
	doc.flags.ordered = True
	doc.insert(ignore_permissions=True)
	listen(name)
	return name


@frappe.whitelist(allow_guest=True, methods=["POST"])
def reported() -> dict:
	"""A box's agent says how an instruction went. Believed only when signed
	with that box's own secret."""
	site.require_admin()
	body = frappe.request.get_data(as_text=True)
	said = json.loads(body)
	server = said.get("server") or ""
	secret = pilot.held(server).get("agent") or ""
	if not secret or not hmac.compare_digest(signed(secret, body), frappe.get_request_header("X-One-Agent") or ""):
		raise frappe.PermissionError
	from onedesk.one_admin import releases

	releases.heard(server, said)
	keys = _keys()
	_r2(keys).delete_object(Bucket=keys["assets_bucket"], Key=_key(server, said["id"]))
	return {"ok": True}
