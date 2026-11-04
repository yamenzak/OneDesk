"""What OneDisplay tells people, and when (its kinds are in notifications.py)."""

import frappe
from frappe.utils import add_to_date, format_datetime, now_datetime, today

from onedesk.one import notify, rights

SILENT = 10
TOLD = "one_display:offline:{}"


def offline() -> None:
	"""Every five minutes: a paired screen that stopped asking, and was not
	turned off from here, is told to whoever runs OneDisplay once for each
	time it went quiet. Which quiet was told is kept on the screen
	(offline_told), not in the cache, which a deploy clears. A screen never
	heard from has not gone quiet: frappe reads an empty date as the
	earliest day, so `<` alone told it every time."""
	since = add_to_date(now_datetime(), minutes=-SILENT)
	screens = frappe.get_all(
		"Display Screen",
		filters=[["status", "=", "Paired"], ["dark", "=", 0], ["last_seen", "is", "set"], ["last_seen", "<", since]],
		fields=["name", "screen_name", "last_seen", "offline_told"],
	)
	if not screens:
		return
	people = _runners()
	for screen in screens:
		if screen.offline_told == screen.last_seen:
			continue
		frappe.db.set_value("Display Screen", screen.name, "offline_told", screen.last_seen, update_modified=False)
		notify.notify(
			"Screen Offline",
			people,
			record=("Display Screen", screen.name),
			screen=screen.screen_name or screen.name,
			when=format_datetime(screen.last_seen, "d MMM, HH:mm"),
		)


def long_waits() -> None:
	"""Every two minutes: a ticket waiting longer than its queue allows is
	told once to whoever staffs the queue's counters, or to whoever runs
	OneDisplay if nobody does."""
	for queue in frappe.get_all("Queue", filters={"wait_alert": [">", 0]}, fields=["name", "wait_alert"]):
		since = add_to_date(now_datetime(), minutes=-queue.wait_alert)
		tickets = frappe.get_all(
			"Queue Ticket",
			filters={"queue": queue.name, "ticket_date": today(), "status": "Waiting", "creation": ["<", since]},
			fields=["name", "ticket", "service", "creation"],
		)
		if not tickets:
			continue
		staff = [row.user for row in frappe.get_cached_doc("Queue", queue.name).counters if row.user] or _runners()
		for ticket in tickets:
			key = TOLD.format(f"wait:{ticket.name}")
			if frappe.cache.get_value(key):
				continue
			frappe.cache.set_value(key, 1, expires_in_sec=86400)
			notify.notify(
				"Long Wait",
				list(dict.fromkeys(staff)),
				record=("Queue Ticket", ticket.name),
				link="/desk/counter",
				ticket=ticket.ticket,
				minutes=int((now_datetime() - ticket.creation).total_seconds() // 60),
				service=ticket.service,
				queue=queue.name,
			)


def past_limits() -> None:
	"""Every two minutes: an item kept on a board in a state past its limit
	is told once, to the board's people, or to whoever runs OneDisplay."""
	from onedesk.one_display import boards

	for doc, row, minutes in boards.overdue():
		people = [one.user for one in doc.people] or _runners()
		notify.notify(
			"Past Its Time",
			list(dict.fromkeys(people)),
			record=(boards.DOCTYPE, doc.name),
			link=f"/desk/boards?board={doc.name}",
			item=row.item_name,
			state=row.state,
			minutes=int(minutes),
			board=doc.board_name,
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


def made(asker: str, doctype: str, playlist: str, what: str, failed: bool = False) -> None:
	"""A song OneAI made in the background is in its playlist, or
	could not be made: whoever asked hears which. Sent as the workspace, since
	the bell does not tell a person of their own doing."""
	notify.notify(
		"Not Made by OneAI" if failed else "Made by OneAI",
		[asker],
		record=(doctype, playlist),
		sender="Administrator",
		what=what,
		playlist=playlist,
	)
