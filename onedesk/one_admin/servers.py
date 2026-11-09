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

import boto3
import frappe

from onedesk.one_admin import boxes, pilot, site, tell, vault

KEYS = "one_server_keys"
CAPACITY = 5
FIRST = "main"
REPOSITORY = boxes.REPOSITORY


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
	return next(one for one in frappe.get_doc("One Admin Settings").get("servers") if one.server == server)


def _save(row, value: list[dict]) -> None:
	frappe.db.set_value("Workspace Server", row.name, "benches", frappe.as_json(value))
	frappe.clear_document_cache("One Admin Settings", "One Admin Settings")


def _keys() -> dict:
	return frappe.parse_json(vault.get(KEYS))


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
	cloudflare.add_bench(f"one-{row.server}", pilot.held(row.server)["tunnel"], [row.pilot_host, *others, host, row.origin_host, f"*.{tenant_domain}"], host, keys["origin_zone"], tell.operators())
	_save(row, [*rows, {"bench": name, "release": release, "host": host, "state": "preparing"}])
	instruct(row.server, "prepare", bench=name, release=release, frappe=about["frappe"], erpnext=about["erpnext"], hrms=about["hrms"], repository=REPOSITORY, branch="main", host=host)


def begin() -> None:
	"""Queue the order, once."""
	if not vault.get(KEYS):
		frappe.throw(frappe._("Server keys are not set."))
	frappe.enqueue("onedesk.one_admin.servers.build", queue="long", timeout=3 * 3600, job_id="one_admin_order_server", deduplicate=True)


def build() -> str:
	"""The box made and listed under Servers, open for new workspaces."""
	site.require_admin()
	keys = _keys()
	settings = frappe.get_single("One Admin Settings")
	name = next_name([one.server for one in settings.get("servers") or []])
	region = keys.get("region") or boxes.REGION
	zone = keys["origin_zone"]
	release = boxes.latest_release(keys)
	cloudflare = boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"])

	def kept(made: dict) -> None:
		pilot.remember(name, made["access"]["client_id"], made["access"]["client_secret"], made["pilot_password"], made["tunnel"], made["agent"])

	try:
		made = boxes.new(keys, cloudflare, name, zone, settings.tenant_domain, zone, tell.operators(), release, region=region, on_made=kept, admin_url=frappe.utils.get_url())
	except Exception:
		frappe.log_error(title=f"Ordering {name} failed")
		raise
	settings.append(
		"servers",
		{
			"server": name,
			"region": region,
			"eu": int(region.startswith("eu-")),
			"open": 1,
			"capacity": CAPACITY,
			"pilot_host": made["host"],
			"origin_host": made["origin"],
			"benches": frappe.as_json([{"bench": FIRST, "release": release, "state": "ready"}]),
		},
	)
	settings.save(ignore_permissions=True)
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
