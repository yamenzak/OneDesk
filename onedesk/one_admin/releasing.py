"""Releasing a machine we connected: Release Server ends its sessions and
gives one line to run on it, `deploy/server/release.sh`, which removes what
`connect.sh` made there in the reverse order. When the machine says it ran,
or an operator presses Finish Release, its tunnel, addresses and lock go from
Cloudflare, its instructions from R2, its keys and what was kept under its
name here, and the row stays as Released. AGENTS.md, Releasing a server.
"""

import hmac
import json
import secrets
import shlex

import frappe
import frappe.defaults
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import sha256_hash
from werkzeug.wrappers import Response

from onedesk.one_admin import boxes, cloudflare, faults, fleet, pilot, servers, site

RELEASING = fleet.RELEASING
RELEASED = fleet.RELEASED
SCRIPT = boxes.ROOT / "deploy/server/release.sh"
GONE = ("Archived", "Dropped")
SESSION = "Workspace Session"
SESSION_GONE = "Deleted"
CLEARED = {"status": RELEASED, "open": 0, "pilot_host": None, "origin_host": None, "benches": "[]", "spares": None, "workspaces": 0, "memory_used": 0, "disk_used": 0}


def why_not(row, placed: list[str]) -> str | None:
	"""Why a server may not be released: `ordered` (on AWS, deleted from
	Home instead), `released` already, or `placed` while workspaces are on
	it. None when it may. Pure."""
	if not row.connected:
		return "ordered"
	if row.status == RELEASED:
		return "released"
	if placed:
		return "placed"
	return None


def script_for(server: str, agent: str, admin_url: str) -> str:
	"""release.sh, headed by the server's name, the secret it signs its
	answer with and where it sends it."""
	told = (("ONE_SERVER", server), ("ONE_AGENT", agent), ("ONE_ADMIN", admin_url.rstrip("/")))
	return "".join(f"{key}={shlex.quote(value)}\n" for key, value in told) + SCRIPT.read_text()


def _row(server: str):
	row = fleet.row_of(server)
	if not row:
		frappe.throw(_("{0} is not a server.").format(server), frappe.DoesNotExistError)
	return row


def _placed(server: str) -> list[str]:
	found = frappe.get_all("Tenant", filters={"server": server, "status": ["not in", GONE]}, fields=["name", "workspace_name"], order_by="workspace_name asc")
	return [one.workspace_name or one.name for one in found]


def begin(server: str) -> dict:
	"""Release Server: the sessions on it end with their addresses, the row
	reads Releasing, and the line to run on the machine. Asked again, a new
	line."""
	row = _row(server)
	placed = _placed(server)
	why = why_not(row, placed)
	if why == "ordered":
		frappe.throw(_("{0} is a box we ordered. Only a machine you connected can be released.").format(server))
	if why == "released":
		frappe.throw(_("{0} is already released.").format(server))
	if why == "placed":
		frappe.throw(_("{0} still holds {1}. Move each to another server first.").format(server, ", ".join(placed)))
	ended = end_sessions(server)
	frappe.db.set_value(fleet.DOCTYPE, row.name, {"status": RELEASING, "open": 0})
	return {"server": server, "command": command(server), "sessions": ended}


def end_sessions(server: str) -> int:
	"""Every session on the server deleted, its address first. Its site goes
	with the machine, so Pilot is not asked."""
	found = frappe.get_all(SESSION, filters={"server": server, "status": ["!=", SESSION_GONE]}, fields=["name", "slug"])
	for one in found:
		if one.slug:
			cloudflare.forget(one.slug)
		frappe.db.set_value(SESSION, one.name, {"status": SESSION_GONE, "task": None, "error": None})
	return len(found)


def command(server: str) -> str:
	"""The line that releases a machine: a ticket good for one hour and one use."""
	ticket = secrets.token_urlsafe(24)
	frappe.cache().set_value(_ticket(ticket), server, expires_in_sec=servers.TICKET_LASTS)
	return f"curl -fsSL '{frappe.utils.get_url()}/api/method/onedesk.one_admin.releasing.release_script?ticket={ticket}' | sudo bash"


def _ticket(ticket: str) -> str:
	return f"one_admin_release:{sha256_hash(ticket)}"


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=20, seconds=3600)
def release_script(ticket: str) -> Response:
	"""What the release line fetches: once, for one server, with the ticket."""
	site.require_admin()
	key = _ticket(ticket)
	server = frappe.cache().get_value(key)
	row = fleet.row_of(server) if server else None
	if not row or row.status != RELEASING:
		raise frappe.PermissionError
	frappe.cache().delete_value(key)
	return Response(script_for(server, pilot.held(server)["agent"], frappe.utils.get_url()), mimetype="text/plain")


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=3600)
def released() -> dict:
	"""The machine says release.sh ran. Believed only when signed with that
	box's own secret, and only while it is Releasing."""
	site.require_admin()
	body = frappe.request.get_data(as_text=True)
	said = json.loads(body or "{}")
	row = fleet.row_of(said.get("server") or "")
	if row and row.status == RELEASED:
		return {"ok": True}
	try:
		secret = (pilot.held(row.server).get("agent") or "") if row and row.status == RELEASING else ""
	except faults.Refused:
		secret = ""
	if not secret or not hmac.compare_digest(servers.signed(secret, body), frappe.get_request_header("X-One-Agent") or ""):
		raise frappe.PermissionError
	finish(row.server)
	return {"ok": True}


def _kept(server: str) -> dict | None:
	try:
		return pilot.held(server)
	except faults.Refused:
		return None


def finish(server: str) -> list[str]:
	"""What OneAdmin holds for a released machine, gone, each step safe to
	run again: its tunnel, addresses and lock on Cloudflare, its instructions
	on R2, what was kept under its name, its keys, and the row cleared to
	Released. What was done, by name."""
	row = _row(server)
	if row.status == RELEASED:
		return []
	if row.status != RELEASING:
		frappe.throw(_("Release {0} first.").format(server))
	done = []
	held = _kept(server)
	if held:
		keys = servers._keys()
		if held.get("tunnel") and forget_on_cloudflare(boxes.Cloudflare(keys["cloudflare_account"], keys["cloudflare_token"]), server, held["tunnel"], row.pilot_host, keys["origin_zone"]):
			done.append("cloudflare")
		if clear_r2(servers._r2(keys), keys["assets_bucket"], server):
			done.append("r2")
	clear_kept(server)
	done.append("defaults")
	if held:
		pilot.forget(server)
		done.append("keys")
	frappe.db.set_value(fleet.DOCTYPE, row.name, CLEARED)
	return done


def forget_on_cloudflare(account: boxes.Cloudflare, server: str, tunnel: str, host: str | None, zone: str) -> bool:
	"""The tunnel, every address pointing at it, its lock and its token, when
	the tunnel is still there. False when it was already gone."""
	if not account.has_tunnel(f"one-{server}", tunnel):
		return False
	account.forget(f"one-{server}", tunnel, host or boxes.admin_host(server, zone), [zone])
	return True


def clear_r2(store, bucket: str, server: str) -> int:
	"""Every instruction left for the server on R2: how many went."""
	listed = store.list_objects_v2(Bucket=bucket, Prefix=f"servers/{server}/").get("Contents") or []
	for one in listed:
		store.delete_object(Bucket=bucket, Key=one["Key"])
	return len(listed)


def clear_kept(server: str) -> None:
	"""What OneAdmin wrote under the server's name: its missed checks and its
	Pilot sign-ins."""
	frappe.defaults.clear_default(key=f"one_admin_server_misses_{server}")
	frappe.cache().delete_keys(f"one_admin_pilot_session:{server}:")
