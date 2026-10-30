"""OneDisplay's part of the integration suite (one_demo/check.py runs it): a
screen paired from its code, the showroom queue worked from the kiosk to a
counter and onto the board, a screen told what to do, an alert and who hears
of it, a silent screen reported, the lobby's sources, and OneAI's reads."""

import base64
import json
from contextlib import contextmanager
from unittest import mock

import frappe
from frappe.utils import add_to_date, now_datetime

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check
from onedesk.one_demo.people import OWNER
from onedesk.one_display.demo import CHANNEL, KIOSK, QUEUE


@contextmanager
def _told():
	"""What tell.py hands notify, as (type, people, context), since notify
	writes the bell in the background."""
	said = []
	with mock.patch("onedesk.one_display.tell.notify.notify", lambda name, users, **context: said.append((name, list(users), context))):
		yield said


def _widget(said: dict, kind: str) -> dict:
	return next(one for one in said["layout"]["widgets"] if one["type"] == kind)


@check
def onedisplay_pairs_a_screen_and_runs_the_queue():
	"""A kiosk hung on its side is paired from the code it shows and given its
	token once; its kiosk widget hands out a ticket, which Omar calls, calls
	again and closes while the lobby's board shows it; Layla mutes the kiosk
	and sends every screen an alert, which Omar is told of, then ends it."""
	from onedesk.one_display import queue, screens

	with as_user("Guest"):
		started = screens.start("check")
		assert screens.status(started["screen"], started["secret"]) == {"code": started["code"]}
		assert screens.status(started["screen"], "a guess") == {"gone": 1}
	with as_user(OWNER):
		screen = screens.pair(started["code"], "Door Kiosk", KIOSK, 90)
	try:
		with as_user("Guest"):
			token = screens.status(started["screen"], started["secret"])["token"]
			assert screens.status(started["screen"], started["secret"]) == {"gone": 1}, "the token is given once"
			assert screens.state(screen, "a guess") == {"gone": 1}
			said = screens.state(screen, token)
			assert said["screen"]["rotate"] == 90 and said["channel"]["name"] == KIOSK, said["screen"]
			light = screens.state(screen, token, have=said["channel"]["revision"])["channel"]
			assert "layout" not in light, "a screen that has the channel is not sent it again"
			kiosk = _widget(said["channel"], "Kiosk")
			board = kiosk["data"]["whole"]
			assert [one["service"] for one in board["services"]] == ["Showroom Visit", "Collections", "Payments"], board
			ticket = screens.take(screen, token, kiosk["id"], "Collections")
			assert ticket["ticket"].startswith("B"), ticket
			try:
				screens.take(screen, token, "no such widget", "Collections")
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("a screen hands out tickets only from its own kiosk widget")
		with as_user("omar@one.test"):
			desk = next(one for one in queue.desks() if one["queue"] == QUEUE)
			assert desk["mine"] == "2", desk
			served = queue.call_next(QUEUE, "2", service="Collections")["serving"]
			assert served["ticket"] == ticket["ticket"], served
			again = queue.recall(served["name"])["serving"]
			assert again["calls"] == 2, again
		with as_user(OWNER):
			lobby = screens.preview(channel=CHANNEL)["channel"]
			called = _widget(lobby, "Queue Board")["data"]["whole"]["called"]
			mine = next(one for one in called if one["ticket"] == ticket["ticket"])
			assert mine["counter"] == "2" and mine["say"], mine
		with as_user("omar@one.test"):
			assert queue.finish(served["name"], "No Show")["serving"] is None
			assert queue.counter_state(QUEUE, "2")["serving"] is None
		with as_user(OWNER):
			lobby = screens.preview(channel=CHANNEL)["channel"]
			called = _widget(lobby, "Queue Board")["data"]["whole"]["called"]
			assert ticket["ticket"] not in [one["ticket"] for one in called], "a closed ticket leaves the board"
			screens.control(screen, "mute")
			with _told() as said:
				screens.alert("Please leave the building by the nearest exit.")
			assert said and said[0][0] == "Emergency Alert Sent", said
			assert OWNER not in said[0][1], "whoever sent the alert is not told of it"
		with as_user("omar@one.test"):
			try:
				screens.alert("")
			except frappe.PermissionError:
				pass
			else:
				raise AssertionError("a counter's user may not end an alert")
		with as_user("Guest"):
			said = screens.state(screen, token)
			assert said["screen"]["muted"] == 1 and said["command"]["name"] == "mute", said["screen"]
			assert said["alert"] == "Please leave the building by the nearest exit."
		with as_user(OWNER):
			screens.alert("")
		with as_user("Guest"):
			assert screens.state(screen, token)["alert"] is None
	finally:
		frappe.delete_doc("Display Screen", screen, ignore_permissions=True, force=True)


@check
def onedisplay_reports_a_silent_screen_once():
	"""A screen not heard from for ten minutes is told to whoever runs
	OneDisplay, once, and a screen turned off is not."""
	from onedesk.one_display import screens, tell

	with as_user("Guest"):
		started = screens.start("check")
	with as_user(OWNER):
		screen = screens.pair(started["code"], "Back Office", CHANNEL)
	try:
		frappe.db.set_value("Display Screen", screen, "last_seen", add_to_date(now_datetime(), minutes=-30), update_modified=False)
		frappe.cache.delete_value(tell.TOLD.format(screen))

		def reported() -> list:
			with _told() as said:
				tell.offline()
			return [one for one in said if one[2].get("record") == ("Display Screen", screen)]

		first = reported()
		assert first and OWNER in first[0][1], f"a silent screen is reported to whoever runs OneDisplay: {first}"
		assert not reported(), "once for each time it goes quiet"
		frappe.db.set_value("Display Screen", screen, "dark", 1, update_modified=False)
		frappe.cache.delete_value(tell.TOLD.format(screen))
		assert not reported(), "a screen turned off is not reported"
	finally:
		frappe.delete_doc("Display Screen", screen, ignore_permissions=True, force=True)


@check
def onedisplay_tells_the_counters_of_a_long_wait():
	"""A ticket waiting past the showroom's fifteen minutes is told once to
	whoever staffs its counters; the socket admits a screen only by its
	token."""
	from onedesk.one_display import live, queue, screens, tell

	ticket = queue.take(QUEUE, "Payments")
	name = frappe.db.get_value("Queue Ticket", {"queue": QUEUE, "ticket": ticket["ticket"], "ticket_date": frappe.utils.today()})
	try:
		frappe.db.set_value("Queue Ticket", name, "creation", add_to_date(now_datetime(), minutes=-20), update_modified=False)

		def told() -> list:
			with _told() as said:
				tell.long_waits()
			return [one for one in said if one[2].get("record") == ("Queue Ticket", name)]

		first = told()
		staff = {row.user for row in frappe.get_doc("Queue", QUEUE).counters if row.user}
		assert first and set(first[0][1]) == staff and first[0][2]["minutes"] >= 20, first
		assert not told(), "a long wait is told once"
	finally:
		frappe.delete_doc("Queue Ticket", name, ignore_permissions=True, force=True)
		frappe.cache.delete_value(tell.TOLD.format(f"wait:{name}"))
	with as_user("Guest"):
		started = screens.start("check")
	with as_user(OWNER):
		screen = screens.pair(started["code"], "Socket Check", CHANNEL)
	try:
		with as_user("Guest"):
			token = screens.status(started["screen"], started["secret"])["token"]
			assert live.admit(screen, "a guess") == {"ok": False}
			assert live.ROOM.format(screen) in live.admit(screen, token)["rooms"]
	finally:
		frappe.delete_doc("Display Screen", screen, ignore_permissions=True, force=True)


@check
def onedisplay_designs_a_slide_on_its_canvas():
	"""The showroom's slides open in the designer as blocks with every
	property the schema declares; one changed and saved is kept as typed and
	reaches a screen as blocks, never as HTML; what the server will not keep
	(an outside picture, a colour that is not one, CSS that loads something,
	a kind it does not know) is dropped; a QR code is drawn by the server."""
	from onedesk.one_display import blocks, programme, slides

	with as_user(OWNER):
		held = slides.get("Showroom")
		assert set(held["schema"]["kinds"]) == set(blocks.KINDS) and held["schema"]["properties"]["rotate"]["label"]
		first = held["slides"][0]
		title = next(one for one in first["design"]["blocks"] if one["kind"] == "text" and one["size"] >= 100)
		assert {"rotate", "shadow_colour", "font", "valign", "css"} <= set(title), title
		was = dict(title)
		title.update(text="Glass <script>alert(1)</script> entrances", rotate=-4, shadow_colour="#00000080", css="text-shadow: 0 4px 24px black; background: url(https://example.com/x.png)")
		first["design"]["blocks"].append({"kind": "qr", "id": "visit", "x": 80, "y": 70, "w": 12, "h": 20, "link": "https://example.com/visit"})
		try:
			saved = slides.save("Showroom", json.dumps(held["slides"]))
			row = saved["slides"][0]
			kept = next(one for one in row["design"]["blocks"] if one["id"] == title["id"])
			assert kept["text"].startswith("Glass <script>") and kept["rotate"] == -4 and kept["css"] == "text-shadow: 0 4px 24px black", kept
			assert not frappe.db.get_value("Display Slide", row["id"], "html"), "a designed slide keeps no HTML of its own"
			channel = frappe.get_doc("Display Channel", CHANNEL)
			shown = programme.slides(channel.slide_playlist)["slides"][0]
			assert shown["design"]["blocks"] and "html" not in shown and shown["qrs"]["https://example.com/visit"].startswith("<svg"), shown.keys()
		finally:
			title.clear()
			title.update(was)
			first["design"]["blocks"].pop()
			slides.save("Showroom", json.dumps(held["slides"]))
		assert slides.qr("https://example.com/visit").startswith("<svg")
		cleaned = slides.clean(
			{
				"background": "red; x",
				"blocks": [
					{"kind": "image", "src": "https://example.com/a.png", "stroke_colour": "blue", "rotate": 9000},
					{"kind": "shape", "shape": "hexagon", "fill": "#12345678"},
					{"kind": "script"},
				],
			}
		)
		image, shape = cleaned["blocks"]
		assert cleaned["background"] == blocks.GROUND and len(cleaned["blocks"]) == 2, cleaned
		assert image["src"] == "" and image["stroke_colour"] == "#ffffff" and image["rotate"] == 360, image
		assert shape["shape"] == "rectangle" and shape["fill"] == "#12345678", shape


@check
def onedisplay_fills_the_lobby_from_its_sources():
	"""The lobby plays its slides and widgets, the projects figure reads as
	the person who saved it, the night plays the screensaver, and OneAI reads
	the queue and the screens and suggests a voice ad."""
	from onedesk.one_display import ai, programme, sources

	with as_user(OWNER):
		lobby = programme.compose(CHANNEL)
		assert len(lobby["slides"]["slides"]) == 3, lobby["slides"]
		number = _widget(lobby, "Number")["data"]["rows"]
		assert number and int(number[0]["value"]) > 0, number
		assert sources.peek("Projects Underway")
		channel = frappe.get_doc("Display Channel", CHANNEL)
		night = now_datetime().replace(hour=23, minute=15)
		assert programme.plays(channel, night)["mode"] == "screensaver", "the lobby sleeps at night"
		rates = {row["currency"]: row for row in sources.read("Exchange Rates")}
		assert set(rates) == {"USD", "EUR", "GBP"} and rates["USD"]["base"] == frappe.get_cached_value("Company", frappe.db.get_default("company"), "default_currency"), rates
		assert ai.queue_now(QUEUE)["queues"][0]["waiting"]
		assert isinstance(ai.screens_now()["screens"], list)
		assert ai.plan_voice_ad("Summer Sale", "Ask us about our summer prices.")["state"] == "Proposed"


@check
def onedisplay_lays_out_a_collection_and_asks_oneai():
	"""The workshop's layout is read and saved back by the editor with one
	widget moved, its sources offer their fields, and OneAI's picture, slide,
	widget and recording come back as things to keep: a public picture, the
	slide's code without its fences, and a recording on the ad."""
	from onedesk.one_display import layout, make, sources, voices
	from onedesk.one_display.demo import WORKSHOP

	pcm = base64.b64encode(b"\x00\x01" * 1600).decode()
	designed = "```json\n" + json.dumps({"background": "#0e6e8c", "blocks": [{"kind": "text", "x": 6, "y": 30, "w": 60, "h": 20, "text": "Fitted in a week", "size": 96}]}) + "\n```"
	pixel = base64.b64encode(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")).decode()
	with as_user(OWNER):
		held = layout.get(WORKSHOP)
		assert held["writable"] and {one["type"] for one in held["types"]} >= {"Queue Board", "Weather", "Custom"}
		clock = next(one for one in held["widgets"] if one["widget_type"] == "Clock")
		was = clock["x"]
		clock["x"] = 70
		saved = layout.save(WORKSHOP, json.dumps(held["widgets"]))
		assert next(one for one in saved["widgets"] if one["id"] == clock["id"])["x"] == 70, "the editor keeps a row by its id"
		clock["x"] = was
		layout.save(WORKSHOP, json.dumps(held["widgets"]))
		assert any(one["fieldname"] == "subject" for one in layout.fields("Late Tasks"))
		assert any(one["fieldname"] == "status" for one in sources.fields_of("Project"))
		assert any(one["fieldname"] == "subject" for one in sources.report_fields("Delayed Tasks Summary"))
		with mock.patch("onedesk.one.apps.ai_on", return_value=True), mock.patch(
			"onedesk.one_ai.run.make",
			side_effect=lambda job, text, reference=None, voice=None: {"data": pcm, "mime": "audio/L16;rate=16000"}
			if job == "display_voice"
			else {"data": pixel, "mime": "image/png"},
		), mock.patch("onedesk.one_ai.run.once", side_effect=lambda job, text, reference=None: designed if job == "display_design" else "```html\n<div>Fitted in a week</div>\n```"):
			picture = make.picture("A glass shopfront at dusk")
			assert picture.startswith("/files/") and not frappe.db.get_value("File", {"file_url": picture}, "is_private")
			made = make.design("Our frameless glass, fitted in a week")
			assert made["design"]["blocks"][0]["text"] == "Fitted in a week" and made["design"]["blocks"][0]["font"] == "sans", made
			assert make.widget("The late tasks as cards", rows=json.dumps([{"subject": "Snag list"}])) == "<div>Fitted in a week</div>"
			recording = voices.record("Frameless Glass")
			assert recording.endswith(".wav") and frappe.db.get_value("Voice Ad", "Frameless Glass", "audio") == recording


@check
def onedisplay_makes_a_video_and_music_in_the_background():
	"""A video is begun and collected, a song made, each kept as a public
	file and added to its playlist paused, with the song's length read from
	the file, and whoever asked is told; a failure adds nothing and says so."""
	import io
	import wave

	from onedesk.one_display import make

	sound = io.BytesIO()
	with wave.open(sound, "wb") as written:
		written.setnchannels(1)
		written.setsampwidth(2)
		written.setframerate(8000)
		written.writeframes(b"\x00\x00" * 8000 * 3)
	song = base64.b64encode(sound.getvalue()).decode()
	film = base64.b64encode(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 64).decode()
	channel = frappe.get_doc("Display Channel", CHANNEL)
	slides, tracks = channel.slide_playlist, channel.music_playlist
	assert slides and tracks, "the showroom channel has slides and music"
	asked = []
	told = []
	with as_user(OWNER), mock.patch("onedesk.one.apps.ai_on", return_value=True), mock.patch("onedesk.one_display.make.time.sleep"), mock.patch(
		"onedesk.one_ai.run.begin", side_effect=lambda job, text, reference=None, orientation=None: asked.append((job, orientation)) or "ticket-1"
	), mock.patch(
		"onedesk.one_ai.run.collect", side_effect=[{"done": False}, {"done": True, "data": film, "mime": "video/mp4"}]
	), mock.patch(
		"onedesk.one_ai.run.make", side_effect=lambda job, text, reference=None, voice=None: {"data": song, "mime": "audio/wav"}
	), mock.patch("onedesk.one_display.tell.notify.notify", lambda name, users, **context: told.append((name, list(users)))):
		with mock.patch("frappe.enqueue") as queued:
			assert make.video(slides, "Sunlight through a frameless glass door")["begun"]
			assert queued.call_args.kwargs["what"] == "video" and queued.call_args.kwargs["asker"] == OWNER
			assert make.music(tracks, "Calm piano for a showroom")["begun"] and queued.call_args.kwargs["what"] == "music"
		before = len(frappe.get_doc("Slide Playlist", slides).slides)
		make.made_later("video", slides, "Sunlight through a frameless glass door", OWNER)
		made = frappe.get_doc("Slide Playlist", slides).slides
		assert len(made) == before + 1 and made[-1].kind == "Video" and made[-1].paused and made[-1].file.endswith(".mp4"), made[-1].as_dict()
		assert asked == [("display_video", "Landscape")] and told[-1] == ("Made by OneAI", [OWNER]), (asked, told)
		make.made_later("music", tracks, "Calm piano for a showroom", OWNER)
		track = frappe.get_doc("Music Playlist", tracks).tracks[-1]
		assert track.paused and track.duration == 3.0 and track.file.endswith(".wav"), track.as_dict()
		with mock.patch("onedesk.one_ai.run.make", side_effect=frappe.ValidationError("no")):
			make.made_later("music", tracks, "Something that fails", OWNER)
		assert told[-1] == ("Not Made by OneAI", [OWNER]) and frappe.get_doc("Music Playlist", tracks).tracks[-1].name == track.name
		playlist = frappe.get_doc("Slide Playlist", slides)
		playlist.set("slides", playlist.slides[:-1])
		playlist.save()
		music = frappe.get_doc("Music Playlist", tracks)
		music.set("tracks", music.tracks[:-1])
		music.save()
