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
def onedisplay_plays_a_presentation():
	"""The showroom's playlist plays a presentation from OneCloud: each of its
	slides reaches a screen as the editor's elements, its own time or the
	row's, and a picture on it at an address only the site can seal. A row
	that was a picture, a video or a designed slide becomes a presentation
	(the patch), and a row may only play what its maker may open."""
	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one_display import programme
	from onedesk.one_display.patches import presentations_on_screens as patch
	from onedesk.one_slide import api, play

	dot = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
	channel = frappe.get_doc("Display Channel", CHANNEL)
	row = frappe.get_doc("Slide Playlist", channel.slide_playlist).slides[0]
	held = api.presentation_of(frappe.db.get_value("File", row.presentation, "file_url"))
	was = getattr(frappe.local, "request", None)
	frappe.db.savepoint("onedisplay_presentation")
	try:
		with as_user(OWNER):
			assert any(found[0] == row.presentation for found in api.search("File", frappe.db.get_value("File", row.presentation, "file_name")[:6], "name", 0, 20)), "the playlist's presentation is offered"
			picture = api.save_base64_image(dot, held, "picture")
			doc = frappe.get_doc("Presentation", held)
			elements = json.loads(doc.slides[0].elements)
			elements.append({"id": "pic", "type": "image", "src": picture, "left": 700, "top": 40, "width": 200, "height": 120, "zIndex": 9})
			elements.append({"id": "gone", "type": "text", "content": "<p>Hidden</p>", "hidden": True, "left": 0, "top": 0})
			doc.slides[0].elements = json.dumps(elements)
			doc.save(ignore_permissions=True)
		shown = programme.slides(channel.slide_playlist)["slides"]
		assert len(shown) == 3 and all(one["kind"] == "Slide" and one["ms"] == 12000 for one in shown), shown
		first = shown[0]["slide"]["elements"]
		sealed = next(one["src"] for one in first if one["id"] == "pic")
		assert sealed.startswith(play.SHOWN) and "&sig=" in sealed and not any(one["id"] == "gone" for one in first), first
		assert any(one["type"] == "text" and "Frameless" in one["content"] for one in first), "the slide's words reach the screen"
		file_id, sig = sealed[len(play.SHOWN) :].split("&sig=")
		with as_user("Guest"):
			frappe.local.request = Request(EnvironBuilder(path="/api/method/onedesk.one_slide.api.shown", method="GET").get_environ())
			api.shown(file_id, sig)
			assert frappe.local.response.status_code == 200, "a screen fetches the picture as nobody"
			frappe.local.response = frappe._dict()
			try:
				api.shown(file_id, "0" * 32)
				raise AssertionError("a guessed seal fetches a picture")
			except frappe.DoesNotExistError:
				frappe.clear_messages()
		old = frappe._dict(parent=channel.slide_playlist, kind="Image", file="/files/lobby.jpg", title="Lobby")
		assert [one["type"] for one in patch.slide(old)["elements"]] == ["image"]
		assert patch.slide(frappe._dict(old, kind="Video", file="/files/lobby.mp4"))["elements"][0]["type"] == "video"
		designed = patch.slide(frappe._dict(old, kind="Design", design=json.dumps({"background": "#0e6e8c", "blocks": [{"kind": "text", "text": "Fitted", "x": 6, "y": 6, "w": 50, "h": 20}]})))
		assert designed["background"] == "#0E6E8CFF" and "Fitted" in designed["elements"][0]["content"], designed
		assert "script" not in patch.slide(frappe._dict(old, kind="Design", design=None, html="<p>Hi<script>x</script></p>"))["elements"][0]["content"]
		with as_user(OWNER):
			playlist = frappe.get_doc("Slide Playlist", channel.slide_playlist)
			playlist.append("slides", {"kind": "Presentation", "presentation": frappe.db.get_value("File", {"is_folder": 0, "file_url": ["not like", f"{api.URL}%"]})})
			try:
				playlist.save()
				raise AssertionError("a row plays a file that is not a presentation")
			except frappe.ValidationError:
				frappe.clear_messages()
	finally:
		frappe.local.request = was
		frappe.db.rollback(save_point="onedisplay_presentation")


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
	widget moved, its sources offer their fields, and OneAI's widget and
	recording come back as things to keep: the widget's code without its
	fences, and a recording on the ad."""
	from onedesk.one_display import layout, make, sources, voices
	from onedesk.one_display.demo import WORKSHOP

	pcm = base64.b64encode(b"\x00\x01" * 1600).decode()
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
			side_effect=lambda job, text, reference=None, voice=None: {"data": pcm, "mime": "audio/L16;rate=16000"},
		), mock.patch("onedesk.one_ai.run.once", return_value="```html\n<div>Fitted in a week</div>\n```"):
			assert make.widget("The late tasks as cards", rows=json.dumps([{"subject": "Snag list"}])) == "<div>Fitted in a week</div>"
			recording = voices.record("Frameless Glass")
			assert recording.endswith(".wav") and frappe.db.get_value("Voice Ad", "Frameless Glass", "audio") == recording


@check
def onedisplay_builds_a_screen_in_oneslide():
	"""The workshop's screen opens in OneSlide's editor as its backdrop, made
	once: its widgets are on the one slide as widget elements at their
	places. Saving a moved clock and a heading keeps the clock's row, by its
	id, ten percent further left, and the heading in the backdrop, which the
	screen draws under the widgets (stage 7 of docs/ONESLIDE.md)."""
	from onedesk.one_display import layout, programme, screen
	from onedesk.one_display.demo import WORKSHOP
	from onedesk.one_slide import api

	frappe.db.savepoint("screen_check")
	try:
		with as_user(OWNER):
			made = screen.backdrop(WORKSHOP)["presentation"]
			assert screen.backdrop(WORKSHOP)["presentation"] == made, "a collection has one backdrop"
			rows = layout.get(WORKSHOP)["widgets"]
			doc = api.get(made)
			assert doc["screen"]["name"] == WORKSHOP and len(doc["slides"]) == 1
			slide = doc["slides"][0]
			elements = json.loads(slide["elements"])
			placed = [one for one in elements if one["type"] == "widget"]
			assert len(placed) == len(rows), (len(placed), len(rows))
			clock = next(one for one in placed if one["widget"]["widget_type"] == "Clock")
			was = next(row["x"] for row in rows if row["id"] == clock["widget"]["id"])
			clock["left"] -= 96
			elements.append({"id": "heading", "type": "text", "left": 40, "top": 400, "width": 400, "zIndex": 1, "content": "<p>Fitted in a week</p>"})
			kept = {key: slide.get(key) for key in api.SLIDE_FIELDS if key in slide}
			api.save_slides(made, json.dumps([{**kept, "elements": json.dumps(elements)}]), doc["modified"])
			after = layout.get(WORKSHOP)["widgets"]
			assert len(after) == len(rows), "no widget is lost or doubled"
			moved = next(row for row in after if row["id"] == clock["widget"]["id"])
			assert abs(moved["x"] - (was - 10)) < 0.01, (was, moved["x"])
			stored = json.loads(frappe.get_doc(api.PRESENTATION, made).slides[0].elements)
			assert [one["id"] for one in stored] == ["heading"], "the backdrop keeps no widget of its own"
			frappe.clear_document_cache("Widget Collection", WORKSHOP)
			drawn = programme.layout(WORKSHOP, "en")["backdrop"]
			assert drawn["bare"] and [one["id"] for one in drawn["elements"]] == ["heading"], drawn
	finally:
		frappe.db.rollback(save_point="screen_check")


@check
def onedisplay_makes_music_in_the_background():
	"""A song is made, kept as a public file and added to its playlist paused,
	with its length read from the file, and whoever asked is told; a failure
	adds nothing and says so. Videos are made in a presentation now
	(oneai_makes_slides_and_pictures)."""
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
	tracks = frappe.get_doc("Display Channel", CHANNEL).music_playlist
	assert tracks, "the showroom channel has music"
	told = []
	with as_user(OWNER), mock.patch("onedesk.one.apps.ai_on", return_value=True), mock.patch(
		"onedesk.one_ai.run.make", side_effect=lambda job, text, reference=None, voice=None: {"data": song, "mime": "audio/wav"}
	), mock.patch("onedesk.one_display.tell.notify.notify", lambda name, users, **context: told.append((name, list(users)))):
		with mock.patch("frappe.enqueue") as queued:
			assert make.music(tracks, "Calm piano for a showroom")["begun"] and queued.call_args.kwargs["what"] == "music"
			assert queued.call_args.kwargs["asker"] == OWNER
		make.made_later("music", tracks, "Calm piano for a showroom", OWNER)
		track = frappe.get_doc("Music Playlist", tracks).tracks[-1]
		assert track.paused and track.duration == 3.0 and track.file.endswith(".wav"), track.as_dict()
		assert told[-1] == ("Made by OneAI", [OWNER]), told
		with mock.patch("onedesk.one_ai.run.make", side_effect=frappe.ValidationError("no")):
			make.made_later("music", tracks, "Something that fails", OWNER)
		assert told[-1] == ("Not Made by OneAI", [OWNER]) and frappe.get_doc("Music Playlist", tracks).tracks[-1].name == track.name
		music = frappe.get_doc("Music Playlist", tracks)
		music.set("tracks", music.tracks[:-1])
		music.save()
