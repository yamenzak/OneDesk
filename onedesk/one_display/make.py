"""What OneAI makes for OneDisplay from a sentence (one_display/AGENTS.md,
stage 6): a picture or a video for a slide, a designed slide, music for a
playlist, a widget of your own. Each is something to look at and change
before it is used: a video or a song is added to its playlist turned off, and
whoever asked is told."""

import base64
import json
import re
import time
from typing import Annotated

import frappe
from frappe import _

from onedesk.one import apps

FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
EXTENSIONS = {
	"image/png": "png",
	"image/jpeg": "jpg",
	"image/webp": "webp",
	"video/mp4": "mp4",
	"video/webm": "webm",
	"audio/mpeg": "mp3",
	"audio/mp3": "mp3",
	"audio/wav": "wav",
	"audio/x-wav": "wav",
	"audio/ogg": "ogg",
}

# How often a begun video is asked after, and for how long.
ASK_EVERY = 10
ASK_FOR = 15 * 60


def _may(doctype: str) -> None:
	frappe.has_permission(doctype, "write", throw=True)
	apps.refuse_ai()


def _brand() -> str:
	company = frappe.db.get_default("company")
	colour = frappe.db.get_value("Company", company, "one_brand_colour") if company else None
	name = frappe.db.get_value("Company", company, "company_name") if company else None
	return f"The business is {name or 'the workspace'}; its brand colour is {colour or '#2563eb'}."


@frappe.whitelist(methods=["POST"])
def picture(description: Annotated[str, "What the picture shows."]) -> str:
	"""A picture for a slide, kept as a public file: its address."""
	_may("Slide Playlist")
	from onedesk.one_ai import run

	said = run.make("display_picture", description.strip()[:2000], reference="OneDisplay picture")
	if not said.get("data"):
		frappe.throw(_("OneAI could not make the picture. Try again."))
	return _kept(said, "slide", "png")


def _kept(said: dict, stem: str, usual: str) -> str:
	"""What OneAI made, as a public file a screen may fetch: its address."""
	extension = EXTENSIONS.get((said.get("mime") or "").split(";")[0].strip(), usual)
	saved = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{stem}-{frappe.generate_hash(length=8)}.{extension}",
			"content": base64.b64decode(said["data"]),
			"is_private": 0,
			"folder": "Home",
		}
	).insert(ignore_permissions=True)
	return saved.file_url


@frappe.whitelist(methods=["POST"])
def video(
	playlist: Annotated[str, "The slide playlist the video is added to."],
	description: Annotated[str, "What the video shows."],
	orientation: Annotated[str, "Landscape or Portrait."] = "Landscape",
) -> dict:
	"""Begin an eight-second video for a slide. It is made in the background,
	added to the playlist as a slide that is not shown yet, and whoever asked
	is told."""
	_may_change("Slide Playlist", playlist)
	_later("video", playlist, description, orientation=orientation if orientation in ("Landscape", "Portrait") else "Landscape")
	return {"begun": True}


@frappe.whitelist(methods=["POST"])
def music(
	playlist: Annotated[str, "The music playlist the track is added to."],
	description: Annotated[str, "What the music sounds like."],
) -> dict:
	"""Begin a piece of instrumental music. It is made in the background,
	added to the playlist's end, and whoever asked is told."""
	_may_change("Music Playlist", playlist)
	_later("music", playlist, description)
	return {"begun": True}


def _may_change(doctype: str, name: str) -> None:
	_may(doctype)
	frappe.get_doc(doctype, name).check_permission("write")


def _later(what: str, playlist: str, description: str, **more) -> None:
	description = (description or "").strip()[:2000]
	if not description:
		frappe.throw(_("Say what OneAI should make."))
	frappe.enqueue(
		"onedesk.one_display.make.made_later",
		queue="long",
		timeout=ASK_FOR + 300,
		what=what,
		playlist=playlist,
		description=description,
		asker=frappe.session.user,
		**more,
	)


TITLE = 60
SECONDS = 8
MADE = "one_display_made"


def made_later(what: str, playlist: str, description: str, asker: str, orientation: str = "Landscape") -> None:
	"""Make it, keep it, add it to its playlist, and tell whoever asked:
	that it is there, or that it could not be made."""
	from onedesk.one_display import tell

	doctype = "Slide Playlist" if what == "video" else "Music Playlist"
	frappe.set_user(asker)
	title = description if len(description) <= TITLE else description[: TITLE - 1].rstrip() + "…"
	frappe.db.savepoint(MADE)
	try:
		said = _video(description, orientation) if what == "video" else _music(description)
		url = _kept(said, what, "mp4" if what == "video" else "mp3")
		doc = frappe.get_doc(doctype, playlist)
		if what == "video":
			doc.append("slides", {"kind": "Video", "file": url, "title": title, "duration": SECONDS, "fit": "Cover", "paused": 1})
		else:
			doc.append("tracks", {"file": url, "title": title, "duration": seconds(said), "paused": 1})
		doc.save()
		tell.made(asker, doctype, playlist, title)
	except Exception:
		frappe.db.rollback(save_point=MADE)
		frappe.log_error(title=f"OneDisplay {what}")
		tell.made(asker, doctype, playlist, title, failed=True)


def _video(description: str, orientation: str) -> dict:
	from onedesk.one_ai import run

	ticket = run.begin("display_video", description, reference="OneDisplay video", orientation=orientation)
	if not ticket:
		raise frappe.ValidationError("no video was begun")
	waited = 0
	while waited < ASK_FOR:
		time.sleep(ASK_EVERY)
		waited += ASK_EVERY
		said = run.collect(ticket, reference="OneDisplay video")
		if said.get("done"):
			if not said.get("data"):
				raise frappe.ValidationError("the video came back empty")
			return said
	raise frappe.ValidationError("the video took too long")


def _music(description: str) -> dict:
	from onedesk.one_ai import run

	said = run.make("display_music", description, reference="OneDisplay music")
	if not said.get("data"):
		raise frappe.ValidationError("the music came back empty")
	return said


def _code(said: str) -> str:
	return FENCE.sub("", (said or "").strip()).strip()


@frappe.whitelist(methods=["POST"])
def design(
	description: Annotated[str, "What the slide says and looks like."],
	orientation: Annotated[str, "Landscape or Portrait."] = "Landscape",
) -> dict:
	"""A slide as blocks on the canvas, and the HTML they draw, so it opens
	in the designer like any slide made there."""
	_may("Slide Playlist")
	from onedesk.one_ai import run
	from onedesk.one_display import slides

	said = run.once("display_design", f"{_brand()}\nOrientation: {orientation}.\n\n{description.strip()[:4000]}", reference="OneDisplay design")
	try:
		blocks = json.loads(_code(said))
	except ValueError:
		blocks = None
	if not isinstance(blocks, dict) or not blocks.get("blocks"):
		frappe.throw(_("OneAI could not design the slide. Try again."))
	made = slides.clean({**blocks, "orientation": orientation})
	return {"design": made, "html": slides.render(made)}


@frappe.whitelist(methods=["POST"])
def widget(
	description: Annotated[str, "What the widget shows and does."],
	rows: Annotated[str | None, "A sample of the rows it will be given, as JSON."] = None,
) -> str:
	"""A custom widget's code, for a widget of kind Custom."""
	_may("Widget Collection")
	from onedesk.one_ai import run

	sample = f"\nIts rows look like this: {rows[:2000]}" if rows else ""
	said = run.once("display_widget", f"{_brand()}{sample}\n\n{description.strip()[:4000]}", reference="OneDisplay widget")
	code = _code(said)
	if not code:
		frappe.throw(_("OneAI could not write the widget. Try again."))
	return code


# An MPEG audio frame's bitrates (kbit/s) and sample rates, by version.
BITRATES = {1: (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320), 2: (0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160)}
RATES = {3: (44100, 48000, 32000), 2: (22050, 24000, 16000), 0: (11025, 12000, 8000)}


def seconds(said: dict) -> float:
	"""How long a song OneAI made plays, read from the file itself, since a
	track no browser has measured is not played. A WAV says so in its header;
	an MP3 in its Xing frame count, or else from its bitrate."""
	data = base64.b64decode(said.get("data") or "")
	if data[:4] == b"RIFF":
		import io
		import wave

		try:
			with wave.open(io.BytesIO(data)) as heard:
				return round(heard.getnframes() / float(heard.getframerate()), 1)
		except (wave.Error, EOFError, ZeroDivisionError):
			return 0.0
	at = 10 + int.from_bytes(bytes(b & 0x7F for b in data[6:10]), "big") if data[:3] == b"ID3" else 0
	while at + 4 <= len(data) and not (data[at] == 0xFF and data[at + 1] & 0xE0 == 0xE0):
		at += 1
	if at + 4 > len(data):
		return 0.0
	head = int.from_bytes(data[at : at + 4], "big")
	version, rate, bitrate = (head >> 19) & 3, (head >> 10) & 3, (head >> 12) & 15
	if version == 1 or rate == 3 or not bitrate or bitrate == 15:
		return 0.0
	hz = RATES[version][rate]
	per_frame = 1152 if version == 3 else 576
	xing = data.find(b"Xing", at, at + 64)
	if xing < 0:
		xing = data.find(b"Info", at, at + 64)
	if xing >= 0 and data[xing + 7] & 1:
		return round(int.from_bytes(data[xing + 8 : xing + 12], "big") * per_frame / hz, 1)
	kbits = BITRATES[1 if version == 3 else 2][bitrate]
	return round((len(data) - at) * 8 / (kbits * 1000), 1)
