"""What OneAI makes for OneDisplay from a sentence (one_display/AGENTS.md,
stage 6): music for a playlist and a widget of your own. A song is added to
its playlist turned off, and whoever asked is told. Pictures, videos and
designed slides are made in a presentation now (one_slide/ai.py)."""

import base64
import re
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

# How long a song may take to make.
ASK_FOR = 15 * 60


def _may(doctype: str) -> None:
	frappe.has_permission(doctype, "write", throw=True)
	apps.refuse_ai()


def _brand() -> str:
	company = frappe.db.get_default("company")
	colour = frappe.db.get_value("Company", company, "one_brand_colour") if company else None
	name = frappe.db.get_value("Company", company, "company_name") if company else None
	return f"The business is {name or 'the workspace'}; its brand colour is {colour or '#2563eb'}."


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
		frappe.throw(_("Describe what OneAI should make."))
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
MADE = "one_display_made"


def made_later(what: str, playlist: str, description: str, asker: str) -> None:
	"""Make it, keep it, add it to its playlist, and tell whoever asked:
	that it is there, or that it could not be made."""
	from onedesk.one_display import tell

	doctype = "Music Playlist"
	frappe.set_user(asker)
	title = description if len(description) <= TITLE else description[: TITLE - 1].rstrip() + "…"
	frappe.db.savepoint(MADE)
	try:
		said = _music(description)
		url = _kept(said, what, "mp3")
		doc = frappe.get_doc(doctype, playlist)
		doc.append("tracks", {"file": url, "title": title, "duration": seconds(said), "paused": 1})
		doc.save()
		tell.made(asker, doctype, playlist, title)
	except Exception:
		frappe.db.rollback(save_point=MADE)
		frappe.log_error(title=f"OneDisplay {what}")
		tell.made(asker, doctype, playlist, title, failed=True)


def _music(description: str) -> dict:
	from onedesk.one_ai import run

	said = run.make("display_music", description, reference="OneDisplay music")
	if not said.get("data"):
		raise frappe.ValidationError("the music came back empty")
	return said


def _code(said: str) -> str:
	return FENCE.sub("", (said or "").strip()).strip()


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
