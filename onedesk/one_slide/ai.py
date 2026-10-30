"""What OneAI makes in a presentation (docs/ONESLIDE.md, OneAI): a slide
designed from a sentence, a picture, and a video that arrives on a new slide.
The jobs are OneDisplay's (`display_design`, `display_picture`,
`display_video`), so their credits and history carry on; only where they are
offered moved. A picture is also offered in OneWriter (`one_doc`)."""

import base64
import json
import re
import time
import uuid
from typing import Annotated

import frappe
from frappe import _

from onedesk.one import apps
from onedesk.one_slide import api, convert, play

FENCE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$")
PICTURES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
VIDEOS = {"video/mp4": "mp4", "video/webm": "webm"}
TITLE = 60
ASK_EVERY = 10
ASK_FOR = 15 * 60


def asked(description: str, most: int) -> str:
	apps.refuse_ai()
	description = (description or "").strip()[:most]
	if not description:
		frappe.throw(_("Say what OneAI should make."))
	return description


def brand() -> str:
	"""The business and its colour, for a design to be in."""
	company = frappe.db.get_default("company")
	colour = frappe.db.get_value("Company", company, "one_brand_colour") if company else None
	name = frappe.db.get_value("Company", company, "company_name") if company else None
	return f"The business is {name or 'the workspace'}; its brand colour is {colour or '#2563eb'}."


@frappe.whitelist(methods=["POST"])
def design(
	name: Annotated[str, "The presentation."],
	description: Annotated[str, "What the slide says and looks like."],
) -> dict:
	"""A slide designed from a sentence, as Suite's elements: the editor adds
	it after the slide that is open, and it can be changed like any other."""
	api._may(name, "write")
	description = asked(description, 4000)
	from onedesk.one_ai import run

	said = run.once("display_design", f"{brand()}\nOrientation: Landscape.\n\n{description}", reference="OneSlide design")
	try:
		designed = json.loads(FENCE.sub("", (said or "").strip()).strip())
	except ValueError:
		designed = None
	if not isinstance(designed, dict) or not designed.get("blocks"):
		frappe.throw(_("OneAI could not design the slide. Try again."))
	drawn = convert.slide({**designed, "orientation": "Landscape"})
	return {"background": play.background(drawn["background"]), "elements": json.loads(play.cleaned(drawn["elements"]))}


def made_picture(description: str) -> tuple[bytes, str]:
	from onedesk.one_ai import run

	said = run.make("display_picture", description, reference="OneSlide picture")
	if not said.get("data"):
		frappe.throw(_("OneAI could not make the picture. Try again."))
	return base64.b64decode(said["data"]), PICTURES.get((said.get("mime") or "").split(";")[0].strip(), "png")


@frappe.whitelist(methods=["POST"])
def picture(
	name: Annotated[str, "The presentation."],
	description: Annotated[str, "What the picture shows."],
) -> dict:
	"""A picture for a slide, kept on the presentation as anything uploaded
	to it is: its file, as the editor's upload answers."""
	api._may(name, "write")
	content, extension = made_picture(asked(description, 2000))
	return api._kept(name, f"picture-{uuid.uuid4().hex[:6]}.{extension}", content)


@frappe.whitelist(methods=["POST"])
def video(
	name: Annotated[str, "The presentation."],
	description: Annotated[str, "What the video shows."],
) -> dict:
	"""Begin an eight-second video. It is made in the background, put on a
	new slide at the end of the presentation, and whoever asked is told."""
	api._may(name, "write")
	frappe.enqueue(
		"onedesk.one_slide.ai.made_later",
		queue="long",
		timeout=ASK_FOR + 300,
		name=name,
		description=asked(description, 2000),
		asker=frappe.session.user,
	)
	return {"begun": True}


def made_later(name: str, description: str, asker: str) -> None:
	"""Make it, keep it, add it on a slide of its own, and tell whoever
	asked: that it is there, or that it could not be made."""
	from onedesk.one_slide import tell

	frappe.set_user(asker)
	what = description if len(description) <= TITLE else description[: TITLE - 1].rstrip() + "…"
	frappe.db.savepoint("one_slide_video")
	try:
		said = _video(description)
		extension = VIDEOS.get((said.get("mime") or "").split(";")[0].strip(), "mp4")
		kept = api._kept(name, f"video-{uuid.uuid4().hex[:6]}.{extension}", base64.b64decode(said["data"]))
		doc = frappe.get_doc(api.PRESENTATION, name)
		doc.append("slides", added(kept["file_url"], what, doc.slides[-1].background if doc.slides else ""))
		doc.save(ignore_permissions=True)
		tell.video(asker, name, what)
	except Exception:
		frappe.db.rollback(save_point="one_slide_video")
		frappe.log_error(title="OneSlide video")
		tell.video(asker, name, what, failed=True)


def added(src: str, what: str, background: str) -> dict:
	"""A slide holding one video across the whole of it. Pure."""
	element = {
		"id": uuid.uuid4().hex[:9], "type": "video", "src": src, "name": what, "left": 0, "top": 0,
		"width": convert.WIDE, "height": convert.HIGH, "zIndex": 1, "opacity": 100,
		"autoplay": True, "loop": True, "muted": True,
	}
	return {"client_id": str(uuid.uuid4()), "background": background or "#000000FF", "elements": play.cleaned([element])}


def _video(description: str) -> dict:
	from onedesk.one_ai import run

	ticket = run.begin("display_video", description, reference="OneSlide video", orientation="Landscape")
	if not ticket:
		raise frappe.ValidationError("no video was begun")
	waited = 0
	while waited < ASK_FOR:
		time.sleep(ASK_EVERY)
		waited += ASK_EVERY
		said = run.collect(ticket, reference="OneSlide video")
		if said.get("done"):
			if not said.get("data"):
				raise frappe.ValidationError("the video came back empty")
			return said
	raise frappe.ValidationError("the video took too long")
