"""A phone as the presenter's remote (AGENTS.md, Notes and presenting).

A screen pairs a phone by a QR code carrying a token: the presenter view for
its signed-in presenter, or a page showing the presentation through a link
for whoever is in front of it. The phone and the screen meet in the token's
socket room (realtime/handlers.js); the first phone in keeps the remote.
"""

import hashlib
import hmac
import secrets
from typing import Annotated

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import get_datetime, get_url, now_datetime

from onedesk.one_deck import api

LIFE = 8 * 3600
ROOM = "onedesk:remote/{}"
KEY = (16, 64)


def _key(token: str) -> str:
	return f"one_deck_remote:{token}"


def paired(token: str | None) -> dict | None:
	"""What a token pairs, while it lasts."""
	if not token or len(token) > 64:
		return None
	return frappe.cache.get_value(_key(token)) or None


def room(token: str) -> str:
	return ROOM.format(hashlib.sha256(token.encode()).hexdigest()[:24])


def _same(said: str | None, kept: str | None) -> bool:
	return bool(said and kept) and hmac.compare_digest(str(said), str(kept))


def _pair(name: str, title: str, user: str | None = None, link: str | None = None) -> dict:
	"""A token for a phone, and a key of the screen's own that the phone never sees."""
	from onedesk.one import qr

	token, screen = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
	said = {"presentation": name, "title": title, "user": user, "link": link, "screen": screen, "phone": None}
	frappe.cache.set_value(_key(token), said, expires_in_sec=LIFE)
	url = get_url(f"/slide-remote?t={token}")
	return {"token": token, "screen": screen, "url": url, "qr": qr.svg(url)}


def phone_key(token: str) -> str:
	"""This phone's own key for a token, kept in a cookie of its own so a
	reloaded page is still the same phone."""
	name = f"one_remote_{hashlib.sha256(token.encode()).hexdigest()[:12]}"
	request = getattr(frappe.local, "request", None)
	key = (request.cookies.get(name) if request else None) or ""
	if not KEY[0] <= len(key) <= KEY[1]:
		key = secrets.token_hex(18)
		if request:
			frappe.local.cookie_manager.set_cookie(name, key, max_age=LIFE, httponly=True, samesite="Lax")
	return key


@frappe.whitelist(methods=["POST"])
def pair(name: Annotated[str, "The presentation being presented."]) -> dict:
	"""A phone to drive the presenter view of this presentation."""
	item = api._may(name, "read")
	return _pair(name, item["file_name"], user=frappe.session.user)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=20, seconds=60)
def pair_link(token: str, ticket: str, item: str | None = None) -> dict:
	"""A phone to drive a page showing the presentation through a link. It
	moves that page and nothing else, so being in front of it is the right
	to it, and nobody signs in."""
	from onedesk.one_deck import shared

	link, name = shared.opened(token, item)
	if not shared._ticket_holds(link, name, ticket):
		raise frappe.PermissionError
	return _pair(name, frappe.db.get_value(api.PRESENTATION, name, "title") or "", link=link.name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def unpair(token: Annotated[str, "The phone's token."], screen: str | None = None) -> None:
	"""The screen closed: the phone can do nothing more. Said by the screen,
	with its own key, or by the presenter who paired."""
	said = paired(token)
	if said and (_same(screen, said["screen"]) or (said["user"] and said["user"] == frappe.session.user)):
		frappe.cache.delete_value(_key(token))


def _link_holds(name: str | None) -> bool:
	if not name:
		return True
	disabled, until = frappe.db.get_value("Cloud Link", name, ["disabled", "expires_on"]) or (1, None)
	return not disabled and not (until and get_datetime(until) < now_datetime())


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60)
def admit(token: str, key: str | None = None) -> dict:
	"""Asked by the socket server when a screen or a phone joins: the room,
	for the screen's own key, or for the first phone's, which keeps it, so
	somebody else in the room who scans the code drives nothing."""
	said = paired(token)
	if not said or not key or not KEY[0] <= len(key) <= KEY[1] or not _link_holds(said.get("link")):
		return {"ok": False}
	if not _same(key, said["screen"]):
		if said["phone"] and not _same(key, said["phone"]):
			return {"ok": False, "taken": True}
		if not said["phone"]:
			frappe.cache.set_value(_key(token), {**said, "phone": key}, expires_in_sec=LIFE)
	return {"ok": True, "room": room(token)}


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=30, seconds=60)
def notes(token: str, key: str | None = None) -> list[str]:
	"""Each slide's notes, for the paired phone of somebody signed in who may
	read the presentation; a phone that only scanned a code gets none."""
	said = paired(token)
	if not said or not _same(key, said["phone"]) or frappe.session.user == "Guest":
		return []
	try:
		api._may(said["presentation"], "read")
	except frappe.PermissionError:
		frappe.clear_messages()
		return []
	return [row.notes or "" for row in frappe.get_doc(api.PRESENTATION, said["presentation"]).slides]
