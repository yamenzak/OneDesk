"""Updates in one quiet window for everyone: Saturday 01:00 to 03:00 UTC.
A server behind on OneDesk's `main` is set for the first window at least
`NOTICE_HOURS` away, every workspace is told when (`hello`), and in the
window each server moves to it through Pilot, which backs up first and
restores if the update fails. README, Updates."""

from datetime import datetime, timedelta

import frappe
from frappe.utils import get_datetime, now_datetime

from onedesk.one_admin import pilot, site

WEEKDAY = 5
HOUR = 1
NOTICE_HOURS = 72
APP = "onedesk"


def window_after(moment: datetime, notice_hours: int = NOTICE_HOURS) -> datetime:
	"""The first Saturday 01:00 UTC at least `notice_hours` after `moment`.
	Pure."""
	earliest = moment + timedelta(hours=notice_hours)
	day = earliest.replace(hour=HOUR, minute=0, second=0, microsecond=0)
	day += timedelta(days=(WEEKDAY - day.weekday()) % 7)
	return day if day >= earliest else day + timedelta(days=7)


def _servers() -> list[str]:
	return [one.server for one in frappe.get_cached_doc("One Admin Settings").get("servers") or [] if one.server and one.pilot_host]


def behind(answer: dict | None) -> bool:
	"""Whether Pilot's list of apps says OneDesk has commits waiting. Pure."""
	return any(one.get("name") == APP and one.get("commits_behind") for one in (answer or {}).get("apps") or [])


def _waiting() -> list[str]:
	return [one for one in _servers() if behind(pilot.call(one, "POST", "/app-update-checks"))]


def check() -> dict:
	"""Hourly, on the admin site: an update waiting is set for its window,
	once, and the operators told; none waiting clears it."""
	if not site.is_admin() or not _servers():
		return {}
	waiting = _waiting()
	settings = frappe.get_single("One Admin Settings")
	if not waiting:
		if settings.release_at:
			settings.db_set("release_at", None)
		return {"waiting": False}
	if not settings.release_at:
		at = window_after(now_datetime())
		settings.db_set("release_at", at)
		from onedesk.one_admin import tell

		tell.release_set(at, [APP])
	return {"at": str(settings.release_at), "servers": waiting}


def _a_site_on(server: str) -> str | None:
	return frappe.db.get_value("Tenant", {"server": server, "site": ["is", "set"], "status": ["not in", ("Archived", "Dropped")]}, "site")


def window() -> dict:
	"""Scheduled for Saturday 01:00 UTC: each server behind is updated, every
	site on it with it."""
	if not site.is_admin() or not _servers():
		return {}
	settings = frappe.get_single("One Admin Settings")
	if not settings.release_at or get_datetime(settings.release_at) > now_datetime() + timedelta(minutes=30):
		return {"due": False}
	started = {}
	for server in _waiting():
		one = _a_site_on(server)
		if one:
			started[server] = pilot.call(server, "POST", f"/sites/{one}/actions/update-apps", key=f"{settings.release_at}:{server}", json={"apps": [APP]})
	settings.db_set("release_at", None)
	return {"started": list(started)}


def upcoming() -> dict | None:
	"""What a workspace is told: when the next update is, if one is set."""
	at = frappe.db.get_single_value("One Admin Settings", "release_at")
	return {"at": str(at)} if at else None
