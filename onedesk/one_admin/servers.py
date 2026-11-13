"""OneAdmin's servers: ordering the next box, and telling a box what to do.

A box's agent (deploy/server/agent.py) reads signed instructions from R2 and
answers `reported`, so no port opens. A server holds up to two benches, each a
release. A box takes about 25 minutes, so ordering runs in the background and
the server joins Settings when Pilot answers. AGENTS.md, Servers.
"""

import hashlib
import hmac
import json
import secrets
import time
from urllib.parse import urlparse

import boto3
import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import sha256_hash
from werkzeug.wrappers import Response

from onedesk.one_admin import boxes, faults, fleet, pilot, providers, quota, site, tell, vault

KEYS = "one_server_keys"
CAPACITY = 5
FIRST = "main"
MISSES = 3
REGION_CODES = {"eu-north-1": "se"}
FILLING = 0.7
DISK_LIMIT = 85
MEMORY_LIMIT = 92
REPOSITORY = boxes.REPOSITORY
SITE_EVENTS = ("site_down", "site_up")
CONNECTED_NAME = "machine"
CONNECTING = "Connecting"
COPIES_AT_ONCE = 4
TICKET_LASTS = 3600
AGENT_UPDATE = "update-agent"


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
		if row.status == CONNECTING:
			if answered:
				_connected(row)
			continue
		count = held.get(row.server, 0)
		frappe.db.set_value("Workspace Server", row.name, {"status": status_of(answered, count, row.capacity), "workspaces": count, **used(read)}, update_modified=False)
		key = f"one_admin_server_misses_{row.server}"
		misses, said = after_a_check(frappe.utils.cint(frappe.db.get_default(key)), answered)
		frappe.db.set_default(key, str(misses))
		if said:
			tell.server_changed(row.server, said)
		if said == "down" and row.provider == "AWS" and not _own_address(row):
			_restart(row)


def _restart(row) -> None:
	"""One reboot for a box that stopped answering. The operators are already told."""
	try:
		boxes.reboot(_keys(), row.server, row.region or boxes.REGION)
	except Exception:
		frappe.log_error(title=f"Rebooting {row.server}")


def _connected(row) -> None:
	"""A connected machine answered for the first time. Its copies get a share
	of the container's memory, and its backups stay on the machine: a copy is
	not kept (README, Servers)."""
	keys = pilot.held(row.server)
	try:
		boxes.settle(row.pilot_host, {"client_id": keys["id"], "client_secret": keys["secret"]}, keys["password"], {}, share=boxes.CONTAINER_MEMORY_SHARE)
		listen(row.server)
	except Exception:
		frappe.log_error(title=f"Connecting {row.server}")
		return
	frappe.db.set_value("Workspace Server", row.name, "status", "Up", update_modified=False)
	tell.server_connected(row.server)


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
		"resource_limits": {"cpu_usage_limit": 0, "memory_usage_limit": MEMORY_LIMIT, "disk_space_limit": DISK_LIMIT, "site_uptime": True},
		"webhook_endpoints": [{"url": url, "token": token, "events": ["resource_limit_breached", *SITE_EVENTS]}],
	}


def listen(server: str) -> None:
	"""A box's Pilot starts warning this site when its disk or memory runs short."""
	url = f"{frappe.utils.get_url()}/api/method/onedesk.one_admin.servers.pressure?server={server}"
	pilot.call(server, "PATCH", "/settings", json=limits_body(url, pilot.held(server)["agent"]))


def sites_of(heard: dict) -> list[str]:
	"""The sites a Pilot event names: `context.sites` when several went down
	together, its own `site` otherwise. Pure."""
	listed = [one["site"] for one in (heard.get("context") or {}).get("sites") or [] if one.get("site")]
	return listed or ([heard["site"]] if heard.get("site") else [])


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
	heard = json.loads(body)
	if heard.get("event") in SITE_EVENTS:
		from onedesk.one_admin import health

		health.pilot_said(sites_of(heard), heard["event"] == "site_up")
		return {"ok": True}
	said = crossed(heard)
	if said:
		tell.server_short(server, said)
	return {"ok": True}


def next_name(held: list[str], region: str) -> str:
	"""The region's code and the lowest number not taken. Pure."""
	code = REGION_CODES.get(region, region.split("-")[0])
	number = 1
	while f"{code}-{number}" in held:
		number += 1
	return f"{code}-{number}"


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


def _with_github(keys: dict) -> dict:
	"""The keys a new box is built with, carrying the GitHub token it starts with."""
	from onedesk.one_admin import github_app

	return {**keys, "github_token": github_app.for_boxes(keys)}


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


def _tunnel_hosts(row, rows: list[dict]) -> list[str]:
	"""Every address the box's tunnel answers for, from its row and these
	benches: the list is written whole."""
	tenant_domain = frappe.get_cached_value("One Admin Settings", None, "tenant_domain")
	return [row.pilot_host, *(one["host"] for one in rows if one.get("host")), *_own_address(row), row.origin_host, f"*.{tenant_domain}"]


def bench_dropped(row, bench: str) -> None:
	"""A box dropped a bench: it leaves the row, then the tunnel, its address
	and its lock. A Cloudflare failure is logged and the row stays changed;
	the next bench prepared on this box clears what was left."""
	rows = [one for one in benches(row) if one["bench"] != bench]
	_save(row, rows)
	try:
		keys = _keys()
		boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"]).drop_bench(f"one-{row.server}", pilot.held(row.server)["tunnel"], _tunnel_hosts(row, rows), keys["origin_zone"])
	except Exception:
		frappe.log_error(title=f"Clearing bench {bench} of {row.server} on Cloudflare")


def prepare(row, release: str) -> None:
	"""The box unpacks this release as a second bench, reachable at its own
	Pilot address behind the box's lock, its agent updated first so it is
	never older than the release it builds. A release with a template site
	makes this bench's spares from it."""
	keys = _keys()
	about = boxes.release_of(keys, release)
	name = f"r{release[:8]}"
	host = f"pilot-{row.server}-{name}.{keys['origin_zone']}"
	rows = benches(row)
	cloudflare = boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"])
	cloudflare.add_bench(f"one-{row.server}", pilot.held(row.server)["tunnel"], _tunnel_hosts(row, [*rows, {"host": host}]), host, keys["origin_zone"], tell.operators())
	_save(row, [*rows, {"bench": name, "release": release, "host": host, "state": "preparing", "template": bool(about.get("template")), "prepared_at": str(frappe.utils.now_datetime())}])
	source = boxes.agent_of(keys, release)
	if source:
		instruct(row.server, AGENT_UPDATE, source=source)
	instruct(row.server, "prepare", bench=name, release=release, frappe=about["frappe"], erpnext=about["erpnext"], hrms=about["hrms"], repository=REPOSITORY, branch="main", host=host)


def begin(tenant: str | None = None) -> None:
	"""Queue the order, once. A named workspace gets a server of its own."""
	if not vault.get(KEYS) or not vault.get("aws_secret_access_key"):
		frappe.throw(frappe._("Server keys are not set."))
	frappe.enqueue("onedesk.one_admin.servers.build", queue="long", timeout=3 * 3600, job_id=f"one_admin_order_server_{tenant or 'shared'}", deduplicate=True, tenant=tenant)


def connect() -> dict:
	"""A machine that is not on AWS listed under Servers, and the one line
	that joins it. Its tunnel, address and lock are made now, under a name
	that stays (`machine-N`: Cloudflare and Pilot's keys hold it); the
	machine asks for its first boot with the ticket in the line and says
	which cloud it is on in `located`. A machine already waiting to join is
	given a new line."""
	site.require_admin()
	waiting = next((one.server for one in fleet.rows() if one.status == CONNECTING), None)
	if waiting:
		return {"server": waiting, "command": connect_command(waiting)}
	if not vault.get(KEYS):
		frappe.throw(frappe._("Server keys are not set."))
	keys = _keys()
	settings = frappe.get_single("One Admin Settings")
	name = next_name([one.server for one in fleet.rows()], CONNECTED_NAME)
	zone = keys["origin_zone"]
	release = boxes.latest_release(keys)
	cloudflare = boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"])

	def kept(made: dict) -> None:
		pilot.remember(name, made["access"]["client_id"], made["access"]["client_secret"], made["pilot_password"], made["tunnel"], made["agent"])

	made = boxes.connect(keys, cloudflare, name, zone, settings.tenant_domain, zone, tell.operators(), on_made=kept)
	doc = frappe.get_doc(
		{
			"doctype": "Workspace Server",
			"server": name,
			"status": CONNECTING,
			"open": 0,
			"capacity": COPIES_AT_ONCE,
			"pilot_host": made["host"],
			"origin_host": made["origin"],
			"benches": frappe.as_json([{"bench": FIRST, "release": release, "state": "ready"}]),
			"provider": providers.OTHER,
			"connected": 1,
			"monthly_cost": 0,
		}
	)
	doc.flags.ordered = True
	doc.insert(ignore_permissions=True)
	return {"server": name, "command": connect_command(name)}


def connect_command(server: str) -> str:
	"""The line that joins a machine: a ticket good for one hour and one use."""
	ticket = secrets.token_urlsafe(24)
	frappe.cache().set_value(_ticket(ticket), server, expires_in_sec=TICKET_LASTS)
	return f"curl -fsSL '{frappe.utils.get_url()}/api/method/onedesk.one_admin.servers.connect_script?ticket={ticket}' | sudo bash"


def _ticket(ticket: str) -> str:
	return f"one_admin_connect:{sha256_hash(ticket)}"


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=20, seconds=3600)
def connect_script(ticket: str) -> Response:
	"""What the connect line fetches: once, for one server, with the ticket."""
	site.require_admin()
	key = _ticket(ticket)
	server = frappe.cache().get_value(key)
	row = fleet.row_of(server) if server else None
	if not row or row.status != CONNECTING:
		raise frappe.PermissionError
	frappe.cache().delete_value(key)
	keys = _with_github(_keys())
	held = pilot.held(server)
	made = {"tunnel": held["tunnel"], "host": row.pilot_host, "pilot_password": held["password"], "agent": held["agent"]}
	cloudflare = boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"])
	script = boxes.connect_script(keys, cloudflare, server, made, boxes.latest_release(keys), frappe.utils.get_url())
	return Response(script, mimetype="text/plain")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def located() -> dict:
	"""A joining machine says what its cloud's metadata service told it, and
	the server takes that provider and region. Believed only when signed with
	that box's own secret, and only while it is Connecting."""
	site.require_admin()
	body = frappe.request.get_data(as_text=True)
	said = json.loads(body or "{}")
	row = fleet.row_of(said.get("server") or "")
	try:
		secret = (pilot.held(row.server).get("agent") or "") if row and row.status == CONNECTING else ""
	except faults.Refused:
		secret = ""
	if not secret or not hmac.compare_digest(signed(secret, body), frappe.get_request_header("X-One-Agent") or ""):
		raise frappe.PermissionError
	provider, region = providers.where(providers.decoded(said.get("found")))
	frappe.db.set_value("Workspace Server", row.name, {"provider": provider, "region": region}, update_modified=False)
	return {"ok": True}


def costs_of(tenant: str | None) -> int:
	return 44 if tenant else 24


def build(tenant: str | None = None) -> str:
	"""The box made and listed under Servers, open for new workspaces."""
	site.require_admin()
	keys = _with_github(_keys())
	settings = frappe.get_single("One Admin Settings")
	region = keys.get("region") or boxes.REGION
	name = f"own-{frappe.db.get_value('Tenant', tenant, 'slug')}" if tenant else next_name([one.server for one in fleet.rows()], region)
	zone = keys["origin_zone"]
	release = boxes.latest_release(keys)
	template = bool(boxes.release_of(keys, release).get("template"))
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
			"open": 0 if tenant else 1,
			"capacity": 1 if tenant else CAPACITY,
			"tenant": tenant,
			"pilot_host": made["host"],
			"origin_host": made["origin"],
			"benches": frappe.as_json([{"bench": FIRST, "release": release, "state": "ready", "template": template}]),
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
