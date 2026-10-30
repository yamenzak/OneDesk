"""Voices: what a screen says in OneAI's voice rather than its own. A phrase
is recorded once per language, voice and tone, kept as a Display Voice, and
every screen plays the same file; a board waits a few seconds for a new one,
then lets the screen's own voice say it (one_display/AGENTS.md, Voices)."""

import base64
import hashlib
import io
import re
import wave
from typing import Annotated

import frappe
from frappe import _

from onedesk.one import apps

DOCTYPE = "Display Voice"
JOB = "display_voice"
TONES = {
	"Announcement": "a clear, calm public announcement",
	"Radio Ad": "a warm, upbeat radio advertisement",
	"Excited": "an excited, energetic announcement",
	"Calm": "a calm, gentle voice",
	"Friendly": "a friendly, welcoming voice",
}


def key(text: str, lang: str, voice: str, tone: str) -> str:
	return hashlib.sha1(f"{lang}|{voice}|{tone}|{text}".encode()).hexdigest()[:20]


def _wav(data: str, mime: str) -> bytes:
	"""Gemini's raw sound, 16-bit samples at the rate its type names, as a
	WAV every TV plays."""
	raw = base64.b64decode(data)
	if mime.startswith("audio/wav") or raw[:4] == b"RIFF":
		return raw
	rate = int((re.search(r"rate=(\d+)", mime or "") or [None, 24000])[1])
	out = io.BytesIO()
	with wave.open(out, "wb") as sound:
		sound.setnchannels(1)
		sound.setsampwidth(2)
		sound.setframerate(rate)
		sound.writeframes(raw)
	return out.getvalue()


def make(text: str, lang: str, voice: str, tone: str = "Announcement") -> str:
	"""The recording of `text`, made now if it isn't kept yet."""
	name = key(text, lang, voice, tone)
	kept = frappe.db.get_value(DOCTYPE, name, "audio")
	if kept:
		return kept
	from onedesk.one_ai import run

	said = run.make(
		JOB,
		f"Tone: {TONES.get(tone, TONES['Announcement'])}.\nLanguage: {lang}.\n\n{text}",
		reference=f"OneDisplay voice {name}",
		voice=voice or "Kore",
	)
	if not said.get("data"):
		return ""
	doc = frappe.get_doc({"doctype": DOCTYPE, "key": name, "text": text, "language": lang, "voice": voice}).insert(
		ignore_permissions=True
	)
	saved = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"voice-{name}.wav",
			"content": _wav(said["data"], said.get("mime") or ""),
			"is_private": 0,
			"attached_to_doctype": DOCTYPE,
			"attached_to_name": doc.name,
			"attached_to_field": "audio",
		}
	).insert(ignore_permissions=True)
	doc.db_set("audio", saved.file_url)
	return saved.file_url


def spoken(text: str, lang: str, voice: str | None, tone: str = "Announcement") -> str:
	"""The recording if it is kept; otherwise ask for it in the background
	and say nothing yet. Cheap enough to ask on every answer to a screen."""
	if not voice or not text or not apps.ai_on():
		return ""
	name = key(text, lang, voice, tone)
	kept = frappe.db.get_value(DOCTYPE, name, "audio")
	if kept:
		return kept
	if frappe.cache.get_value(f"one_display_voice_asked:{name}"):
		return ""
	frappe.cache.set_value(f"one_display_voice_asked:{name}", 1, expires_in_sec=600)
	frappe.enqueue(
		"onedesk.one_display.voices.made_later",
		queue="short",
		job_id=f"one_display_voice:{name}",
		deduplicate=True,
		text=text,
		lang=lang,
		voice=voice,
		tone=tone,
	)
	return ""


def made_later(text: str, lang: str, voice: str, tone: str) -> None:
	try:
		make(text, lang, voice, tone)
	except Exception:
		frappe.log_error(title="OneDisplay voice")


@frappe.whitelist(methods=["POST"])
def record(ad: Annotated[str, "The voice ad."]) -> str:
	"""Make the ad's recording in OneAI's voice, in its tone and language."""
	doc = frappe.get_doc("Voice Ad", ad)
	doc.check_permission("write")
	apps.refuse_ai()
	url = make(doc.script, doc.language or frappe.db.get_default("lang") or "en", doc.voice or "Kore", doc.tone or "Announcement")
	if not url:
		frappe.throw(_("OneAI could not make the recording. Try again."))
	doc.db_set("audio", url)
	return url
