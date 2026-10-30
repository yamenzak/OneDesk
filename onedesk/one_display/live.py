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
	"""Tell one screen, or every screen, to ask for its state now."""
	frappe.publish_realtime(EVENT, {}, room=ROOM.format(screen or EVERY), after_commit=True)


def changed(doc, method=None) -> None:
	"""doc_events: a screen hears of a change to itself, every screen of a
	change to what any channel shows."""
	if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
		return
	wake(doc.name if doc.doctype == "Display Screen" else None)
