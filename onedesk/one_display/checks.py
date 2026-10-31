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
	from onedesk.one_display import programme, queue, screens

	with as_user("Guest"):
		started = screens.start("check")
		waiting = screens.status(started["screen"], started["secret"])
		assert waiting["code"] == started["code"] and "<svg" in waiting["qr"], "a waiting screen shows its code and a code to scan"
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
			assert mine["counter"] == "2", mine
			# the call is said in the queue's sound zone (D6), not by the board
			said = programme.heard(frappe.db.get_value("Queue", QUEUE, "sound_zone"))["calls"]
			mine = next(one for one in said if one["ticket"] == ticket["ticket"])
			assert mine["say"] and mine["start"] > programme.now_ms() - 600000, mine
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
def onedisplay_hears_what_a_screen_is():
	"""A paired screen says its pixels and memory once a minute; a page past
	most of its memory, or one restarted three times today for no reason it
	gave, is shown at risk, and a nightly fresh start is not counted."""
	from onedesk.one_display import programme, screens

	with as_user("Guest"):
		started = screens.start("check")
	with as_user(OWNER):
		screen = screens.pair(started["code"], "Report Check", CHANNEL)
	try:
		with as_user("Guest"):
			token = screens.status(started["screen"], started["secret"])["token"]
			said = {"boot": "a", "why": "start", "w": 1920, "h": 1080, "dpr": 2, "mem": 4, "heap": 50 * screens.MB, "limit": 1000 * screens.MB, "ua": "TV"}
			assert screens.state(screen, token, report=json.dumps(said))["channel"]["reload_at"] == 4 * 60
			row = frappe.db.get_value("Display Screen", screen, ["pixels", "memory_gb", "at_risk", "restarts_today", "device"], as_dict=True)
			assert row.pixels == "1920 × 1080 · 2x" and row.memory_gb == 4 and not row.at_risk and row.device == "TV", row
			for boot, why in (("b", "nightly"), ("c", "unexpected"), ("d", "unexpected")):
				screens.state(screen, token, report=json.dumps({**said, "boot": boot, "why": why}))
			row = frappe.db.get_value("Display Screen", screen, ["at_risk", "restarts_today", "risk"], as_dict=True)
			assert row.restarts_today == 3 and row.at_risk and "3" in row.risk, row
			screens.state(screen, token, report=json.dumps({**said, "boot": "d", "heap": 900 * screens.MB}))
			risk = frappe.db.get_value("Display Screen", screen, "risk")
			assert "90%" in risk, risk
		assert programme._minutes("23:30:00") == 23 * 60 + 30 and programme._minutes(None) is None
	finally:
		frappe.delete_doc("Display Screen", screen, ignore_permissions=True, force=True)


@check
def onedisplay_draws_any_size_and_pictures_as_sharp_as_the_screen():
	"""A screen of any shape: a bar over a counter is drawn on its own frame,
	and Custom keeps its width and height in bounds. A picture larger than
	the largest screen showing it is copied once at that size, the original
	kept, and the copy goes when the picture does."""
	import base64
	import io
	import os

	from PIL import Image
	from werkzeug.test import EnvironBuilder
	from werkzeug.wrappers import Request

	from onedesk.one_display import programme, sizes
	from onedesk.one_slide import api, play, sized

	assert sizes.pixels({"screen_size": "Bar"}) == (1920, 540) and sizes.editor({"screen_size": "Wall"}) == (1920, 540)
	assert sizes.pixels({"screen_size": "Custom", "width": 99999, "height": 10}) == (sizes.LARGEST, sizes.SMALLEST)
	assert sized.bucket(1281) == 1920 and sized.bucket(9000) == 7680 and programme._longest("1920 × 1080 · 2x") == 3840
	channel = frappe.get_doc("Display Channel", CHANNEL)
	frappe.db.savepoint("onedisplay_sizes")
	picture = None
	was = getattr(frappe.local, "request", None)
	try:
		channel.screen_size = "Bar"
		channel.save(ignore_permissions=True)
		said = programme.compose(CHANNEL)
		assert (said["width"], said["height"]) == (1920, 540) and channel.width == 1920 and channel.height == 540, said
		buffer = io.BytesIO()
		Image.new("RGB", (3000, 2000), "#0e6e8c").save(buffer, "PNG")
		row = frappe.get_doc("Slide Playlist", channel.slide_playlist).slides[0]
		held = api.presentation_of(frappe.db.get_value("File", row.presentation, "file_url"))
		with as_user(OWNER):
			src = api.save_base64_image("data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode(), held, "large")
		picture = src[len(play.MEDIA) :].split("&")[0]
		assert f"&edge={1920}" in play._shown(src, 1920) and "&edge" not in play._shown(src), "a screen asks for its size"
		sized.make(picture, 1920)
		copy = sized.served(picture, 1920)
		path = frappe.get_site_path(copy["path"])
		assert Image.open(path).size == (1920, 1280), Image.open(path).size
		assert os.path.exists(frappe.get_doc("File", picture).get_full_path()), "the original is kept"
		sized.make(picture, 3840)
		assert sized.served(picture, 3840) is None, "a picture never grows"
		with as_user("Guest"):
			frappe.local.request = Request(EnvironBuilder(path="/api/method/onedesk.one_slide.api.shown", method="GET").get_environ())
			sent = api.shown(picture, play.seal(picture), edge=1920)
			assert sent.status_code == 200 and Image.open(io.BytesIO(b"".join(sent.response))).size == (1920, 1280)
		frappe.delete_doc("File", picture, ignore_permissions=True, force=True)
		picture = None
		assert not os.path.exists(path), "the copy goes with the picture"
	finally:
		frappe.local.request = was
		if picture:
			frappe.delete_doc("File", picture, ignore_permissions=True, force=True)
		frappe.db.rollback(save_point="onedisplay_sizes")
		frappe.clear_document_cache("Display Channel", CHANNEL)


@check
def onedisplay_shows_data_and_media_without_the_editor():
	"""A screen's words can come from a Display Source and are refilled with
	it; a saved project makes the source that counts projects read again and
	wakes the screens; pictures dropped on a playlist each become a
	presentation of one slide."""
	import base64
	import io

	from PIL import Image

	from onedesk.one_display import live, playlist, programme, sources
	from onedesk.one_slide import api, data, play

	frappe.db.savepoint("onedisplay_data")
	made = []
	try:
		with as_user(OWNER):
			name = api.presentation_of(frappe.db.get_value("File", api.make_with("@records/Slide Playlist/Showroom", "Data Check", [{"elements": []}]), "file_url"))
			made.append(frappe.db.get_value(api.PRESENTATION, name, "file"))
			data.save_sources(name, [{"key": "projects", "kind": "rows", "source": "Projects Underway"}])
			doc = frappe.get_doc(api.PRESENTATION, name)
			doc.slides[0].elements = json.dumps([{"id": "t", "type": "text", "content": "<p>{projects.value} underway</p>", "left": 0, "top": 0, "width": 400}])
			doc.save(ignore_permissions=True)
			shown = data.evaluate(name)["values"]
			assert shown.get("projects.value"), shown
			drawn = play.for_screen(name, 10)[0]["slide"]["elements"][0]["content"]
			assert "{projects" not in drawn and "underway" in drawn, drawn
		assert programme.light({"revision": "r", "mode": "show", "muted": 0, "layout": {"widgets": [], "backdrop": {"live": 1, "elements": []}}})["backdrop"], "a backdrop with chips is sent with every answer"
		before = frappe.cache.get_value(sources.FRESH.format("Projects Underway"))
		frappe.cache.delete_value(live.READ)
		frappe.flags.one_display_woken = False
		with mock.patch("onedesk.one_display.live.wake") as woken:
			live.record_saved(frappe.get_doc("Project", frappe.get_all("Project", limit=1, pluck="name")[0]))
			live.record_saved(frappe.get_doc("Project", frappe.get_all("Project", limit=1, pluck="name")[0]))
		assert frappe.cache.get_value(sources.FRESH.format("Projects Underway")) != before and woken.call_count == 1, "one wake a request"
		buffer = io.BytesIO()
		Image.new("RGB", (64, 36), "#7c2d12").save(buffer, "PNG")
		with as_user(OWNER):
			upload = frappe.get_doc({"doctype": "File", "file_name": "lobby-photo.png", "content": buffer.getvalue(), "is_private": 1, "attached_to_doctype": "Slide Playlist", "attached_to_name": "Showroom"})
			upload.insert(ignore_permissions=True)
			added = playlist.add_media("Showroom", [upload.name])
			made += added
			row = frappe.get_doc("Slide Playlist", "Showroom").slides[-1]
			assert row.presentation == added[0] and row.title == "lobby-photo", row.as_dict()
			element = json.loads(frappe.get_doc(api.PRESENTATION, api.presentation_of(frappe.db.get_value("File", added[0], "file_url"))).slides[0].elements)[0]
			assert element["type"] == "image" and element["src"].startswith(play.MEDIA) and element["width"] > 900, element
			assert not frappe.db.exists("File", upload.name), "the upload is kept only inside its presentation"
	finally:
		frappe.flags.one_display_woken = False
		for file in made:
			held = api.presentation_of(frappe.db.get_value("File", file, "file_url") or "")
			if held and frappe.db.exists(api.PRESENTATION, held):
				frappe.delete_doc(api.PRESENTATION, held, ignore_permissions=True, force=True)
			if frappe.db.exists("File", file):
				frappe.delete_doc("File", file, ignore_permissions=True, force=True)
		frappe.db.rollback(save_point="onedisplay_data")
		frappe.clear_document_cache("Slide Playlist", "Showroom")


@check
def onedisplay_keeps_a_board():
	"""A board of the business's own items and states: an item set to a state
	and its value stepped, each change kept with how long the item was as it
	was; a screen reads it as a source; a state kept past its limit is told
	once; a board that names its people lets nobody else change it."""
	from onedesk.one_display import boards, sources, tell
	from onedesk.one_display import widgets as kinds

	frappe.db.savepoint("onedisplay_board")
	try:
		frappe.get_doc(
			{
				"doctype": "Display Board",
				"board_name": "Check Board",
				"value_label": "Count",
				"states": [{"state": "Ready", "colour": "#15803D"}, {"state": "Busy", "colour": "#B45309", "limit_minutes": 5}],
				"items": [{"item_name": "One"}, {"item_name": "Two"}],
			}
		).insert(ignore_permissions=True)
		with as_user(OWNER), mock.patch("onedesk.one_display.live.wake") as woken:
			assert "Check Board" in [one["board"] for one in boards.mine()]
			assert [one["item"] for one in boards.get("Check Board")["items"]] == ["One", "Two"]
			said = boards.change("Check Board", "One", state="Busy")
			one = next(row for row in said["items"] if row["item"] == "One")
			assert one["state"] == "Busy" and one["colour"] == "#B45309" and one["limit"] == 5 and woken.called, one
			boards.change("Check Board", "One", step=1)
			said = boards.change("Check Board", "One", step=1)
			assert next(row for row in said["items"] if row["item"] == "One")["value"] == "2", said
			try:
				boards.change("Check Board", "One", state="Nowhere")
				raise AssertionError("a state the board does not have")
			except frappe.ValidationError:
				frappe.clear_messages()
		kept = boards.history("Check Board", "One")
		assert [row.state for row in kept][-1] == "Busy" and kept[-1].was_state == "" and len(kept) == 3, kept
		frappe.get_doc({"doctype": "Display Source", "source_name": "Check Board", "kind": "Board", "board": "Check Board"}).insert(ignore_permissions=True)
		assert [row["item"] for row in sources.read("Check Board")] == ["One", "Two"]
		assert {"Board", "Board Item"} <= set(kinds.TYPES)
		row = next(row for row in frappe.get_doc("Display Board", "Check Board").items if row.item_name == "One")
		frappe.db.set_value("Display Board Item", row.name, "since", add_to_date(now_datetime(), minutes=-9))
		with _told() as said:
			tell.past_limits()
			tell.past_limits()
		told = [one for one in said if one[0] == "Past Its Time" and one[2]["item"] == "One"]
		assert len(told) == 1 and told[0][2]["minutes"] >= 9, said
		board = frappe.get_doc("Display Board", "Check Board")
		board.append("people", {"user": "Administrator"})
		board.save(ignore_permissions=True)
		frappe.clear_document_cache("Display Board", "Check Board")
		with as_user("Guest"):
			assert not boards.may("Check Board"), "a board that names its people lets nobody else change it"
		assert boards.codes("Check Board")[0]["svg"].startswith("<svg")
	finally:
		frappe.db.rollback(save_point="onedisplay_board")
		frappe.clear_document_cache("Display Board", "Check Board")


@check
def onedisplay_plays_sound_by_zone():
	"""A channel is only what is seen; the showroom's zone plays its music, ad
	and calls. A radio pairs to a zone and shows nothing; a radio without a
	zone is refused. A screen's video plays its own sound only when it says
	so, and the zone's music is quieter while it does. A zone's schedule may
	only change what is heard, and a channel's no longer plays music."""
	from onedesk.one_display import programme, screens

	zone = frappe.db.get_value("Queue", QUEUE, "sound_zone")
	heard = programme.heard(zone)
	assert heard["music"]["tracks"] and heard["announce"] and isinstance(heard["calls"], list), heard
	lobby = programme.compose(CHANNEL)
	assert not {"music", "ads", "announce"} & set(lobby), "a channel is only what is seen"
	with as_user("Guest"):
		started = screens.start("check", kind="Radio")
	with as_user(OWNER):
		try:
			screens.pair(started["code"], "Check Radio")
			raise AssertionError("a radio plays a zone")
		except frappe.ValidationError:
			frappe.clear_messages()
		radio = screens.pair(started["code"], "Check Radio", sound_zone=zone)
	try:
		with as_user("Guest"):
			token = screens.status(started["screen"], started["secret"])["token"]
			said = screens.state(radio, token)
			assert said["channel"] is None and said["sounds"]["name"] == heard["name"] and said["screen"]["kind"] == "Radio", said
	finally:
		frappe.delete_doc("Display Screen", radio, ignore_permissions=True, force=True)
	video = {"slide": {"elements": [{"type": "video", "sound": True}]}}
	assert programme._sounds(video) and not programme._sounds({"slide": {"elements": [{"type": "video"}]}})
	with mock.patch("onedesk.one_display.programme.slides", return_value={"slides": [{**video, "ms": 8000}, {"slide": {"elements": []}, "ms": 4000}]}):
		assert programme.duck(zone) == [[{"ms": 8000, "sound": 1}, {"ms": 4000, "sound": 0}]], "a zone knows when a screen in it plays a video's sound"
	for doctype, row in (("Sound Zone", {"plays": "Slides", "slide_playlist": "Showroom"}), ("Display Channel", {"plays": "Music", "music_playlist": heard["music"]["name"]})):
		doc = frappe.get_doc(doctype, zone if doctype == "Sound Zone" else CHANNEL)
		doc.append("programme", {**row, "days": "Every Day", "from_time": "09:00:00", "to_time": "10:00:00"})
		try:
			doc.save(ignore_permissions=True)
			raise AssertionError(f"a {doctype} plays {row['plays']}")
		except frappe.ValidationError:
			frappe.clear_messages()
			frappe.clear_document_cache(doctype, doc.name)


@check
def onedisplay_says_calls_from_a_voice_pack():
	"""The showroom's calls are said from a voice pack: the first call asks
	OneAI for the pieces it lacks and is said in the screen's own voice; once
	they are kept, a ticket is joined from them. Make the Rest asks for the
	rest, Make Again says a piece once more in its place, and deleting the
	pack deletes its clips."""
	from onedesk.one_display import packs, programme, queue

	zone = frappe.get_doc("Sound Zone", frappe.db.get_value("Queue", QUEUE, "sound_zone"))
	lang = zone.voice_language or "en"
	sounds = iter(base64.b64encode(n.to_bytes(2, "little") * 1600).decode() for n in range(10000))
	said = mock.patch("onedesk.one_ai.run.make", side_effect=lambda job, text, reference=None, voice=None: {"data": next(sounds), "mime": "audio/L16;rate=16000"})
	called = {"called": [{"id": "check", "ticket": "A12", "counter": "1", "at": str(now_datetime())}]}
	name = None
	kept = packs.pack(lang, "Kore", make=False)
	if kept:
		frappe.delete_doc("Voice Pack", kept, ignore_permissions=True, force=True)
	try:
		with mock.patch("onedesk.one.apps.ai_on", return_value=True), said, mock.patch("frappe.enqueue") as queued:
			zone.voice = "Kore"
			with mock.patch.object(queue, "board", return_value=called):
				first = programme.calls(zone, lang)[0]
			name = packs.pack(lang, "Kore")
			assert not first["pieces"] and not first["audio"] and queued.call_args.kwargs["name"] == name, "a missing piece is asked for"
			packs.fill(name)
			with mock.patch.object(queue, "board", return_value=called):
				joined = programme.calls(zone, lang)[0]["pieces"]
			assert len(joined) == len(packs.call("A12", "1", lang=lang)) and all(joined), joined
			with as_user(OWNER):
				assert packs.of_zone(zone.name) == name
				assert packs.make(name) > packs.NUMBERS, "the rest is every number below a thousand and more"
				assert packs.again(name) == frappe.db.get_value("Voice Pack", name, "made")
			was = packs.clips(name)["n:12"]
			packs.redo(name, ["n:12"])
			now = packs.clips(name)["n:12"]
			assert now != was and not frappe.db.exists("File", {"file_url": was, "attached_to_name": name}), "Make Again says a piece in its place"
			assert frappe.db.get_value("Voice Pack", name, "made") == len(packs.clips(name))
	finally:
		frappe.cache.delete_value(f"one_display_pack_wanted:{name}")
		if name:
			frappe.delete_doc("Voice Pack", name, ignore_permissions=True, force=True)
			assert not frappe.db.exists("File", {"attached_to_doctype": "Voice Pack", "attached_to_name": name}), "a pack's clips go with it"
		if kept:
			packs.pack(lang, "Kore")
		frappe.clear_document_cache("Sound Zone", zone.name)


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
			assert api.shown(file_id, sig).status_code == 200, "a screen fetches the picture as nobody"
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
		# the projects figure is words on the screen, a chip its source fills (chips.py)
		said = " ".join(one.get("content") or "" for one in lobby["layout"]["backdrop"]["elements"])
		assert "Projects underway" in said and "{projects" not in said, said
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
			# the words it already has, such as a list a source fills (chips.py)
			words = [one["id"] for one in elements if one["type"] != "widget"]
			weather = next(one for one in placed if one["widget"]["widget_type"] == "Weather")
			assert weather.get("fillColor"), "a widget's look is its element's"
			weather["fillColor"] = "#FFFFFFF2"
			elements.append({"id": "heading", "type": "text", "left": 40, "top": 400, "width": 400, "zIndex": 1, "content": "<p>Fitted in a week</p>"})
			kept = {key: slide.get(key) for key in api.SLIDE_FIELDS if key in slide}
			api.save_slides(made, json.dumps([{**kept, "elements": json.dumps(elements)}]), doc["modified"])
			after = layout.get(WORKSHOP)["widgets"]
			assert len(after) == len(rows), "no widget is lost or doubled"
			moved = next(row for row in after if row["id"] == clock["widget"]["id"])
			assert abs(moved["x"] - (was - 10)) < 0.01, (was, moved["x"])
			stored = json.loads(frappe.get_doc(api.PRESENTATION, made).slides[0].elements)
			assert [one["id"] for one in stored] == words + ["heading"], "the backdrop keeps no widget of its own"
			looked = next(row for row in after if row["widget_type"] == "Weather")
			assert json.loads(looked["settings"])["look"]["fillColor"] == "#FFFFFFF2", looked["settings"]
			frappe.clear_document_cache("Widget Collection", WORKSHOP)
			drawn = programme.layout(WORKSHOP, "en")["backdrop"]
			assert drawn["bare"] and [one["id"] for one in drawn["elements"]] == words + ["heading"], drawn
	finally:
		frappe.db.rollback(save_point="screen_check")


@check
def onedisplay_starts_a_screen_from_a_template():
	"""Every template lays out on every shape of screen, its widgets kinds
	there are and inside the frame; one put on a new layout is saved as its
	rows and its backdrop, the way the editor saves, and a channel with no
	layout is given one to open on its templates (starters.py)."""
	from onedesk.one_display import layout, screen, sizes, starters
	from onedesk.one_display import widgets as kinds

	frappe.db.savepoint("starter_check")
	try:
		with as_user(OWNER):
			for size in sizes.SIZES:
				wide, high = (round(one / 2) for one in sizes.SIZES[size])
				for key in starters.STARTERS:
					made = starters.build(key, wide, high)
					placed = [one for one in made["elements"] if one["type"] == "widget"]
					assert placed, f"{key} puts down no widget"
					for one in placed:
						assert one["widget"]["widget_type"] in kinds.TYPES, (key, one["widget"]["widget_type"])
						assert -1 <= one["left"] and one["left"] + one["width"] <= wide + 1, (key, size, one["left"], one["width"])
			named = frappe.get_doc({"doctype": "Widget Collection", "collection_name": "Template Check", "screen_size": "Portrait"}).insert().name
			assert starters.offered(named)["shape"] == "tall"
			drawn_for_editor = starters.made(named, "queue_tall")
			assert any(one["type"] == "widget" for one in drawn_for_editor["elements"]), "the editor is given the widgets"
			starters.apply(named, "queue_tall")
			rows = layout.get(named)["widgets"]
			built = [one for one in starters.build("queue_tall", 540, 960)["elements"] if one["type"] == "widget"]
			assert [row["widget_type"] for row in rows] == [one["widget"]["widget_type"] for one in built], rows
			assert any(row["source"] for row in rows if row["widget_type"] == "Queue Board"), "the queue board reads the first queue"
			drawn = screen.drawn(frappe.get_doc("Widget Collection", named))
			assert drawn and drawn["elements"], "the template's words are on its backdrop"
			channel = frappe.get_doc({"doctype": "Display Channel", "channel_name": "Template Check Channel"}).insert()
			opened = starters.for_channel(channel.name)["presentation"]
			assert frappe.db.get_value("Display Channel", channel.name, "widget_collection"), "the channel was given a layout"
			assert starters.for_channel(channel.name)["presentation"] == opened, "and keeps it"
	finally:
		frappe.db.rollback(save_point="starter_check")


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
	tracks = frappe.db.get_value("Sound Zone", frappe.db.get_value("Queue", QUEUE, "sound_zone"), "music_playlist")
	assert tracks, "the showroom's zone has music"
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
