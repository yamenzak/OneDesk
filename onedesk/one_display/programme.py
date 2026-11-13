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
from frappe.utils import cint, flt, get_datetime, get_system_timezone, get_time, getdate, now_datetime

from onedesk.one_display import sizes, sources, widgets

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


CACHED = "one_display:composed:"
KEPT_FOR = 30


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
	"""What a channel's or a sound zone's schedule says now: its playlists, and
	whether it sleeps, is off or is muted. A later row wins over an earlier one."""
	at = at or now_datetime()
	said = {
		"slides": channel.get("slide_playlist"),
		"widgets": channel.get("widget_collection"),
		"music": channel.get("music_playlist"),
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
	"""A file a screen may play: on this machine, in the store, or on the web."""
	from onedesk.one_cloud import store

	path = path or ""
	return path if path.startswith(("/files/", f"{store.FETCH}?key=files/public/", "https://", "http://")) else ""


def slides(name: str | None, today=None, edge: int | None = None) -> dict | None:
	if not name:
		return None
	playlist = frappe.get_cached_doc("Slide Playlist", name)
	today = getdate(today)
	shown = []
	for row in playlist.slides:
		if row.paused or (row.from_date and getdate(row.from_date) > today) or (row.to_date and getdate(row.to_date) < today):
			continue
		if row.kind == "Presentation":
			shown += [{**one, "id": f"{row.name}-{one['id']}", "kind": "Slide", "fill": cint(row.fill)} for one in _presented(row, edge)]
		elif row.kind == "Web Page" and (row.url or "").startswith("https://"):
			shown.append({"id": row.name, "kind": "Web Page", "src": row.url, "ms": max(cint(row.duration) or SLIDE, 2) * 1000})
	return {"name": name, "transition": (playlist.transition or "Fade").lower(), "slides": shown}


def _presented(row, edge: int | None = None) -> list[dict]:
	"""A presentation row's slides, as one_slide/play.py gives them to a screen."""
	from onedesk.one_slide import api, play

	url = frappe.db.get_value("File", row.presentation, "file_url") if row.presentation else None
	name = api.presentation_of(url)
	if not name or not frappe.db.exists("Presentation", name):
		return []
	return play.for_screen(name, cint(row.duration) or SLIDE, edge=edge)


def _spoken(ticket: str) -> str:
	"""A001 as a voice says it: A 1."""
	found = re.match(r"^(\D*)0*(\d+)$", ticket or "")
	return f"{found.group(1)} {found.group(2)}".strip() if found else ticket


def _shown_now(row, at: datetime) -> bool:
	if (row.shown or "Always") == "Always":
		return True
	return _within(frappe._dict(days="Every Day", from_time=row.from_time, to_time=row.to_time), at)


def layout(name: str | None, lang: str, at: datetime | None = None, edge: int | None = None) -> dict | None:
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
			if settings.get("layout") == "wifi":
				link = wifi(settings.get("network"), settings.get("password"))
			data["svg"] = _qr(link) if link else ""
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
	from onedesk.one_display import screen

	return {"name": name, "background": collection.background or "", "widgets": placed, "backdrop": screen.drawn(collection, edge)}


def wifi(network, password) -> str:
	"""The link a phone's camera reads as join this network. Pure."""
	if not network:
		return ""

	def quote(word) -> str:
		return "".join("\\" + c if c in "\\;,:\"" else c for c in str(word or ""))

	kind = "WPA" if password else "nopass"
	return f"WIFI:T:{kind};S:{quote(network)};P:{quote(password)};;"


def _qr(link: str) -> str:
	from onedesk.one import qr

	return qr.svg(link)


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
		if _url(row.file) and flt(row.duration) > 0 and not row.paused
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
						"audio": _url(ad.audio) or voices.spoken(ad.script, ad.language or lang, ad.voice or channel.get("voice"), ad.tone),
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
		"data": {one["id"]: one["data"] for one in ((said.get("layout") or {}).get("widgets") or [])},
		# a backdrop with chips, refilled each time its sources are read
		**({"backdrop": backdrop} if (backdrop := (said.get("layout") or {}).get("backdrop") or {}).get("live") else {}),
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


def day_parts(lang: str) -> dict:
	"""Today in pieces, for a clock drawn as a page of a calendar."""
	day = now_datetime()
	return {"weekday": _babel(day, "EEEE", lang), "day": _babel(day, "d", lang), "month": _babel(day, "MMMM", lang), "year": _babel(day, "y", lang)}


def zone_minutes() -> int:
	"""How far the workspace's clock is from UTC now, which a screen's clock
	widget adds: a TV's own time zone is often wrong."""
	offset = datetime.now(ZoneInfo(get_system_timezone())).utcoffset()
	return int(offset.total_seconds() // 60) if offset else 0


def current(channel_name: str) -> dict:
	"""What a screen on this channel plays, built once however many screens
	ask. A change forgets it at once (`live.wake`); the clock, within `KEPT_FOR`."""
	key = f"{CACHED}{channel_name}"
	said = frappe.cache.get_value(key)
	if said is None:
		said = compose(channel_name)
		frappe.cache.set_value(key, said, expires_in_sec=KEPT_FOR)
	return said


def forget() -> None:
	frappe.cache.delete_keys(CACHED)


def compose(channel_name: str, lang: str | None = None) -> dict:
	"""Everything a screen on this channel plays now."""
	channel = frappe.get_cached_doc("Display Channel", channel_name)
	lang = channel.voice_language or lang or frappe.db.get_default("lang") or "en"
	previous = frappe.local.lang
	frappe.local.lang = lang
	try:
		at = now_datetime()
		now = plays(channel, at)
		edge = longest(channel.name)
		said = {
			"name": channel.channel_name,
			# the frame in pixels the screen draws on and scales to fit (sizes.py)
			**dict(zip(("width", "height"), sizes.pixels(channel))),
			"mode": now["mode"],
			"muted": now["muted"],
			"language": lang,
			"slides": slides(now["slides"], edge=edge),
			"layout": layout(now["widgets"], lang, at, edge=edge),
			"words": words(),
			# the minute of the day screens reload at (screens.py, the brakes), or None
			"reload_at": _minutes(channel.get("reload_at")),
		}
	finally:
		frappe.local.lang = previous
	said["revision"] = _revision(said)
	return said


def heard(zone_name: str | None, lang: str | None = None) -> dict | None:
	"""What a sound zone plays now (D6 of SCRATCHPAD.md): its music, its voice
	ads, the calls of the queues that name it, and when to play its music
	quietly because a screen in it is playing a video's own sound. Played by
	a radio, or by a screen with no speakers of its own."""
	if not zone_name or not frappe.db.exists("Sound Zone", zone_name):
		return None
	zone = frappe.get_cached_doc("Sound Zone", zone_name)
	lang = zone.voice_language or lang or frappe.db.get_default("lang") or "en"
	previous = frappe.local.lang
	frappe.local.lang = lang
	try:
		now = plays(zone)
		return {
			"name": zone.zone_name,
			"language": lang,
			"muted": now["muted"],
			"announce": cint(zone.announce),
			"music": music(now["music"]),
			"ads": ads(zone, lang),
			"calls": calls(zone, lang) if cint(zone.announce) else [],
			"duck": duck(zone.name),
		}
	finally:
		frappe.local.lang = previous


def calls(zone, lang: str) -> list[dict]:
	"""Today's calls of the queues that name the zone, newest first, each
	with what is said, how (a whole recording, or a voice pack's pieces to
	join), and the moment every player in the zone starts it: a few seconds
	after the call, so all have it by then."""
	from onedesk.one_display import packs, voices
	from onedesk.one_display import queue as queues

	out = []
	for name, reading in frappe.get_all("Queue", filters={"sound_zone": zone.name}, fields=["name", "number_reading"], as_list=True):
		for call in queues.board(name).get("called") or []:
			say = _("Ticket {0}, counter {1}", lang=lang).format(_spoken(call["ticket"]), call["counter"] or "")
			whole = voices.kept(say, lang, zone.voice) if zone.voice else None
			joined = None if whole else packs.voiced(call["ticket"], call["counter"], lang, zone.voice, reading)
			if joined is None and not whole:
				whole = voices.spoken(say, lang, zone.voice)
			out.append({**call, "say": say, "audio": whole or "", "pieces": joined or [], "start": _epoch(get_datetime(call["at"])) + CALL_DELAY})
	return sorted(out, key=lambda one: one["start"], reverse=True)


# how long after a call every player in the zone starts saying it
CALL_DELAY = 3000


def duck(zone: str) -> list[list[dict]]:
	"""For each channel a screen in the zone shows with its sound on, the
	length of each slide and whether it plays a video's sound: from the fixed
	timing of the playlists, any player in the zone knows when to play its
	music quietly."""
	out = []
	names = frappe.get_all("Display Screen", filters={"sound_zone": zone, "plays_sound": 1, "kind": "Screen", "channel": ["is", "set"]}, pluck="channel", distinct=True)
	for name in names:
		playing = slides(plays(frappe.get_cached_doc("Display Channel", name))["slides"])
		items = (playing or {}).get("slides") or []
		if any(_sounds(one) for one in items):
			out.append([{"ms": one["ms"], "sound": 1 if _sounds(one) else 0} for one in items])
	return out


def _sounds(item: dict) -> bool:
	"""Whether a slide plays a video's own sound. Pure."""
	return any(one.get("type") == "video" and one.get("sound") for one in ((item.get("slide") or {}).get("elements") or []))


# a 4K screen's, until a screen on the channel says what it is
LONGEST = 3840
PIXELS = re.compile(r"(\d+)\D+(\d+)\D+([\d.]+)x")


def longest(channel: str) -> int:
	"""How large a channel's pictures are asked for: the longest edge, in the
	device's own pixels, of the largest screen showing it (screens._heard),
	as one of the sizes pictures are copied at (one_slide/sized.py)."""
	from onedesk.one_slide import sized

	reported = frappe.get_all("Display Screen", filters={"channel": channel, "pixels": ["is", "set"]}, pluck="pixels")
	return sized.bucket(max((_longest(one) for one in reported), default=0) or LONGEST)


def _longest(pixels: str) -> int:
	"""'1920 × 1080 · 2x' as 3840. Pure."""
	found = PIXELS.search(pixels or "")
	return int(max(int(found.group(1)), int(found.group(2))) * float(found.group(3))) if found else 0


def _minutes(value) -> int | None:
	if not value:
		return None
	hours, minutes = (str(value).split(":") + ["0"])[:2]
	return cint(hours) * 60 + cint(minutes)


def words() -> dict:
	"""What a board and a kiosk say around the data, in the channel's
	language, so a screen speaks one language whatever its browser asks for."""
	return {
		"counter": _("Counter"),
		"waiting": _("Waiting"),
		"nobody": _("No ticket is being served."),
		"your": _("Your ticket"),
		"ahead": _("{0} ahead of you"),
		"busy": _("The ticket could not be taken. Try again."),
		"minutes": _("{0} min"),
		"hours": _("{0} h {1}"),
		"no_news": _("No headlines yet."),
	}


def _revision(said: dict) -> str:
	"""Changes when what is drawn changes shape, not when a widget's rows do,
	so a screen rebuilds only when it has to."""
	shape = {
		"frame": [said["width"], said["height"]],
		"slides": said["slides"],
		"layout": [
			{k: v for k, v in one.items() if k != "data"} for one in ((said["layout"] or {}).get("widgets") or [])
		],
		"background": (said["layout"] or {}).get("background"),
		"backdrop": ((said["layout"] or {}).get("backdrop") or {}).get("shape"),
	}
	return hashlib.sha1(json.dumps(shape, sort_keys=True, default=str).encode()).hexdigest()[:12]
