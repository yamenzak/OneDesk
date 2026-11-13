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

from onedesk.one import apps, registry

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


def say(text: str, lang: str, voice: str, tone: str = "Announcement", reference: str = "") -> bytes | None:
	"""`text` said by OneAI in that voice and tone, as a WAV, or None."""
	from onedesk.one_ai import run

	said = run.make(
		JOB,
		f"Tone: {TONES.get(tone, TONES['Announcement'])}.\nLanguage: {lang}.\n\n{text}",
		reference=reference or f"OneDisplay voice {key(text, lang, voice, tone)}",
		voice=voice or "Kore",
	)
	return _wav(said["data"], said.get("mime") or "") if said.get("data") else None


def kept(text: str, lang: str, voice: str, tone: str = "Announcement") -> str | None:
	"""The recording of the whole of `text`, where one was made."""
	return frappe.db.get_value(DOCTYPE, key(text, lang, voice, tone), "audio")


def make(text: str, lang: str, voice: str, tone: str = "Announcement") -> str:
	"""The recording of `text`, made now if it isn't kept yet."""
	name = key(text, lang, voice, tone)
	found = kept(text, lang, voice, tone)
	if found:
		return found
	sound = say(text, lang, voice, tone)
	if not sound:
		return ""
	doc = frappe.get_doc({"doctype": DOCTYPE, "key": name, "text": text, "language": lang, "voice": voice}).insert(
		ignore_permissions=True
	)
	saved = attach(DOCTYPE, doc.name, f"voice-{name}.wav", sound, "audio")
	doc.db_set("audio", saved.file_url)
	return saved.file_url


def attach(doctype: str, name: str, file_name: str, sound: bytes, field: str | None = None, quiet: bool = False):
	"""A recording kept as a file on a record, which OneCloud shows under it.
	Quiet leaves the record's timeline alone, for a pack's thousand clips."""
	on = {"attached_to_doctype": doctype, "attached_to_name": name, "attached_to_field": field}
	saved = frappe.get_doc({"doctype": "File", "file_name": file_name, "content": sound, "is_private": 0, **({} if quiet else on)})
	saved.insert(ignore_permissions=True)
	if quiet:
		saved.db_set(on, update_modified=False)
	return saved


def replace(url: str | None, doctype: str, name: str, keep: str) -> None:
	"""Drop the file a record kept at `url`, once `keep` takes its place."""
	filters = {"file_url": url, "attached_to_doctype": doctype, "attached_to_name": name, "name": ["!=", keep]}
	for old in frappe.get_all("File", filters=filters, pluck="name") if url else []:
		frappe.delete_doc("File", old, ignore_permissions=True, force=True)


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
	sound = say(doc.script, doc.language or frappe.db.get_default("lang") or "en", doc.voice or "Kore", doc.tone or "Announcement", f"OneDisplay ad {doc.name}")
	if not sound:
		frappe.throw(_("{0} could not make the recording. Try again.").format(registry.name("one_ai")))
	was = doc.audio
	saved = attach("Voice Ad", doc.name, f"{doc.name}.wav", sound, "audio")
	replace(was, "Voice Ad", doc.name, saved.name)
	doc.db_set("audio", saved.file_url)
	return saved.file_url
