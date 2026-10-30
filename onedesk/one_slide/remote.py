"""A phone as the presenter's remote (AGENTS.md, Notes and presenting).

The presenter view pairs a phone by a QR code carrying a token for this one
presentation and person; the phone's page (www/slide-remote) and the
presenter view meet in the token's socket room (realtime/handlers.js).
Nothing a phone sends reaches the server beyond the room.
"""

import hashlib
import secrets
from typing import Annotated

import frappe
from frappe.rate_limiter import rate_limit
from frappe.utils import get_url

from onedesk.one_slide import api

LIFE = 8 * 3600
ROOM = "onedesk:remote/{}"


def _key(token: str) -> str:
	return f"one_slide_remote:{token}"


def paired(token: str | None) -> dict | None:
	"""The presentation and person a token pairs, while it lasts."""
	if not token or len(token) > 64:
		return None
	return frappe.cache.get_value(_key(token)) or None


def room(token: str) -> str:
	return ROOM.format(hashlib.sha256(token.encode()).hexdigest()[:24])


@frappe.whitelist(methods=["POST"])
def pair(name: Annotated[str, "The presentation being presented."]) -> dict:
	"""A token for a phone to drive this presentation, the address it opens
	and the QR code that carries it."""
	from onedesk.one import qr

	item = api._may(name, "read")
	token = secrets.token_urlsafe(18)
	frappe.cache.set_value(_key(token), {"presentation": name, "user": frappe.session.user, "title": item["file_name"]}, expires_in_sec=LIFE)
	url = get_url(f"/slide-remote?t={token}")
	return {"token": token, "url": url, "qr": qr.svg(url)}


@frappe.whitelist(methods=["POST"])
def unpair(token: Annotated[str, "The phone's token."]) -> None:
	"""The presenter view closed: the phone can do nothing more."""
	said = paired(token)
	if said and said["user"] == frappe.session.user:
		frappe.cache.delete_value(_key(token))


@frappe.whitelist(allow_guest=True, methods=["GET"])
@rate_limit(limit=60, seconds=60)
def admit(token: str) -> dict:
	"""Asked by the socket server when the phone or the presenter view joins:
	the room, while the token lasts."""
	if not paired(token):
		return {"ok": False}
	return {"ok": True, "room": room(token)}
