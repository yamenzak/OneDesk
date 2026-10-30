"""What a channel plays at this moment: its slides, the widgets over them
with what each shows, its music and voice ads, and whether its schedule has
put it to sleep. Every screen on a channel plays in step on one clock that
started at the epoch (one_display/AGENTS.md, Playing in step)."""

import hashlib
import json
import re
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import cint, flt, get_system_timezone, get_time, getdate, now_datetime

from onedesk.one_display import sources, widgets

DAYS = {
	"Every Day": range(7),
	"Weekdays": range(5),
	"Weekend": (5, 6),
	"Monday": (0,),
	"Tuesday": (1,),
	"Wednesday": (2,),
	"Thursday": (3,),
	"Friday": (4,),
	"Saturday": (5,),
	"Sunday": (6,),
}
AHEAD = 15 * 60
# A time of day as an ad's times are written: 9.30, 09:30.
TIME = re.compile(r"(\d{1,2})[:.](\d{2})")
SLIDE = 10


def now_ms() -> int:
	return int(time.time() * 1000)


def _epoch(local: datetime) -> int:
	"""A wall-clock time in the workspace's time zone, as the epoch in ms."""
	return int(local.replace(tzinfo=ZoneInfo(get_system_timezone())).timestamp() * 1000)


def _within(row, at: datetime) -> bool:
	"""Whether a row with days and a from and to time covers `at`. A row that
	ends before it starts runs across midnight, on the day it starts."""
	days = DAYS.get(row.get("days") or "Every Day", range(7))
	if not row.get("from_time") or not row.get("to_time"):
		return at.weekday() in days
	start, end, now = get_time(row.from_time), get_time(row.to_time), at.time()
	if start <= end:
		return at.weekday() in days and start <= now < end
	if now >= start:
		return at.weekday() in days
	return now < end and (at - timedelta(days=1)).weekday() in days


def plays(channel, at: datetime | None = None) -> dict:
	"""What the channel's schedule says now: its playlists, and whether it
	sleeps, is off or is muted. A later row wins over an earlier one."""
	at = at or now_datetime()
	said = {
		"slides": channel.slide_playlist,
		"widgets": channel.widget_collection,
		"music": channel.music_playlist,
		"mode": "show",
		"muted": False,
	}
	for row in channel.get("programme") or []:
		if not _within(row, at):
			continue
		if row.plays == "Slides":
			said["slides"] = row.slide_playlist
		elif row.plays == "Widgets":
			said["widgets"] = row.widget_collection
		elif row.plays == "Music":
			said["music"] = row.music_playlist
		elif row.plays == "Screensaver":
			said["mode"] = "screensaver"
		elif row.plays == "Screen Off":
			said["mode"] = "off"
		elif row.plays == "Muted":
			said["muted"] = True
	return said


def _url(path: str) -> str:
	path = path or ""
	return path if path.startswith(("/files/", "https://", "http://")) else ""


def slides(name: str | None, today=None) -> dict | None:
	if not name:
		return None
	playlist = frappe.get_cached_doc("Slide Playlist", name)
	today = getdate(today)
	shown = []
	for row in playlist.slides:
		if (row.from_date and getdate(row.from_date) > today) or (row.to_date and getdate(row.to_date) < today):
			continue
		one = {"id": row.name, "kind": row.kind, "fit": (row.fit or "Cover").lower(), "ms": max(cint(row.duration) or SLIDE, 2) * 1000}
		if row.kind in ("Image", "Video"):
			one["src"] = _url(row.file)
			if not one["src"]:
				continue
		elif row.kind == "Web Page":
			one["src"] = row.url if (row.url or "").startswith("https://") else ""
			if not one["src"]:
				continue
		elif row.kind == "Design":
			one["html"] = row.html or ""
		shown.append(one)
	return {"name": name, "transition": (playlist.transition or "Fade").lower(), "slides": shown}


def _spoken(ticket: str) -> str:
	"""A001 as a voice says it: A 1."""
	found = re.match(r"^(\D*)0*(\d+)$", ticket or "")
	return f"{found.group(1)} {found.group(2)}".strip() if found else ticket


def _shown_now(row, at: datetime) -> bool:
	if (row.shown or "Always") == "Always":
		return True
	return _within(frappe._dict(days="Every Day", from_time=row.from_time, to_time=row.to_time), at)


def layout(name: str | None, lang: str, at: datetime | None = None, voice: str | None = None) -> dict | None:
	"""A collection's widgets where they sit, each with what it shows now."""
	if not name:
		return None
	collection = frappe.get_cached_doc("Widget Collection", name)
	at = at or now_datetime()
	placed = []
	for row in collection.widgets:
		if row.widget_type not in widgets.TYPES or not _shown_now(row, at):
			continue
		settings = {**widgets.defaults(row.widget_type), **_json(row.settings)}
		data = sources.fill(row, lang)
		if row.widget_type == "QR Code":
			link = ((data.get("rows") or [{}])[0] or {}).get("link") or settings.get("link")
			data["svg"] = _qr(link) if link else ""
		if row.widget_type == "Weather" and data.get("whole"):
			for day in data["whole"].get("days") or []:
				day["label"] = _babel(day.get("date"), "EEE", lang)
		if row.widget_type == "Queue Board" and data.get("whole"):
			from onedesk.one_display import voices

			for call in data["whole"].get("called") or []:
				call["say"] = _("Ticket {0}, counter {1}", lang=lang).format(_spoken(call["ticket"]), call["counter"] or "")
				call["audio"] = voices.spoken(call["say"], lang, voice)
		placed.append(
			{
				"id": row.name,
				"type": row.widget_type,
				"x": flt(row.x),
				"y": flt(row.y),
				"w": flt(row.w),
				"h": flt(row.h),
				"layer": cint(row.layer),
				"settings": settings,
				"data": data,
			}
		)
	return {"name": name, "background": collection.background or "", "widgets": placed}


def _qr(link: str) -> str:
	"""The code as SVG, drawn here so a TV needs no library for it."""
	import pyqrcode

	return _svg(pyqrcode.create(str(link)[:1000], error="M"))


def _svg(code) -> str:
	rows = code.code
	size = len(rows) + 2
	cells = "".join(
		f'<rect x="{x + 1}" y="{y + 1}" width="1" height="1"/>' for y, row in enumerate(rows) for x, cell in enumerate(row) if cell
	)
	return (
		f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" shape-rendering="crispEdges">'
		f'<rect width="{size}" height="{size}" fill="#fff"/><g fill="#000">{cells}</g></svg>'
	)


def _json(text) -> dict:
	try:
		said = json.loads(text or "{}")
	except ValueError:
		return {}
	return said if isinstance(said, dict) else {}


def music(name: str | None) -> dict | None:
	if not name:
		return None
	playlist = frappe.get_cached_doc("Music Playlist", name)
	tracks = [
		{"id": row.name, "src": _url(row.file), "ms": int(flt(row.duration) * 1000), "title": row.title or ""}
		for row in playlist.tracks
		if _url(row.file) and flt(row.duration) > 0
	]
	return {"name": name, "volume": cint(playlist.volume if playlist.volume is not None else 60), "tracks": tracks}


def _offset(key: str, period: int) -> int:
	return int(hashlib.sha1(key.encode()).hexdigest(), 16) % max(period, 1)


def ads(channel, lang: str, now: int | None = None) -> list[dict]:
	"""The ads due in the next quarter of an hour, each at an exact moment."""
	from onedesk.one_display import voices

	now = now or now_ms()
	due = []
	local = now_datetime()
	for row in channel.get("ads") or []:
		ad = frappe.get_cached_doc("Voice Ad", row.voice_ad) if frappe.db.exists("Voice Ad", row.voice_ad) else None
		if not ad:
			continue
		moments = []
		if row.plays == "At Times":
			for day in (0, 1):
				for said in re.split(r"[,\s]+", row.at_times or ""):
					found = TIME.fullmatch(said)
					if not found:
						continue
					hour, minute = int(found.group(1)), int(found.group(2))
					when = (local + timedelta(days=day)).replace(hour=hour % 24, minute=minute % 60, second=0, microsecond=0)
					moments.append(_epoch(when))
		else:
			period = max(cint(row.every) or 15, 1) * 60 * 1000
			slot = now // period
			while slot * period <= now + AHEAD * 1000:
				moments.append(slot * period + _offset(f"{row.name}:{slot}", period))
				slot += 1
		for at in moments:
			if now - 30 * 1000 <= at <= now + AHEAD * 1000:
				due.append(
					{
						"key": f"{row.name}:{at}",
						"at": at,
						"audio": _url(ad.audio) or voices.spoken(ad.script, ad.language or lang, ad.voice or channel.voice, ad.tone),
						"text": ad.script,
						"lang": ad.language or lang,
						"chime": cint(ad.chime),
					}
				)
	return sorted(due, key=lambda one: one["at"])


def light(said: dict) -> dict:
	"""What changes between two answers when the shape has not: the mode, the
	ads and each widget's rows. A screen that already has the revision is
	sent only this."""
	return {
		"revision": said["revision"],
		"light": 1,
		"mode": said["mode"],
		"muted": said["muted"],
		"ads": said["ads"],
		"data": {one["id"]: one["data"] for one in ((said.get("layout") or {}).get("widgets") or [])},
	}


def _babel(day, pattern: str, lang: str) -> str:
	"""A day in the reader's words, as frappe's own dates are: a TV's browser
	is too old to be trusted with it."""
	from babel.dates import format_date

	try:
		return format_date(getdate(day), pattern, locale=(lang or "en").replace("-", "_"))
	except Exception:
		return format_date(getdate(day), pattern, locale="en")


def today_line(lang: str) -> str:
	"""Today, as a clock widget writes it under the time."""
	return _babel(now_datetime(), "EEEE d MMMM", lang)


def zone_minutes() -> int:
	"""How far the workspace's clock is from UTC now, which a screen's clock
	widget adds: a TV's own time zone is often wrong."""
	offset = datetime.now(ZoneInfo(get_system_timezone())).utcoffset()
	return int(offset.total_seconds() // 60) if offset else 0


def compose(channel_name: str, lang: str | None = None) -> dict:
	"""Everything a screen on this channel plays now."""
	channel = frappe.get_cached_doc("Display Channel", channel_name)
	lang = channel.voice_language or lang or frappe.db.get_default("lang") or "en"
	previous = frappe.local.lang
	frappe.local.lang = lang
	try:
		at = now_datetime()
		now = plays(channel, at)
		said = {
			"name": channel.channel_name,
			"orientation": (channel.orientation or "Landscape").lower(),
			"mode": now["mode"],
			"muted": now["muted"],
			"language": lang,
			"announce": cint(channel.announce),
			"slides": slides(now["slides"]),
			"layout": layout(now["widgets"], lang, at, channel.voice),
			"music": music(now["music"]),
			"ads": ads(channel, lang),
			"words": words(),
		}
	finally:
		frappe.local.lang = previous
	said["revision"] = _revision(said)
	return said


def words() -> dict:
	"""What a board and a kiosk say around the data, in the channel's
	language, so a screen speaks one language whatever its browser asks for."""
	return {
		"counter": _("Counter"),
		"waiting": _("Waiting"),
		"nobody": _("Nobody is being served yet."),
		"your": _("Your ticket"),
		"ahead": _("{0} ahead of you"),
		"busy": _("The ticket could not be taken. Try again."),
	}


def _revision(said: dict) -> str:
	"""Changes when what is drawn changes shape, not when a widget's rows do,
	so a screen rebuilds only when it has to."""
	shape = {
		"orientation": said["orientation"],
		"slides": said["slides"],
		"music": said["music"],
		"layout": [
			{k: v for k, v in one.items() if k != "data"} for one in ((said["layout"] or {}).get("widgets") or [])
		],
		"background": (said["layout"] or {}).get("background"),
	}
	return hashlib.sha1(json.dumps(shape, sort_keys=True, default=str).encode()).hexdigest()[:12]
