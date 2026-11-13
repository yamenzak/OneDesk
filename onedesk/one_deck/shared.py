"""A presentation through a OneCloud link (AGENTS.md, Shared by link).

The guest page (www/s.py) draws the slides with play.js, filled as whoever
shared the link, so a guest never reaches the records. Present Live keeps the
presenter's slide in the cache and tells a socket room (realtime/handlers.js
admits a guest by the link's gates); a guest page that has no socket asks
`where`. Every look is a Presentation View the presenter reads as Views.
"""

import hashlib
import hmac
import json
import secrets
import time
from typing import Annotated

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, now_datetime
from werkzeug.exceptions import NotFound

from onedesk.one_deck import api

EVENT = "onedesk_slide_at"
ROOM = "onedesk:slide/{}"
LIVE_FOR = 6 * 3600
VIEW = "Presentation View"
MOST_SECONDS = 4 * 3600


def _key(name: str) -> str:
	return f"one_deck_live:{name}"


def live(name: str) -> dict | None:
	"""Where a presentation being presented live is, or None."""
	return frappe.cache.get_value(_key(name)) or None


def opened(token: str, item: str | None = None) -> tuple:
	"""The link and the presentation it opens for this guest, or NotFound."""
	from onedesk.one_cloud import links

	link = links.live(token)
	if not link or links.opened_as(link) is None:
		raise NotFound
	found = links._within(link, item)
	name = api.presentation_of(found.file_url)
	if not name:
		raise NotFound
	return link, name


def _signed(said: str) -> str:
	from frappe.utils.password import get_encryption_key

	return hmac.new(get_encryption_key().encode(), f"one_slide_live:{said}".encode(), hashlib.sha256).hexdigest()[:32]


def ticket(link, name: str) -> str:
	"""What a guest page that passed the link's gates hands the socket server,
	which carries only the session's cookie, not the link's: the link and
	presentation, sealed, for as long as a live presentation lasts."""
	until = int(time.time()) + LIVE_FOR
	return f"{until}.{_signed(f'{link.name}:{name}:{until}')}"


def _ticket_holds(link, name: str, said: str | None) -> bool:
	until, _dot, seal = str(said or "").partition(".")
	if not until.isdigit() or int(until) < time.time():
		return False
	return hmac.compare_digest(seal, _signed(f"{link.name}:{name}:{until}"))


def page(link, item, name: str) -> dict:
	"""What the guest page draws: every slide, filled as the person who
	shared it, and whether it is being presented live."""
	from onedesk.one_deck import play

	return {
		"title": item.file_name,
		"slides": play.for_screen(name, 10, reader=link.owner),
		"live": live(name),
		"session": secrets.token_hex(8),
		"ticket": ticket(link, name),
		"download": bool(link.allow_download),
	}


@frappe.whitelist(methods=["POST"])
def present_live(
	name: Annotated[str, "The presentation."], slide: Annotated[int, "The slide shown, from 0."] = 0
) -> dict:
	"""Show everyone on the presentation's links this slide, now."""
	api._may(name, "write")
	said = {"slide": max(0, cint(slide)), "by": frappe.session.user}
	frappe.cache.set_value(_key(name), said, expires_in_sec=LIVE_FOR)
	frappe.publish_realtime(EVENT, {"live": True, "slide": said["slide"]}, room=ROOM.format(name), after_commit=True)
	return said


@frappe.whitelist(methods=["POST"])
def stop_live(name: Annotated[str, "The presentation."]) -> None:
	"""Stop presenting live: guests go on at their own pace."""
	api._may(name, "write")
	frappe.cache.delete_value(_key(name))
	frappe.publish_realtime(EVENT, {"live": False}, room=ROOM.format(name), after_commit=True)


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=240, seconds=60)
def where(token: str, item: str | None = None) -> dict:
	"""For a guest page without a socket: where the live presentation is."""
	_link, name = opened(token, item)
	said = live(name)
	return {"live": bool(said), "slide": (said or {}).get("slide", 0)}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=120, seconds=60)
def admit(token: str, item: str | None = None, ticket: str | None = None) -> dict:
	"""Asked by the socket server when a guest page joins: its room, if the
	page's ticket says it passed the link's gates."""
	from onedesk.one_cloud import links

	link = links.live(token)
	if not link:
		return {"ok": False}
	try:
		name = api.presentation_of(links._within(link, item or None).file_url)
	except NotFound:
		return {"ok": False}
	if not name or not _ticket_holds(link, name, ticket):
		return {"ok": False}
	return {"ok": True, "rooms": [ROOM.format(name)]}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=120, seconds=60)
def viewed(token: str, session: str, seconds: str | dict, item: str | None = None) -> None:
	"""How long each slide has been on a guest's screen in this look, so
	far: one row per look, kept up to date as they go."""
	from onedesk.one_cloud import links

	link, name = opened(token, item)
	said = frappe.parse_json(seconds) if isinstance(seconds, str) else seconds
	kept = {str(cint(at)): min(cint(value), MOST_SECONDS) for at, value in (said or {}).items() if cint(value) > 0}
	session = str(session or "")[:32]
	if not session:
		return
	row = frappe.db.get_value(VIEW, {"session": session, "presentation": name}, "name")
	values = {"seconds": json.dumps(kept), "total": min(sum(kept.values()), MOST_SECONDS), "last_seen": now_datetime()}
	if row:
		frappe.db.set_value(VIEW, row, values, update_modified=False)
		return
	who = links.opened_as(link)
	frappe.get_doc(
		{"doctype": VIEW, "presentation": name, "cloud_link": link.name, "viewer": who if who and "@" in who else "", "session": session, "opened_on": now_datetime(), **values}
	).insert(ignore_permissions=True)


@frappe.whitelist()
@frappe.read_only()
def views(name: Annotated[str, "The presentation."]) -> dict:
	"""Who looked at the presentation through its links, when and for how
	long, and how long each slide held them, added up."""
	api._may(name, "write")
	rows = frappe.get_all(VIEW, filters={"presentation": name}, fields=["viewer", "opened_on", "total", "seconds"], order_by="opened_on desc", limit=200)
	slides = {}
	for row in rows:
		for at, value in json.loads(row.seconds or "{}").items():
			slides[int(at)] = slides.get(int(at), 0) + cint(value)
	return {
		"looks": [{"viewer": row.viewer or _("Anyone with the link"), "opened_on": row.opened_on, "total": row.total} for row in rows],
		"slides": [{"number": at + 1, "seconds": slides[at]} for at in sorted(slides)],
		"live": live(name),
	}


def forget(name: str) -> None:
	"""The views of a presentation that is gone."""
	frappe.db.delete(VIEW, {"presentation": name})
	frappe.cache.delete_value(_key(name))
