"""The showroom's screens. The lobby channel plays a presentation of three slides
with the queue board, a clock, how many projects are underway, a ticker,
quiet music and now and then a spoken ad, and sleeps at night. The kiosk
channel is a kiosk at the door, and the workshop's shows the weather and the
late tasks and is off at night. Layla runs OneDisplay and Omar works counter
2; the morning so far is six tickets. Three screens are on the list as paired
ones that have not been switched on yet."""

import io
import json
import math
import secrets
import struct
import wave

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_demo.people import OWNER
from onedesk.one_display import chips

QUEUE = "Showroom"
CHANNEL = "Showroom Lobby"
KIOSK = "Showroom Kiosk"
WORKSHOP = "Workshop"
MUSIC = "Showroom Calm"
ZONE = "Showroom"
BOARD = "Workshop Bays"
# the lobby's screen plays the showroom's sound itself; nothing else has speakers
SCREENS = (("Lobby TV", CHANNEL, "0", ZONE), ("Door Kiosk", KIOSK, "0", None), ("Workshop TV", WORKSHOP, "0", None))
SERVICES = (("Showroom Visit", "A"), ("Collections", "B"), ("Payments", "C"))
COUNTERS = (("1", OWNER), ("2", "omar@one.test"), ("3", None))
ROLES = {OWNER: "OneDisplay Manager", "omar@one.test": "OneDisplay User"}

SLIDES = (
	("#0E6E8C", "New this season", "Frameless glass entrances", "Twelve metres of clear glass, two sliding doors, fitted in a week."),
	("#1f2937", "Made in our workshop", "Aluminium cut to the millimetre", "Every frame is cut, drilled and anodised in Al Quoz."),
	("#7c2d12", "Ask at the counter", "A free site visit", "We measure, draw and price your project before you decide."),
)


def run(password=None):
	for user, role in ROLES.items():
		if frappe.db.exists("User", user):
			doc = frappe.get_doc("User", user)
			doc.flags.ignore_permissions = True
			doc.add_roles(role)
	if not frappe.db.exists("Queue", QUEUE):
		frappe.get_doc(
			{
				"doctype": "Queue",
				"queue_name": QUEUE,
				"wait_alert": 15,
				"services": [{"service": name, "prefix": prefix} for name, prefix in SERVICES],
				"counters": [{"counter": counter, "user": user} for counter, user in COUNTERS],
			}
		).insert(ignore_permissions=True)
	with as_user(OWNER):
		_screens()
	_paired()
	_morning()


def _make(doctype: str, name: str, values: dict) -> str:
	if not frappe.db.exists(doctype, name):
		frappe.get_doc({"doctype": doctype, **values}).insert()
	return name


def _screens():
	queue = _make("Display Source", "Showroom Queue", {"source_name": "Showroom Queue", "kind": "Queue", "queue": QUEUE})
	projects = _make(
		"Display Source",
		"Projects Underway",
		{
			"source_name": "Projects Underway",
			"kind": "Records",
			"ref_doctype": "Project",
			"filters": json.dumps([["Project", "status", "=", "Open"]]),
			"aggregate": "Count",
		},
	)
	_make(
		"Display Source",
		"Dubai Weather",
		{"source_name": "Dubai Weather", "kind": "Weather", "place": "Dubai", "latitude": 25.2048, "longitude": 55.2708},
	)
	late = _make(
		"Display Source",
		"Late Tasks",
		{"source_name": "Late Tasks", "kind": "Report", "report": "Delayed Tasks Summary", "refresh": 300},
	)
	rates = _make(
		"Display Source",
		"Exchange Rates",
		{"source_name": "Exchange Rates", "kind": "Exchange Rates", "currencies": "USD, EUR, GBP"},
	)
	# a board, set up the way any business sets one up: things, their states, how long each may last
	_make(
		"Display Board",
		BOARD,
		{
			"board_name": BOARD,
			"description": "The workshop's bays, set from a phone at each bay.",
			"states": [
				{"state": "Free", "colour": "#15803D"},
				{"state": "Cutting", "colour": "#B45309", "limit_minutes": 90},
				{"state": "Assembly", "colour": "#1D4ED8"},
				{"state": "Cleaning", "colour": "#6B7280", "limit_minutes": 20},
			],
			"items": [{"item_name": f"Bay {n}", "state": "Free", "since": frappe.utils.now_datetime()} for n in range(1, 5)],
		},
	)
	_make("Display Source", BOARD, {"source_name": BOARD, "kind": "Board", "board": BOARD})
	if not frappe.db.exists("Slide Playlist", "Showroom"):
		_make("Slide Playlist", "Showroom", {"playlist_name": "Showroom"})
		_showroom()
	# a figure and a list from a source are words with chips on the screen (chips.py)
	words = {name: not frappe.db.exists("Widget Collection", name) for name in (CHANNEL, WORKSHOP)}
	_make(
		"Widget Collection",
		CHANNEL,
		{
			"collection_name": CHANNEL,
			"widgets": [
				_widget("Queue Board", 64, 0, 36, 92, source=queue, settings={"rows": 5}),
				_widget("Clock", 2, 3, 22, 16),
				_widget(
					"Ticker",
					0,
					92,
					100,
					8,
					settings={"text": "Welcome to the Sahara Glass showroom. Take a ticket at the kiosk and we will call you shortly."},
				),
			],
		},
	)
	_make(
		"Widget Collection",
		KIOSK,
		{"collection_name": KIOSK, "widgets": [_widget("Kiosk", 0, 0, 100, 100, source=queue)]},
	)
	_make(
		"Widget Collection",
		WORKSHOP,
		{
			"collection_name": WORKSHOP,
			"widgets": [
				_widget("Text", 3, 4, 60, 12, settings={"text": "Workshop", "size": 7}),
				_widget("Clock", 76, 4, 22, 16),
				_widget("Weather", 66, 26, 32, 34, source="Dubai Weather"),
				_widget("QR Code", 76, 64, 16, 26, settings={"link": frappe.utils.get_url("/desk/task"), "caption": "Open your tasks"}),
				_widget("Ticker", 0, 92, 100, 8, source=rates, mapping={"text": "{line}"}),
			],
		},
	)
	if words[CHANNEL]:
		chips.onto(CHANNEL, chips.number("projects", {"value": "{value}"}, "Projects underway", (26, 3, 14, 16)), [{"key": "projects", "kind": "rows", "source": projects}])
	if words[WORKSHOP]:
		chips.onto(WORKSHOP, chips.listed("late", {"title": "{subject}", "subtitle": "Due {exp_end_date}"}, "Late tasks", 8, (3, 22, 58, 66)), [{"key": "late", "kind": "rows", "source": late, "limit": 12}])
	if not frappe.db.exists("Music Playlist", MUSIC):
		frappe.get_doc(
			{"doctype": "Music Playlist", "playlist_name": MUSIC, "volume": 30, "tracks": [{"title": "Morning Glass", "file": _track(), "duration": 24}]}
		).insert()
	_make(
		"Voice Ad",
		"Frameless Glass",
		{
			"ad_name": "Frameless Glass",
			"script": "While you wait, ask us about our new frameless glass entrances, fitted in a week.",
			"tone": "Radio Ad",
		},
	)
	_make(
		"Display Channel",
		CHANNEL,
		{
			"channel_name": CHANNEL,
			"description": "The screen in the showroom's lobby",
			"slide_playlist": "Showroom",
			"widget_collection": CHANNEL,
			"programme": [{"plays": "Screensaver", "days": "Every Day", "from_time": "22:00:00", "to_time": "07:00:00"}],
		},
	)
	# what the showroom hears: its music, an ad, and the queue's calls (D6)
	_make(
		"Sound Zone",
		ZONE,
		{
			"zone_name": ZONE,
			"description": "The lobby's speakers",
			"music_playlist": MUSIC,
			"announce": 1,
			"programme": [{"plays": "Muted", "days": "Every Day", "from_time": "22:00:00", "to_time": "07:00:00"}],
			"ads": [{"voice_ad": "Frameless Glass", "plays": "Every Few Minutes", "every": 20}],
		},
	)
	if not frappe.db.get_value("Queue", QUEUE, "sound_zone"):
		frappe.db.set_value("Queue", QUEUE, "sound_zone", ZONE)
	_make(
		"Display Channel",
		KIOSK,
		{"channel_name": KIOSK, "description": "The kiosk at the showroom's door", "widget_collection": KIOSK},
	)
	_make(
		"Display Channel",
		WORKSHOP,
		{
			"channel_name": WORKSHOP,
			"description": "The screen over the workshop's benches",
			"widget_collection": WORKSHOP,
			"programme": [{"plays": "Screen Off", "days": "Every Day", "from_time": "20:00:00", "to_time": "06:00:00"}],
		},
	)


def _track() -> str:
	"""Twenty-four seconds of soft chords, made here so the demo carries no
	recording of anybody's: a public file, as a screen fetches it."""
	rate, chords = 16000, ((220.0, 277.18, 329.63), (196.0, 246.94, 293.66), (174.61, 220.0, 261.63), (196.0, 246.94, 293.66))
	out = io.BytesIO()
	with wave.open(out, "wb") as sound:
		sound.setnchannels(1)
		sound.setsampwidth(2)
		sound.setframerate(rate)
		frames = bytearray()
		for chord in chords:
			for i in range(rate * 6):
				fade = min(1.0, i / 4000, (rate * 6 - i) / 4000)
				value = sum(math.sin(2 * math.pi * pitch * i / rate) for pitch in chord) / len(chord)
				frames += struct.pack("<h", int(value * fade * 6000))
		sound.writeframes(bytes(frames))
	return frappe.get_doc(
		{"doctype": "File", "file_name": "morning-glass.wav", "content": out.getvalue(), "is_private": 0, "folder": "Home"}
	).insert().file_url


def _paired():
	"""Screens on the list as if somebody had paired them and not switched
	them on yet: each keeps a token nobody holds, so none can be played."""
	from onedesk.one_display.screens import _hash

	for screen_name, channel, rotate, zone in SCREENS:
		if frappe.db.exists("Display Screen", {"screen_name": screen_name}):
			continue
		frappe.get_doc(
			{
				"doctype": "Display Screen",
				"screen_name": screen_name,
				"channel": channel,
				"rotate": rotate,
				"sound_zone": zone,
				"status": "Paired",
				"token_hash": _hash(secrets.token_urlsafe(32)),
				"device": "Paired in the demo",
			}
		).insert(ignore_permissions=True)


def _showroom() -> None:
	"""The lobby's slides, a presentation of three filed on the playlist."""
	from onedesk.one_slide import api, convert

	file = api.make_with(
		"@records/Slide Playlist/Showroom", "Showroom slides", [convert.slide(_design(*one)) for one in SLIDES]
	)
	playlist = frappe.get_doc("Slide Playlist", "Showroom")
	playlist.append("slides", {"kind": "Presentation", "presentation": file, "title": "Showroom slides", "duration": 12})
	playlist.save()


def _design(ground: str, eyebrow: str, title: str, line: str) -> dict:
	"""A showroom slide as OneDisplay's blocks, as OneAI designs one, for
	one_slide/convert.py to draw as a presentation's slide."""
	text = {"kind": "text", "colour": "#ffffff", "align": "start", "x": 6, "w": 54}
	return {
		"orientation": "Landscape",
		"background": ground,
		"blocks": [
			{"kind": "shape", "x": 6, "y": 27, "w": 5, "h": 0.8, "fill": "#ffffff", "radius": 4, "opacity": 0.8},
			{**text, "y": 30, "h": 6, "text": eyebrow, "size": 34, "weight": 600, "upper": 1, "spacing": 0.18},
			{**text, "y": 38, "h": 28, "text": title, "size": 112, "weight": 700, "line": 1.05},
			{**text, "y": 68, "h": 14, "text": line, "size": 40, "weight": 400, "line": 1.3},
		],
	}


def _widget(kind, x, y, w, h, source=None, settings=None, mapping=None) -> dict:
	return {
		"widget_type": kind,
		"x": x,
		"y": y,
		"w": w,
		"h": h,
		"source": source,
		"settings": json.dumps(settings or {}),
		"mapping": json.dumps(mapping or {}),
	}


# (service, counter that served it, how it ended)
MORNING = (
	("Showroom Visit", "1", "Done"),
	("Payments", "2", "Done"),
	("Collections", "2", "No Show"),
	("Showroom Visit", "1", "Called"),
	("Showroom Visit", None, "Waiting"),
	("Payments", None, "Waiting"),
)


def _morning():
	from onedesk.one_display import queue as queues

	if frappe.db.exists("Queue Ticket", {"queue": QUEUE}):
		return
	for service, counter, status in MORNING:
		ticket = queues.take(QUEUE, service)
		if not counter:
			continue
		name = frappe.db.get_value("Queue Ticket", {"queue": QUEUE, "ticket": ticket["ticket"], "status": "Waiting"})
		queues._call(name, counter)
		if status != "Called":
			frappe.db.set_value("Queue Ticket", name, "status", status)
