"""A screen and what it shows. A TV opens /tv, which asks for a pairing code
and shows it; somebody in OneDisplay enters the code and picks the channel;
the TV is given a token once and from then on asks for what to show with it.
The TV asks every few seconds: an old TV's browser keeps a plain request
going where a socket drops. Every call a screen makes is a POST, so what it
changes (its token taken, when it was last seen) is written when it ends."""

import hashlib
import hmac
import secrets
from typing import Annotated

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import add_to_date, cint, flt, get_datetime, getdate, now_datetime, today

from onedesk.one_display import programme, sizes
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
	frappe.throw(_("No pairing code is available. Try again."))


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=600)
def start(
	device: Annotated[str | None, "What the screen says it is."] = None,
	kind: Annotated[str | None, "Screen, or Radio for /radio, which plays a zone's sound and shows nothing."] = None,
) -> dict:
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
			"kind": "Radio" if kind == "Radio" else "Screen",
			"last_seen": now_datetime(),
		}
	).insert(ignore_permissions=True)
	return {"screen": screen.name, "code": screen.pair_code, "secret": secret, "qr": _pairing_qr(screen.pair_code)}


def _pairing_qr(code: str) -> str:
	"""A code a phone scans to open Pair a Screen with this code filled in."""
	from frappe.utils import get_url

	from onedesk.one import qr

	return qr.svg(get_url(f"/desk/display-screen?pair_code={code}"))


@frappe.whitelist(allow_guest=True, methods=["POST"])
def status(screen: str, secret: str) -> dict:
	"""Whether the screen has been paired; the first time it has, its token."""
	row = frappe.db.get_value(
		DOCTYPE, screen, ["status", "pair_code", "secret_hash", "token", "screen_name", "channel", "sound_zone"], as_dict=True
	)
	if not row or not hmac.compare_digest(row.secret_hash or "", _hash(secret)):
		return {"gone": 1}
	if row.status != "Paired":
		return {"code": row.pair_code, "qr": _pairing_qr(row.pair_code)}
	if not row.token:
		return {"gone": 1}
	frappe.db.set_value(DOCTYPE, screen, "token", None, update_modified=False)
	return {"token": row.token, "name": row.screen_name, "plays": row.channel or row.sound_zone or ""}


@frappe.whitelist(methods=["POST"])
def pair(
	code: Annotated[str, "The code the screen shows."],
	screen_name: Annotated[str, "What to call the screen."],
	channel: Annotated[str | None, "The channel it shows; a radio shows none."] = None,
	rotate: Annotated[int, "Degrees to turn the picture: 0, 90, 180 or 270."] = 0,
	sound_zone: Annotated[str | None, "The sound zone it plays, if any."] = None,
) -> str:
	"""Pair the screen or radio showing this code."""
	frappe.has_permission(DOCTYPE, "write", throw=True)
	name = frappe.db.get_value(DOCTYPE, {"pair_code": (code or "").strip(), "status": "Waiting to Pair"})
	if not name:
		frappe.throw(_("No screen is showing code {0}. Check the code and try again.").format(code))
	token = secrets.token_urlsafe(32)
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.kind == "Radio" and not sound_zone:
		frappe.throw(_("Select a sound zone for the radio."))
	if doc.kind != "Radio" and not channel:
		frappe.throw(_("Select a channel for the screen."))
	doc.update(
		{
			"screen_name": screen_name,
			"channel": channel if doc.kind != "Radio" else None,
			"sound_zone": sound_zone or None,
			"rotate": str(cint(rotate)) if cint(rotate) in (0, 90, 180, 270) else "0",
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
		[
			"name", "screen_name", "channel", "rotate", "muted", "dark", "command", "command_at", "token_hash", "last_seen",
			"kind", "sound_zone", "plays_sound",
			"boot", "restarts_today", "last_restart", "device",
		],
		as_dict=True,
	)
	if not row or not row.token_hash or not hmac.compare_digest(row.token_hash, _hash(token)):
		return None
	return row


def _alert() -> str | None:
	settings = frappe.get_cached_doc("Display Settings")
	return settings.alert_message if settings.alert_active else None


# How far a screen may go before it is shown as at risk: of its page's
# memory limit, and of the device's memory taken by decoded pictures.
HEAP_SHARE = 0.8
PICTURE_SHARE = 0.25
PICTURES_UNKNOWN_MB = 400
RESTARTS = 3
MB = 1024 * 1024


def _why(said: str) -> str:
	return {
		"memory": _("Page memory was nearly full."),
		"nightly": _("Nightly reload."),
		"command": _("Reloaded from OneDisplay."),
		"start": _("Started or opened."),
	}.get(said) or _("The device or browser restarted unexpectedly.")


def _risks(seen: dict) -> list[str]:
	"""Why a screen may fail soon, from what it last said about itself."""
	said = []
	heap, limit = cint(seen.get("heap_mb")), cint(seen.get("heap_limit_mb"))
	if limit and heap > limit * HEAP_SHARE:
		said.append(_("Page memory is {0}% full.").format(round(heap * 100 / limit)))
	pictures, memory = cint(seen.get("pictures_mb")), flt(seen.get("memory_gb"))
	if memory and pictures > memory * 1024 * PICTURE_SHARE:
		said.append(_("Images use {0} MB, at least a quarter of the device memory.").format(pictures))
	elif not memory and pictures > PICTURES_UNKNOWN_MB:
		said.append(_("Images use {0} MB.").format(pictures))
	if cint(seen.get("restarts_today")) >= RESTARTS:
		said.append(_("Restarted {0} times today.").format(cint(seen["restarts_today"])))
	if seen.get("video_too_big"):
		said.append(_("A video is {0}, larger than this screen's resolution.").format(seen["largest_video"]))
	return said


def _heard(row, report: str | dict | None) -> None:
	"""What a screen says about itself, at most once a minute: its pixels, its
	memory and what its pictures and videos take, and a new page with why
	the last one ended. Kept on the Display Screen, with whether it is at risk."""
	said = frappe.parse_json(report) if isinstance(report, str) else report
	if not isinstance(said, dict):
		return
	values = {}
	w, h, dpr = cint(said.get("w")), cint(said.get("h")), flt(said.get("dpr")) or 1
	if w and h:
		values["pixels"] = f"{w} × {h} · {dpr:g}x"
	if flt(said.get("mem")):
		values["memory_gb"] = flt(said["mem"])
	for key, field in (("heap", "heap_mb"), ("limit", "heap_limit_mb"), ("pictures", "pictures_mb")):
		if said.get(key) is not None:
			values[field] = round(flt(said[key]) / MB)
	video = said.get("video") or []
	if isinstance(video, list) and len(video) == 2 and cint(video[0]) and cint(video[1]):
		vw, vh = cint(video[0]), cint(video[1])
		values["largest_video"] = f"{vw} × {vh}"
		shown = max(w * dpr, h * dpr) if w and h else 1920
		values["video_too_big"] = max(vw, vh) > max(shown * 2, 3840)
	if said.get("ua") and said["ua"] != row.device:
		values["device"] = str(said["ua"])[:500]
	boot = str(said.get("boot") or "")[:32]
	if boot and boot != row.boot:
		values["boot"] = boot
		if row.boot:
			same_day = row.last_restart and getdate(row.last_restart) == getdate(today())
			values["restarts_today"] = (cint(row.restarts_today) if same_day else 0) + (0 if said.get("why") == "start" else 1)
			values["last_restart"] = now_datetime()
			values["last_restart_reason"] = _why(said.get("why") or "")
	seen = {**row, **values}
	risks = _risks(seen)
	values.pop("video_too_big", None)
	values["at_risk"] = 1 if risks else 0
	values["risk"] = "\n".join(risks)
	frappe.db.set_value(DOCTYPE, row.name, values, update_modified=False)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def state(screen: str, token: str, have: str | None = None, report: str | None = None) -> dict:
	"""Everything a paired screen shows now, and the server's time, which the
	screen keeps its clock to. Once a minute it also says what it is (_heard)."""
	row = _screen(screen, token)
	if not row:
		return {"gone": 1}
	if report:
		_heard(row, report)
	if not row.last_seen or get_datetime(row.last_seen) < add_to_date(now_datetime(), seconds=-30):
		frappe.db.set_value(DOCTYPE, screen, "last_seen", now_datetime(), update_modified=False)
	return {
		"now": programme.now_ms(),
		"screen": {
			"name": row.screen_name, "rotate": cint(row.rotate), "muted": row.muted, "dark": row.dark,
			"kind": row.kind or "Screen", "plays_sound": cint(row.plays_sound),
		},
		"command": {"name": row.command, "at": str(row.command_at or "")},
		"alert": _alert(),
		"brand": _brand(),
		"zone": programme.zone_minutes(),
		"today": programme.today_line(_language(row.channel)),
		"day": programme.day_parts(_language(row.channel)),
		"channel": _channel(row.channel, have) if row.kind != "Radio" else None,
		# what it plays for the speakers it is wired to, if any (programme.heard)
		"sounds": programme.heard(row.sound_zone, _language(row.channel)),
	}


def _language(channel: str | None) -> str:
	said = frappe.db.get_value("Display Channel", channel, "voice_language") if channel else None
	return said or frappe.db.get_default("lang") or "en"


def _channel(name: str | None, have: str | None):
	if not name:
		return None
	said = programme.compose(name)
	return programme.light(said) if have and have == said["revision"] else said


@frappe.whitelist(methods=["POST"])
def preview(
	channel: Annotated[str | None, "The channel."] = None,
	collection: Annotated[str | None, "A widget collection to show instead, or alone."] = None,
) -> dict:
	"""What a screen on this channel shows now, for somebody in the desk: the
	channel's Preview, and the layout editor's, which may have a collection
	and no channel."""
	if channel:
		frappe.has_permission("Display Channel", "read", doc=channel, throw=True)
		said = programme.compose(channel)
	else:
		said = {
			"name": "",
			"width": 1920,
			"height": 1080,
			"mode": "show",
			"muted": True,
			"language": frappe.local.lang,
			"slides": None,
			"layout": None,
			"words": programme.words(),
		}
	if collection:
		frappe.has_permission("Widget Collection", "read", doc=collection, throw=True)
		said["layout"] = programme.layout(collection, said["language"])
		if not channel:
			said["width"], said["height"] = sizes.pixels(frappe.get_cached_doc("Widget Collection", collection))
	said["mode"] = "show"
	said["revision"] = programme._revision(said)
	return {
		"now": programme.now_ms(),
		"screen": {"name": _("Preview"), "rotate": 0, "muted": 1, "dark": 0, "kind": "Screen", "plays_sound": 0},
		"command": {"name": None, "at": ""},
		"alert": _alert(),
		"brand": _brand(),
		"zone": programme.zone_minutes(),
		"today": programme.today_line(said["language"]),
		"day": programme.day_parts(said["language"]),
		"channel": said,
	}


def _brand() -> dict:
	company = frappe.db.get_default("company")
	row = (
		frappe.db.get_value("Company", company, ["company_name", "company_logo", "one_brand_icon", "one_brand_colour"], as_dict=True)
		if company
		else None
	) or {}
	return {
		"name": row.get("company_name") or "",
		"logo": row.get("company_logo"),
		"icon": row.get("one_brand_icon") or row.get("company_logo"),
		"colour": row.get("one_brand_colour"),
	}


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=60)
def take(screen: str, token: str, widget: str, service: str) -> dict:
	"""A kiosk widget on this screen's channel hands out a ticket."""
	row = _screen(screen, token)
	if not row or not row.channel:
		frappe.throw(_("This screen has no kiosk."), frappe.PermissionError)
	collection = programme.plays(frappe.get_cached_doc("Display Channel", row.channel))["widgets"]
	kiosk = frappe.db.get_value(
		"Display Widget",
		{"name": widget, "parent": collection, "parenttype": "Widget Collection", "widget_type": "Kiosk"},
		"source",
	)
	queue = frappe.db.get_value("Display Source", {"name": kiosk, "kind": "Queue"}, "queue") if kiosk else None
	if not queue:
		frappe.throw(_("This screen has no kiosk."), frappe.PermissionError)
	return queues.take(queue, service)


@frappe.whitelist(methods=["POST"])
def control(screen: Annotated[str, "The screen."], command: Annotated[str, "reload, mute, unmute, off or on."]) -> str:
	"""Tell a screen to reload, go quiet or dark, or come back."""
	if command not in COMMANDS:
		frappe.throw(_("{0} is not a valid screen command.").format(command))
	doc = frappe.get_doc(DOCTYPE, screen)
	doc.check_permission("write")
	doc.update({**COMMANDS[command], "command": command, "command_at": now_datetime()})
	doc.save()
	return _("Sent.")


@frappe.whitelist(methods=["POST"])
def alert(message: Annotated[str, "What every screen shows; empty ends the alert."] = "") -> str:
	"""Show a message on every screen, over everything, or end it: whoever
	holds OneDisplay's Send an Emergency Alert (abilities.py)."""
	from onedesk.one import rights

	if not rights.held("Display Settings", "display_alert"):
		frappe.throw(_("You do not have permission to send an emergency alert."), frappe.PermissionError)
	settings = frappe.get_doc("Display Settings")
	settings.alert_active = 1 if (message or "").strip() else 0
	settings.alert_message = (message or "").strip() or settings.alert_message
	settings.flags.ignore_permissions = True
	settings.save()
	if settings.alert_active:
		from onedesk.one_display import tell

		tell.alert_sent(settings.alert_message)
	return _("The alert is showing on all screens.") if settings.alert_active else _("The alert has ended.")
