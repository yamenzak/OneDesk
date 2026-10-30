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
		), mock.patch("onedesk.one_ai.run.once", side_effect=lambda job, text, reference=None: "```html\n<div>Fitted in a week</div>\n```"):
			picture = make.picture("A glass shopfront at dusk")
			assert picture.startswith("/files/") and not frappe.db.get_value("File", {"file_url": picture}, "is_private")
			assert make.design("Our frameless glass, fitted in a week") == "<div>Fitted in a week</div>"
			assert make.widget("The late tasks as cards", rows=json.dumps([{"subject": "Snag list"}])) == "<div>Fitted in a week</div>"
			recording = voices.record("Frameless Glass")
			assert recording.endswith(".wav") and frappe.db.get_value("Voice Ad", "Frameless Glass", "audio") == recording
