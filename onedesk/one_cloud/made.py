"""What OneAI makes into a OneCloud folder from a description: a picture,
music, a short video, or words read aloud. A picture and speech are made
while the person waits; music and a video in the background, and whoever
asked is told when the file is there (AGENTS.md, Under the hood)."""

import base64

import frappe
from frappe import _

from onedesk.one import apps
from onedesk.one_cloud import api, tell, upload

JOBS = {"picture": "cloud_picture", "music": "cloud_music", "video": "cloud_video", "speech": "cloud_voice"}
LATER = ("music", "video")
SHAPES = {"square": ("square", "Landscape"), "wide": ("wide, 16:9", "Landscape"), "tall": ("tall, 9:16", "Portrait")}
VOICES = ("Kore", "Puck", "Charon", "Aoede", "Fenrir", "Leda", "Orus", "Zephyr")
USUAL = {"picture": "png", "music": "mp3", "video": "mp4", "speech": "wav"}
MOST_WORDS = 4000
TITLE = 60


def named(name: str | None, description: str) -> str:
	"""The file's name without its extension: the one given, else the start
	of the description. Pure."""
	given = api._clean(name)
	if given:
		return given
	words = api._clean(description)
	return words if len(words) <= TITLE else words[: TITLE - 1].rstrip() + "…"


def making(kind: str, description: str, shape: str | None, voice: str | None, reference: str | None = None) -> tuple[bytes, str]:
	"""Make it: the bytes and their extension. OneWriter's pictures are made
	here too, under their own reference."""
	from onedesk.one_ai import run
	from onedesk.one_display.make import EXTENSIONS
	from onedesk.one_display.voices import _wav

	job, reference = JOBS[kind], reference or f"OneCloud {kind}"
	look, orientation = SHAPES.get(shape or "", SHAPES["square" if kind == "picture" else "wide"])
	if kind == "video":
		from onedesk.one_slide.ai import _video

		said = _video(f"Shape: {look}.\n\n{description}", orientation, job=job, reference=reference)
	elif kind == "picture":
		said = run.make(job, f"Shape: {look}.\n\n{description}", reference=reference)
	elif kind == "speech":
		said = run.make(job, f"Tone: a clear, natural voice.\n\n{description}", reference=reference, voice=voice if voice in VOICES else VOICES[0])
	else:
		said = run.make(job, description, reference=reference)
	if not said.get("data"):
		raise frappe.ValidationError(f"the {kind} came back empty")
	mime = (said.get("mime") or "").split(";")[0].strip()
	if kind == "speech":
		return _wav(said["data"], said.get("mime") or ""), "wav"
	return base64.b64decode(said["data"]), EXTENSIONS.get(mime, USUAL[kind])


def _keep(target: str, stem: str, content: bytes, extension: str) -> dict:
	return upload._place(target, None, {"file_name": f"{stem}.{extension}", "content": content})


@frappe.whitelist(methods=["POST"])
def create(kind: str, target: str, description: str, shape: str | None = None, voice: str | None = None, name: str | None = None) -> dict:
	"""A picture or speech made now and put in `target`: its node. Music or
	a video begun, put there when it is made, and whoever asked told."""
	if kind not in JOBS:
		frappe.throw(_("OneAI can make a picture, music, a video or speech."))
	description = (description or "").strip()[:MOST_WORDS]
	if not description:
		frappe.throw(_("Describe what OneAI should make."))
	api._target(target)
	apps.refuse_ai()
	stem = named(name, description)
	if kind in LATER:
		frappe.enqueue(
			"onedesk.one_cloud.made.made_later",
			queue="long",
			timeout=20 * 60,
			kind=kind,
			target=target,
			description=description,
			shape=shape,
			stem=stem,
			asker=frappe.session.user,
		)
		return {"begun": True}
	try:
		content, extension = making(kind, description, shape, voice)
	except frappe.ValidationError:
		frappe.throw(_("OneAI could not make it. Try again, or describe it differently."))
	return _keep(target, stem, content, extension)


def made_later(kind: str, target: str, description: str, shape: str | None, stem: str, asker: str) -> None:
	"""Make it, keep it, and tell whoever asked that it is there, or that
	it could not be made."""
	frappe.set_user(asker)
	frappe.db.savepoint("one_cloud_made")
	try:
		content, extension = making(kind, description, shape, None)
		tell.made(asker, _keep(target, stem, content, extension), target)
	except Exception:
		frappe.db.rollback(save_point="one_cloud_made")
		frappe.log_error(title=f"OneCloud {kind}")
		tell.not_made(asker, stem, target)
