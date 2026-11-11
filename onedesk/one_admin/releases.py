"""Updates, one workspace at a time.

A new release is put on each server as a second bench, ahead of time, when
the release workflow says it is up (`released`) or the hourly check finds it.
Each workspace moves in its own window, `NOTICE_HOURS` after it is told, or
at once with Update Now; one waiting on new terms waits `HOLD_DAYS`. A bench
with nobody left is dropped. AGENTS.md, Updates.
"""

import hmac
import json
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import add_days, get_datetime, get_system_timezone, getdate, now_datetime, today

from onedesk.one_admin import boxes, fleet, private, servers, site

WEEKDAY = 5
HOUR = 1
NOTICE_HOURS = 72
HOLD_DAYS = 30
REMIND_EVERY = 7
MOST_BENCHES = 2
GONE = ("Archived", "Dropped")
RELEASE_SECRET = "one_release_secret"
FRESH_FOR = 600


def window_after(moment: datetime, notice_hours: int = NOTICE_HOURS, weekday: int = WEEKDAY, hour: int = HOUR) -> datetime:
	"""The first `weekday` at `hour` at least `notice_hours` after `moment`,
	all in one timezone. Pure."""
	earliest = moment + timedelta(hours=notice_hours)
	day = earliest.replace(hour=hour, minute=0, second=0, microsecond=0)
	day += timedelta(days=(weekday - day.weekday()) % 7)
	return day if day >= earliest else day + timedelta(days=7)


def window_for(tenant, now: datetime | None = None) -> datetime:
	"""The workspace's next window, as this site's clock reads it."""
	system = ZoneInfo(get_system_timezone())
	zone = ZoneInfo(tenant.time_zone or get_system_timezone())
	moment = (now or now_datetime()).replace(tzinfo=system).astimezone(zone).replace(tzinfo=None)
	at = window_after(moment, weekday=tenant.update_weekday, hour=tenant.update_hour)
	return at.replace(tzinfo=zone).astimezone(system).replace(tzinfo=None)


def may_move(terms_pending: bool, due: datetime, now: datetime) -> bool:
	"""Whether a workspace moves now: agreed to the terms, or its 30 days of
	waiting are up. Pure."""
	return not terms_pending or now >= due + timedelta(days=HOLD_DAYS)


def _rows() -> list:
	return [one for one in fleet.rows() if one.server and one.pilot_host]


def _tenants(server: str) -> list:
	names = frappe.get_all("Tenant", filters={"server": server, "site": ["is", "set"], "status": ["not in", GONE]}, pluck="name")
	return [frappe.get_doc("Tenant", one) for one in names]


def check() -> dict:
	"""Hourly, and when the release workflow says one is up, on the admin
	site: a release the servers do not have yet is put on each, unless one is
	still being prepared. A full box first drops the versions nobody is on,
	and takes the release at the next check. Then the Private App records
	become the private apps the release declares."""
	if not site.is_admin() or not _rows() or not frappe.conf.get(servers.KEYS):
		return {}
	keys = frappe.parse_json(frappe.conf.get(servers.KEYS))
	latest = boxes.latest_release(keys)
	started = []
	for row in _rows():
		rows = servers.benches(row)
		if any(one.get("release") == latest for one in rows):
			continue
		if len(rows) >= MOST_BENCHES:
			_drop_the_empty(row)
			continue
		servers.prepare(row, latest)
		started.append(row.server)
	return {"release": latest, "started": started, "private": private.register(boxes.release_of(keys, latest).get("private_apps"))}


def fresh(at, now: float) -> bool:
	"""Whether a signed call was made in the last `FRESH_FOR` seconds. Pure."""
	return isinstance(at, int | float) and abs(now - at) <= FRESH_FOR


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=3600)
def released() -> dict:
	"""The release workflow says a release is in the registry. Believed only
	when signed with the secret it shares with this site; what is built is
	still what the registry holds, so a repeated call starts nothing new."""
	site.require_admin()
	body = frappe.request.get_data(as_text=True)
	secret = frappe.conf.get(RELEASE_SECRET) or ""
	if not secret or not hmac.compare_digest(servers.signed(secret, body), frappe.get_request_header("X-One-Release") or ""):
		raise frappe.PermissionError
	if not fresh(json.loads(body).get("at"), time.time()):
		raise frappe.PermissionError
	frappe.enqueue("onedesk.one_admin.releases.check", queue="long", job_id="one_admin_release_check", deduplicate=True)
	return {"ok": True}


def heard(server: str, said: dict) -> None:
	"""A box reports. What happens next depends on what it was told to do."""
	row = servers.row_of(server)
	kind = said.get("kind")
	if str(kind).startswith("session-"):
		from onedesk.one_admin import sessions

		sessions.heard(said)
		return
	if kind == "spare":
		from onedesk.one_admin import spares

		spares.heard(server, said)
		return
	if not said.get("ok"):
		frappe.log_error(title=f"{kind} failed on {server}", message=str(said.get("error")))
		if kind == "prepare":
			servers._save(row, [one for one in servers.benches(row) if one["bench"] != said.get("bench")])
		if kind == "move":
			_moved(frappe.db.get_value("Tenant", {"site": said["site"]}), None)
		return
	if kind == "prepare":
		_built(row, said["bench"])
	elif kind == "move":
		_moved(frappe.db.get_value("Tenant", {"site": said["site"]}), said["to"])
		_drop_the_empty(row)
	elif kind == "drop-bench":
		servers.bench_dropped(row, said["bench"])


def _built(row, bench: str) -> None:
	"""The bench is ready: new workspaces go on it, everybody on the old one
	gets a window, and our own workspace moves at once."""
	rows = [{**one, "state": "ready"} if one["bench"] == bench else one for one in servers.benches(row)]
	servers._save(row, rows)
	for tenant in _tenants(row.server):
		if tenant.bench == bench:
			continue
		tenant.db_set({"update_at": window_for(tenant), "update_moving": 0})
		if tenant.is_house:
			update_now(tenant)


def _moved(tenant: str, bench: str | None) -> None:
	"""A move ended. `None` is a failed one: the workspace is still where it
	was, and tries again at its next window."""
	doc = frappe.get_doc("Tenant", tenant)
	if bench:
		doc.db_set({"bench": bench, "update_at": None, "update_moving": 0})
		frappe.enqueue("onedesk.one_admin.releases.wake", site=doc.site, enqueue_after_commit=True)
	else:
		doc.db_set({"update_at": window_for(doc), "update_moving": 0})


def wake(site: str) -> None:
	"""A moved workspace asks again who it is, so its bar stops saying an
	update is coming."""
	import requests

	try:
		requests.post(f"https://{site}/api/method/onedesk.one.account.wake", timeout=30)
	except requests.RequestException:
		frappe.log_error(title=f"Waking {site} after its update")


def _drop_the_empty(row) -> None:
	rows = servers.benches(row)
	used = {one.bench for one in _tenants(row.server)} | set(frappe.get_all("Workspace Session", filters={"server": row.server, "status": ["!=", "Deleted"]}, pluck="bench"))
	newest = servers.newest_ready(rows)
	for one in rows:
		if one["bench"] != newest and one["bench"] not in used and one.get("state") == "ready":
			servers.instruct(row.server, "drop-bench", bench=one["bench"])
			servers._save(row, [{**other, "state": "dropping"} if other["bench"] == one["bench"] else other for other in rows])


def tick() -> None:
	"""Every 15 minutes, on the admin site: each workspace whose window has
	come moves, or is reminded if it is waiting on the terms."""
	if not site.is_admin():
		return
	now = now_datetime()
	for name in frappe.get_all("Tenant", filters=[["update_at", "is", "set"], ["update_at", "<=", now], ["update_moving", "=", 0], ["site", "is", "set"], ["status", "not in", GONE]], pluck="name"):
		try:
			_due(frappe.get_doc("Tenant", name), now)
		except Exception:
			frappe.log_error(title=f"Moving {name}")


def _due(tenant, now: datetime) -> None:
	row = servers.row_of(tenant.server)
	to = servers.current(row)
	if tenant.bench == to:
		tenant.db_set("update_at", None)
		return
	if not may_move(bool(tenant.terms_pending), get_datetime(tenant.update_at), now):
		if not tenant.terms_reminded_on or getdate(tenant.terms_reminded_on) <= getdate(add_days(today(), -REMIND_EVERY)):
			from onedesk.one_admin import tell

			tell.update_waits(tenant)
			tenant.db_set("terms_reminded_on", today())
		return
	tenant.db_set("update_moving", 1)
	servers.instruct(tenant.server, "move", site=tenant.site, **{"from": tenant.bench, "to": to}, quiet=tenant.status == "Suspended")


def update_now(tenant) -> dict:
	"""The workspace's box is told to move it now, if a newer bench is ready."""
	row = servers.row_of(tenant.server)
	if tenant.bench == servers.current(row):
		return {"waiting": False}
	if not tenant.update_moving:
		now = now_datetime()
		tenant.db_set("update_at", now)
		_due(tenant, now)
	return {"waiting": True}


def upcoming(tenant) -> dict:
	"""What a workspace is told: when its next update is, and its window."""
	at, weekday, hour = frappe.db.get_value("Tenant", tenant, ["update_at", "update_weekday", "update_hour"])
	return {"at": str(at) if at else None, "weekday": weekday, "hour": hour}
