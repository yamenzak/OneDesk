"""A screen and what it shows. A TV opens /tv, which asks for a pairing code
and shows it; somebody in OneDisplay enters the code and picks the channel;
the TV is given a token once and from then on asks for what to show with it.
The TV asks every few seconds: an old TV's browser keeps a plain request
going where a socket drops. Every call a screen makes is a POST, so what it
changes (its token taken, when it was last seen) is written when it ends."""

import hashlib
import hmac
import re
import secrets
from typing import Annotated

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, get_datetime, now_datetime

from onedesk.one_display import queue as queues

DOCTYPE = "Display Screen"
COMMANDS = {
	"reload": {},
	"mute": {"muted": 1},
	"unmute": {"muted": 0},
	"off": {"dark": 1},
	"on": {"dark": 0},
}


def _hash(value: str) -> str:
	return hashlib.sha256((value or "").encode()).hexdigest()


def _code() -> str:
	for _attempt in range(20):
		code = f"{secrets.randbelow(900000) + 100000}"
		if not frappe.db.exists(DOCTYPE, {"pair_code": code, "status": "Waiting to Pair"}):
			return code
	frappe.throw(_("No pairing code is free. Try again."))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=600)
def start(device: Annotated[str | None, "What the screen says it is."] = None) -> dict:
	"""A new screen asks to be paired: it is given a code to show and a secret
	only it holds."""
	secret = secrets.token_urlsafe(24)
	screen = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"screen_name": _("New Screen"),
			"status": "Waiting to Pair",
			"pair_code": _code(),
			"secret_hash": _hash(secret),
			"device": (device or "")[:500],
			"last_seen": now_datetime(),
		}
	).insert(ignore_permissions=True)
	return {"screen": screen.name, "code": screen.pair_code, "secret": secret}


@frappe.whitelist(allow_guest=True, methods=["POST"])
def status(screen: str, secret: str) -> dict:
	"""Whether the screen has been paired; the first time it has, its token."""
	row = frappe.db.get_value(DOCTYPE, screen, ["status", "pair_code", "secret_hash", "token"], as_dict=True)
	if not row or not hmac.compare_digest(row.secret_hash or "", _hash(secret)):
		return {"gone": 1}
	if row.status != "Paired":
		return {"code": row.pair_code}
	if not row.token:
		return {"gone": 1}
	frappe.db.set_value(DOCTYPE, screen, "token", None, update_modified=False)
	return {"token": row.token}


@frappe.whitelist(methods=["POST"])
def pair(
	code: Annotated[str, "The code the screen shows."],
	screen_name: Annotated[str, "What to call the screen."],
	channel: Annotated[str, "The channel it shows."],
	mode: Annotated[str, "Board or Kiosk."] = "Board",
) -> str:
	"""Pair the screen showing this code."""
	frappe.has_permission(DOCTYPE, "write", throw=True)
	name = frappe.db.get_value(DOCTYPE, {"pair_code": (code or "").strip(), "status": "Waiting to Pair"})
	if not name:
		frappe.throw(_("No screen is showing {0}. Check the code on the screen.").format(code))
	token = secrets.token_urlsafe(32)
	doc = frappe.get_doc(DOCTYPE, name)
	doc.update(
		{
			"screen_name": screen_name,
			"channel": channel,
			"mode": mode if mode in ("Board", "Kiosk") else "Board",
			"status": "Paired",
			"pair_code": None,
			"token": token,
			"token_hash": _hash(token),
		}
	)
	doc.save()
	return doc.name


def _screen(screen: str, token: str):
	row = frappe.db.get_value(
		DOCTYPE,
		screen,
		["name", "screen_name", "channel", "mode", "muted", "dark", "command", "command_at", "token_hash", "last_seen"],
		as_dict=True,
	)
	if not row or not row.token_hash or not hmac.compare_digest(row.token_hash, _hash(token)):
		return None
	return row


@frappe.whitelist(allow_guest=True, methods=["POST"])
def state(screen: str, token: str) -> dict:
	"""Everything a paired screen shows now."""
	row = _screen(screen, token)
	if not row:
		return {"gone": 1}
	if not row.last_seen or get_datetime(row.last_seen) < add_to_date(now_datetime(), seconds=-30):
		frappe.db.set_value(DOCTYPE, screen, "last_seen", now_datetime(), update_modified=False)
	channel = frappe.get_cached_doc("Display Channel", row.channel) if row.channel else None
	settings = frappe.get_cached_doc("Display Settings")
	said = {
		"screen": {"name": row.screen_name, "mode": row.mode, "muted": row.muted, "dark": row.dark},
		"command": {"name": row.command, "at": str(row.command_at or "")},
		"alert": settings.alert_message if settings.alert_active else None,
		"brand": _brand(),
		"channel": None,
		"board": None,
	}
	if channel:
		said["channel"] = {
			"name": channel.channel_name,
			"headline": channel.headline,
			"ticker": channel.ticker,
			"announce": channel.announce,
			"language": channel.voice_language or frappe.db.get_default("lang") or "en",
		}
		if channel.queue:
			said["board"] = queues.board(channel.queue)
			for row in said["board"]["called"]:
				row["say"] = _("Ticket {0}, counter {1}", lang=said["channel"]["language"]).format(
					_spoken(row["ticket"]), row["counter"] or ""
				)
	return said


def _spoken(ticket: str) -> str:
	"""A001 as a voice says it: A 1."""
	found = re.match(r"^(\D*)0*(\d+)$", ticket or "")
	return f"{found.group(1)} {found.group(2)}".strip() if found else ticket


def _brand() -> dict:
	company = frappe.db.get_default("company")
	row = (
		frappe.db.get_value("Company", company, ["company_name", "company_logo", "one_brand_colour"], as_dict=True)
		if company
		else None
	) or {}
	return {"name": row.get("company_name") or "", "logo": row.get("company_logo"), "colour": row.get("one_brand_colour")}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def take(screen: str, token: str, service: str) -> dict:
	"""A kiosk screen hands out a ticket."""
	row = _screen(screen, token)
	if not row or row.mode != "Kiosk" or not row.channel:
		frappe.throw(_("This screen does not hand out tickets."), frappe.PermissionError)
	queue = frappe.db.get_value("Display Channel", row.channel, "queue")
	if not queue:
		frappe.throw(_("This screen's channel has no queue."))
	return queues.take(queue, service)


@frappe.whitelist(methods=["POST"])
def control(screen: Annotated[str, "The screen."], command: Annotated[str, "reload, mute, unmute, off or on."]) -> str:
	"""Tell a screen to reload, go quiet or dark, or come back."""
	if command not in COMMANDS:
		frappe.throw(_("A screen cannot be told {0}.").format(command))
	doc = frappe.get_doc(DOCTYPE, screen)
	doc.check_permission("write")
	doc.update({**COMMANDS[command], "command": command, "command_at": now_datetime()})
	doc.save()
	return _("Sent.")


@frappe.whitelist(methods=["POST"])
def alert(message: Annotated[str, "What every screen shows; empty ends the alert."] = "") -> str:
	"""Show a message on every screen, over everything, or end it."""
	frappe.has_permission("Display Settings", "write", throw=True)
	settings = frappe.get_doc("Display Settings")
	settings.alert_active = 1 if (message or "").strip() else 0
	settings.alert_message = (message or "").strip() or settings.alert_message
	settings.save()
	return _("Every screen shows the alert.") if settings.alert_active else _("The alert has ended.")
