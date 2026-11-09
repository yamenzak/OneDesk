"""Finished, empty sites waiting on each server, so a signup takes seconds.

A spare is built in the background with its scheduler paused, and renamed to
the workspace's address when one is claimed (steps.create_site). Pilot gives
each its own random administrator password and encryption key, so nothing is
shared between them. A spare counts towards a server's limit. README, Servers.
"""

import secrets

import frappe

from onedesk.one_admin import faults, hosts, pilot, quota, site

KEEP = 2


def _rows() -> list:
	return [one for one in frappe.get_cached_doc("One Admin Settings").get("servers") or [] if one.open and one.pilot_host]


def held(row) -> list[dict]:
	"""A server's spares: `task` while it is still being built."""
	return frappe.parse_json(row.spares or "[]") or []


def _save(row, spares: list[dict]) -> None:
	frappe.db.set_value("Workspace Server", row.name, "spares", frappe.as_json(spares))
	frappe.clear_document_cache("One Admin Settings", "One Admin Settings")


def wants_one(tenants: int, spares: list[dict], capacity: int) -> bool:
	"""Whether to start another spare: none being built, fewer than `KEEP`,
	and room under the limit. Pure."""
	if any(one.get("task") for one in spares) or len(spares) >= KEEP:
		return False
	return not capacity or tenants + len(spares) < capacity


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


def _tend(row, tenants: int) -> None:
	spares = held(row)
	for one in list(spares):
		if not one.get("task"):
			continue
		try:
			if pilot.task(row.server, one["task"]) == "done":
				pilot.call(row.server, "PATCH", f"/sites/{one['site']}/configuration", json={"pause_scheduler": 1})
				one.pop("task")
		except faults.Again:
			raise
		except faults.Refused:
			spares.remove(one)
			frappe.log_error(title=f"A spare failed on {row.server}")
	if wants_one(tenants, spares, row.capacity):
		from onedesk.one_admin.steps import APPS, _tenant_domain

		name = hosts.under(f"spare-{secrets.token_hex(4)}", _tenant_domain())
		answered = pilot.call(row.server, "POST", "/sites", key=name, json={"name": name, "apps": ["frappe", *APPS]})
		spares.append({"site": name, "task": (answered or {}).get("task_id")})
	_save(row, spares)


def ready(server: str) -> str | None:
	"""A finished spare on this server, or None. Left in the list until
	`used` says the rename was asked for, so a retry finds the same one."""
	row = next((one for one in _rows() if one.server == server), None)
	found = next((one for one in held(row) if not one.get("task")), None) if row else None
	return found["site"] if found else None


def used(server: str, name: str) -> None:
	row = next(one for one in _rows() if one.server == server)
	_save(row, [one for one in held(row) if one["site"] != name])
