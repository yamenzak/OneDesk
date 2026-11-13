"""UpdateCenter's This Workspace: when One next updates this workspace and
the day and hour it updates in, as OneAdmin last said (Workspace Account,
written by one/account.py from proxy.hello), changed and hurried through
OneAdmin (one_admin/proxy.py update_window and update_now)."""

import frappe
from frappe import _
from frappe.utils import cint, get_system_timezone

ACCOUNT = "Workspace Account"
FIELDS = ("update_at", "update_weekday", "update_hour", "update_moving", "update_held_until")
WEEKDAY = 5
HOUR = 1


def held_until() -> str | None:
	"""The day the waiting update goes ahead even though the organisation
	has not agreed to the new terms yet, while it waits for them."""
	value = frappe.db.get_single_value(ACCOUNT, "update_held_until")
	return str(value) if value else None


def plainly(said: dict) -> dict:
	"""The account's fields as UpdateCenter reads them: the window falls
	back to OneAdmin's own (Saturday, 01:00) until it has said one. Pure."""
	weekday = said.get("update_weekday")
	hour = said.get("update_hour")
	return {
		"at": str(said["update_at"]) if said.get("update_at") else None,
		"weekday": WEEKDAY if weekday is None else cint(weekday),
		"hour": HOUR if hour is None else cint(hour),
		"moving": cint(said.get("update_moving")),
		"held_until": str(said["update_held_until"]) if said.get("update_held_until") else None,
	}


@frappe.whitelist(methods=["GET"])
def state() -> dict:
	"""What UpdateCenter shows everybody: the next update, if one waits, and
	the window; whether this workspace has an account to ask, and whether
	the reader may change the window or update now."""
	from onedesk.one import account, roles

	said = {field: frappe.db.get_single_value(ACCOUNT, field) for field in FIELDS}
	return {**plainly(said), "linked": account.configured(), "may": roles.administers(), "zone": get_system_timezone()}


@frappe.whitelist(methods=["POST"])
def set_window(weekday: int, hour: int) -> dict:
	"""The day and hour the workspace updates, in its own time zone."""
	from onedesk.one import account, roles

	roles.require()
	if not 0 <= cint(weekday) <= 6 or not 0 <= cint(hour) <= 23:
		frappe.throw(_("That is not a day and hour."))
	account.ask("onedesk.one_admin.proxy.update_window", weekday=cint(weekday), hour=cint(hour))
	account.refresh()
	return state()


@frappe.whitelist(methods=["POST"])
def update_now() -> dict:
	"""The workspace moves to the waiting release straight away; `waiting`
	is false when there is none, and nothing happens."""
	from onedesk.one import account, roles

	roles.require()
	said = account.ask("onedesk.one_admin.proxy.update_now") or {}
	account.refresh()
	return {**state(), "waiting": int(bool(said.get("waiting")))}
