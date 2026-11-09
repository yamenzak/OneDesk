"""The socket that wakes a screen. A screen still asks for its state; the
socket only tells it to ask now, so nothing a screen shows ever arrives by
the socket alone, and a screen whose socket drops just asks more often.

realtime/handlers.js admits a screen by its token into two rooms: its own,
for a command meant for it, and every screen's, for anything a channel
shows. A change publishes `onedesk_display_wake` to one of them after its
transaction commits."""

from typing import Annotated

import frappe
from frappe.rate_limiter import rate_limit

EVENT = "onedesk_display_wake"
ROOM = "onedesk:display/{}"
EVERY = "all"

@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60)
def admit(
	screen: Annotated[str, "The screen."], token: Annotated[str, "Its token."]
) -> dict:
	"""Asked by the socket server when a screen joins: the rooms it may hear."""
	from onedesk.one_display import screens

	if not screens._screen(screen, token):
		return {"ok": False}
	return {"ok": True, "rooms": [ROOM.format(EVERY), ROOM.format(screen)]}


def wake(screen: str | None = None) -> None:
	"""Tell one screen, or every screen, to ask for its state now, and what
	they would be told built again."""
	from onedesk.one_display import programme

	frappe.db.after_commit.add(programme.forget)
	frappe.publish_realtime(EVENT, {}, room=ROOM.format(screen or EVERY), after_commit=True)


def changed(doc, method=None) -> None:
	"""doc_events: a screen hears of a change to itself, every screen of a
	change to what any channel shows."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	if doc.doctype == "Display Source":
		frappe.cache.delete_value(READ)
	wake(doc.name if doc.doctype == "Display Screen" else None)


# the record types some Display Source reads, so a save elsewhere costs one look
READ = "one_display:read_doctypes"


def _read_doctypes() -> dict:
	held = frappe.cache.get_value(READ)
	if held is None:
		held = {}
		for one in frappe.get_all("Display Source", filters={"kind": ["in", ["Records", "Record", "Report"]]}, fields=["name", "kind", "ref_doctype", "report"]):
			doctype = frappe.db.get_value("Report", one.report, "ref_doctype") if one.kind == "Report" and one.report else one.ref_doctype
			if doctype:
				held.setdefault(doctype, []).append(one.name)
		frappe.cache.set_value(READ, held)
	return held


def record_saved(doc, method=None) -> None:
	"""doc_events "*": a record some source reads was saved or deleted, so
	those sources read again and every screen asks now, as it does for a call.
	One wake a request, however many records it saves."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch or frappe.flags.in_import:
		return
	reading = _read_doctypes().get(doc.doctype)
	if not reading:
		return
	from onedesk.one_display import sources

	for name in reading:
		sources.forget(name)
	if not frappe.flags.one_display_woken:
		frappe.flags.one_display_woken = True
		wake()
