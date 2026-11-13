"""Finished, empty sites waiting on each server, so a signup takes seconds.

A spare is made with its scheduler paused and renamed to the workspace's
address when claimed (steps.create_site): restored from the release's
template by the box's agent, or installed by Pilot on a bench without one.
Nothing is shared between spares. AGENTS.md, Servers.
"""

import secrets
import time

import frappe

from onedesk.one_admin import faults, fleet, hosts, pilot, quota, servers, site

KEEP = 2
WAITING = "one_admin_spare_failed"
AFTER_A_FAILURE = 3600
AGENT_LASTS = 1800
KIND = "spare"
LOGS = ("Error Log", "Scheduled Job Log", "Activity Log", "Access Log", "Route History", "Email Queue", "Calendar Feed")


def _rows() -> list:
	return [one for one in fleet.rows() if one.open and one.pilot_host]


def held(row) -> list[dict]:
	"""A server's spares: `task` while Pilot is still building one, `asked`
	while the box's agent is."""
	return frappe.parse_json(row.spares or "[]") or []


def _save(row, spares: list[dict]) -> None:
	frappe.db.set_value("Workspace Server", row.name, "spares", frappe.as_json(spares))


def building(one: dict) -> bool:
	"""Pure."""
	return bool(one.get("task") or one.get("asked"))


def wants_one(tenants: int, spares: list[dict], capacity: int) -> bool:
	"""Whether to start another spare: none being built, fewer than `KEEP`,
	and room under the limit. Pure."""
	if any(building(one) for one in spares) or len(spares) >= KEEP:
		return False
	return not capacity or tenants + len(spares) < capacity


def overdue(one: dict, now: float) -> bool:
	"""An agent's spare that has not been reported in `AGENT_LASTS`. Pure."""
	return bool(one.get("asked")) and now - (one.get("at") or 0) > AGENT_LASTS


def keep() -> None:
	"""The cron entry, on the admin site only: each server's spares finished
	and topped up. One server's trouble leaves the rest alone."""
	if not site.is_admin():
		return
	counts = quota.held_on_servers()
	for row in _rows():
		try:
			_tend(row, counts.get(row.server, 0))
		except faults.Refused:
			frappe.log_error(title=f"Spares on {row.server}")


def _drop(row, one: dict) -> None:
	"""What an agent left of a spare it did not finish, if anything."""
	try:
		pilot.call(row.server, "DELETE", f"/sites/{one['site']}", key=f"drop:{one['site']}", bench=one.get("bench"))
	except faults.Refused:
		pass


def _failed(row) -> None:
	frappe.cache().set_value(f"{WAITING}:{row.server}", 1, expires_in_sec=AFTER_A_FAILURE)
	frappe.log_error(title=f"A spare failed on {row.server}")


def _tend(row, tenants: int) -> None:
	now = servers.current(row)
	spares = []
	for one in held(row):
		bench = one.get("bench")
		if bench and bench != now:
			pilot.call(row.server, "DELETE", f"/sites/{one['site']}", key=f"drop:{one['site']}", bench=bench)
			continue
		if overdue(one, time.time()):
			_drop(row, one)
			_failed(row)
			continue
		spares.append(one)
		if not one.get("task"):
			continue
		try:
			if pilot.task(row.server, one["task"], bench=now) == "done":
				pilot.call(row.server, "PATCH", f"/sites/{one['site']}/configuration", bench=now, json={"pause_scheduler": 1})
				one.pop("task")
		except faults.Again:
			raise
		except faults.Refused:
			spares.remove(one)
			_failed(row)
	if wants_one(tenants, spares, row.capacity) and not frappe.cache().get_value(f"{WAITING}:{row.server}"):
		spares.append(_start(row, now))
	_save(row, spares)


def _start(row, bench: str) -> dict:
	from onedesk.one_admin.steps import APPS, _tenant_domain

	name = hosts.under(f"spare-{secrets.token_hex(4)}", _tenant_domain())
	made = next((one for one in servers.benches(row) if one["bench"] == bench), {})
	if made.get("template") and made.get("release"):
		asked = servers.instruct(row.server, KIND, bench=bench, site=name, release=made["release"])
		return {"site": name, "bench": bench, "asked": asked, "at": int(time.time())}
	answered = pilot.call(row.server, "POST", "/sites", key=name, bench=bench, json={"name": name, "apps": ["frappe", *APPS]})
	return {"site": name, "bench": bench, "task": (answered or {}).get("task_id")}


def heard(server: str, said: dict) -> None:
	"""The box's agent says how a spare went: ready, or gone from the list."""
	row = next((one for one in _rows() if one.server == server), None)
	if not row:
		return
	spares = held(row)
	if said.get("ok"):
		_save(row, [{key: value for key, value in one.items() if key not in ("asked", "at")} if one["site"] == said.get("site") else one for one in spares])
		return
	_save(row, [one for one in spares if one["site"] != said.get("site")])
	_drop(row, said)
	_failed(row)


def ready(server: str) -> str | None:
	"""A finished spare on this server, or None. Left in the list until
	`used` says the rename was asked for, so a retry finds the same one."""
	row = next((one for one in _rows() if one.server == server), None)
	found = next((one for one in held(row) if not building(one) and one.get("bench") in (None, servers.current(row))), None) if row else None
	return found["site"] if found else None


def used(server: str, name: str) -> None:
	row = next(one for one in _rows() if one.server == server)
	_save(row, [one for one in held(row) if one["site"] != name])


def as_template() -> None:
	"""Run once by the release build on its template site, before it is
	copied: what must be a site's own taken out. Every encrypted value (its
	key is not kept), the Administrator's password, sessions, API keys,
	calendar links and logs. A spare made from it is given its own. The
	bench carries every private app, but a template holding one would give
	it to every workspace, so the build stops there."""
	from onedesk.account_center import private

	if private.names():
		raise SystemExit(f"the template site has private apps installed ({', '.join(private.names())}); a workspace gets one only by claiming it")
	frappe.db.sql("delete from `__Auth` where encrypted = 1 or (doctype = 'User' and fieldname = 'password')")
	frappe.db.sql("delete from `tabSessions`")
	frappe.db.sql("update `tabUser` set api_key = null")
	from frappe.utils.logging import connection_for, is_log_doctype

	for doctype in LOGS:
		if is_log_doctype(doctype) or frappe.db.table_exists(doctype):
			connection_for(doctype).delete(doctype)
	frappe.db.commit()
