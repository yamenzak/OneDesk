"""Updates in one quiet window for everyone: Saturday 01:00 to 03:00 UTC.
An update Frappe Cloud has waiting is set for the first window at least
`NOTICE_HOURS` away, every workspace is told when (`hello`), and in the
window the bench group is deployed with each app at the commit the gates
passed: OneDesk's `main` as Frappe Cloud has it, frappe, erpnext and hrms at
the commits upstream.json pins. A pinned commit Frappe Cloud does not offer
holds the update and tells the operators (README, Updates)."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import frappe
from frappe.utils import get_datetime, now_datetime

from onedesk.one_admin import faults, press, site

WEEKDAY = 5
HOUR = 1
NOTICE_HOURS = 72
PINNED = ("frappe", "erpnext", "hrms")
UPSTREAM = Path(__file__).resolve().parents[2] / "upstream.json"


def window_after(moment: datetime, notice_hours: int = NOTICE_HOURS) -> datetime:
	"""The first Saturday 01:00 UTC at least `notice_hours` after `moment`.
	Pure."""
	earliest = moment + timedelta(hours=notice_hours)
	day = earliest.replace(hour=HOUR, minute=0, second=0, microsecond=0)
	day += timedelta(days=(WEEKDAY - day.weekday()) % 7)
	return day if day >= earliest else day + timedelta(days=7)


def pins() -> dict:
	"""The commit each pinned app runs on, from upstream.json."""
	held = json.loads(UPSTREAM.read_text())
	return {app: held[app]["sha"] for app in PINNED if app in held}


def chosen(apps: list[dict], pinned: dict) -> tuple[list[dict], list[str]]:
	"""Each app's release to deploy, and the apps whose pinned commit Frappe
	Cloud does not offer. An app already on its target is left out. Pure."""
	out, missing = [], []
	for app in apps:
		name = app.get("app") or app.get("name")
		releases = app.get("releases") or []
		if name in pinned:
			if (app.get("current_hash") or "").startswith(pinned[name]):
				continue
			found = next((one for one in releases if (one.get("hash") or "").startswith(pinned[name])), None)
			if not found:
				missing.append(name)
				continue
		else:
			if not app.get("update_available"):
				continue
			found = next((one for one in releases if one.get("name") == app.get("next_release")), None)
			if not found:
				continue
		out.append({"app": name, "source": found.get("source") or app.get("source"), "release": found["name"], "hash": found.get("hash")})
	return out, missing


def _bench() -> str | None:
	return frappe.db.get_single_value("One Admin Settings", "press_bench")


def check() -> dict:
	"""Hourly, on the admin site: an update waiting is set for its window,
	once, and the operators told; none waiting clears it."""
	if not site.is_admin() or not _bench():
		return {}
	info = press.call("press.api.bench.deploy_information", name=_bench()) or {}
	apps, missing = chosen(info.get("apps") or [], pins())
	settings = frappe.get_single("One Admin Settings")
	if info.get("deploy_in_progress"):
		return {"running": True}
	if settings.release_running:
		settings.db_set("release_running", None)
	if not apps:
		if settings.release_at and not settings.release_running:
			settings.db_set({"release_at": None, "release_apps": None})
		return {"waiting": False, "missing": missing}
	if not settings.release_at:
		at = window_after(now_datetime())
		settings.db_set({"release_at": at, "release_apps": json.dumps(apps)})
		from onedesk.one_admin import tell

		tell.release_set(at, [one["app"] for one in apps], missing)
	else:
		settings.db_set("release_apps", json.dumps(apps))
	return {"at": str(settings.release_at), "apps": apps, "missing": missing}


def window() -> dict:
	"""Scheduled for Saturday 01:00 UTC: the update set for now deployed,
	every site on the bench group updated."""
	if not site.is_admin() or not _bench():
		return {}
	settings = frappe.get_single("One Admin Settings")
	if not settings.release_at or get_datetime(settings.release_at) > now_datetime() + timedelta(minutes=30):
		return {"due": False}
	info = press.call("press.api.bench.deploy_information", name=_bench()) or {}
	apps, missing = chosen(info.get("apps") or [], pins())
	if missing:
		from onedesk.one_admin import tell

		tell.release_held(missing)
		settings.db_set("release_at", window_after(now_datetime()))
		return {"held": missing}
	if not apps:
		settings.db_set({"release_at": None, "release_apps": None})
		return {"nothing": True}
	sites = [one["name"] for one in info.get("sites") or []]
	try:
		started = press.call("press.api.bench.deploy_and_update", name=_bench(), apps=apps, sites=sites)
	except faults.Refused:
		settings.db_set("release_at", window_after(now_datetime()))
		raise
	settings.db_set({"release_at": None, "release_apps": None, "release_running": str(started or "")})
	return {"started": started, "apps": apps, "sites": len(sites)}


def upcoming() -> dict | None:
	"""What a workspace is told: when the next update is, if one is set."""
	at = frappe.db.get_single_value("One Admin Settings", "release_at")
	return {"at": str(at)} if at else None
