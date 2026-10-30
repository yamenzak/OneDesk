"""What OneDisplay tells people, and when (its kinds are in notifications.py)."""

import frappe
from frappe.utils import add_to_date, format_datetime, now_datetime

from onedesk.one import notify, rights

SILENT = 10
TOLD = "one_display:offline:{}"


def offline() -> None:
	"""Every five minutes: a paired screen that stopped asking, and was not
	turned off from here, is told to whoever runs OneDisplay once for each
	time it went quiet."""
	since = add_to_date(now_datetime(), minutes=-SILENT)
	screens = frappe.get_all(
		"Display Screen",
		filters={"status": "Paired", "dark": 0, "last_seen": ["<", since]},
		fields=["name", "screen_name", "last_seen"],
	)
	if not screens:
		return
	people = _runners()
	for screen in screens:
		key = TOLD.format(screen.name)
		if frappe.cache.get_value(key) == str(screen.last_seen):
			continue
		frappe.cache.set_value(key, str(screen.last_seen), expires_in_sec=7 * 86400)
		notify.notify(
			"Screen Offline",
			people,
			record=("Display Screen", screen.name),
			screen=screen.screen_name or screen.name,
			when=format_datetime(screen.last_seen, "d MMM, HH:mm"),
		)


def _runners() -> list[str]:
	"""Everybody turned on whose role may change a screen: who runs OneDisplay."""
	from frappe.permissions import get_doctype_roles

	held = set(get_doctype_roles("Display Screen", "write"))
	people = frappe.get_all(
		"Has Role",
		filters={"role": ["in", list(held) or [""]], "parenttype": "User", "parent": ["not in", ("Administrator", "Guest")]},
		pluck="parent",
		distinct=True,
	)
	return frappe.get_all("User", filters={"name": ["in", people or [""]], "enabled": 1}, pluck="name")


def alert_sent(message: str) -> None:
	"""An alert went up on every screen: the others who may send one hear it."""
	people = [user for user in rights.people_with("Display Settings", "display_alert") if user != frappe.session.user]
	notify.notify(
		"Emergency Alert Sent",
		people,
		link="/desk/display-screen",
		who=frappe.utils.get_fullname(frappe.session.user),
		message=message,
	)
