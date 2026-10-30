"""What OneAI makes in a presentation (AGENTS.md, OneAI): a slide designed
from a sentence, a picture, and a video that arrives on a new slide. The jobs
are OneSlide's own (`slide_design`, `slide_picture`, `slide_video`). A
picture is also offered in OneWriter (`one_doc`)."""

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

# Why OneAI's chat does not do these itself (docs/READY.md, mechanism 11):
# each is the editor's own, or is OneAI already, asked from the editor.
NOT_FOR_AI = {
	"ai.design": "It is OneAI designing a slide, asked from the presentation's own OneAI menu.",
	"ai.picture": "It is OneAI making a picture, asked from the presentation's own OneAI menu.",
	"ai.video": "It is OneAI making a video, asked from the presentation's own OneAI menu.",
	"api.make": "A presentation is made in OneCloud where it is to be kept, by the person who will work on it.",
	"api.save_slides": "Slides are laid out by eye in the editor, which saves them as it goes.",
	"api.update_slide_attachments": "It answers a slide pasted in the editor.",
	"api.get_updated_json": "It answers a slide pasted from another presentation in the editor.",
	"api.get_webp_doc": "It answers a picture put on a slide in the editor.",
	"api.save_base64_image": "It keeps a video's first frame, taken in the editor.",
	"api.save_presentation_thumbnail": "It keeps the picture OneCloud shows, taken in the editor.",
	"api.upload": "It answers a picture or a video put on a slide in the editor.",
	"api.update_title": "A presentation is named from its title in the editor.",
	"api.rename_presentation": "A presentation is named from its title in the editor.",
	"api.update_theme": "A theme is chosen by eye in the editor, where its layouts are shown.",
	"paper.pdf": "A PDF is drawn from the slides as the editor shows them, so only the editor can make one.",
	"templates.save_as": "A template is kept from the editor's File menu by whoever made the presentation.",
	"versions.keep": "A version is named from the editor's Version History by the person working on it.",
	"versions.restore": "Going back to a version is the person's call, from the editor's Version History.",
	"guides.keep": "A guide is dragged out of the editor's rulers to line things up by eye.",
	"master.edit": "The master is opened from the editor's File menu by the person laying out the slides.",
	"fonts.upload": "A font file is chosen from a person's own computer in the editor's font picker.",
	"fonts.google_add": "Adding a font to the workspace is the person's call, from the font picker.",
	"powerpoint.export": "A PowerPoint file is made from the editor's File menu by the person who will take it elsewhere.",
	"library.keep": "A slide is put in the company's library from its menu by a manager who chose it.",
	"library.forget": "A slide is taken off the company's library by a manager, in Add Slide.",
	"layouts.restyle": "Bringing a template's new look into every slide is the person's call, from the editor's File menu.",
	"resize.resize": "A presentation's size is chosen in the editor, where every slide is redrawn in front of the person who asked.",
}

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

	width, height = api.frame(name)
	said = run.once("slide_design", f"{brand()}\nThe slide is {width} by {height} pixels.\n\n{description}", reference="OneSlide design")
	try:
		designed = json.loads(FENCE.sub("", (said or "").strip()).strip())
	except ValueError:
		designed = None
	if not isinstance(designed, dict) or not designed.get("blocks"):
		frappe.throw(_("OneAI could not design the slide. Try again."))
	drawn = convert.slide(designed, width, height)
	return {"background": play.background(drawn["background"]), "elements": json.loads(play.cleaned(drawn["elements"]))}


def made_picture(description: str) -> tuple[bytes, str]:
	from onedesk.one_ai import run

	said = run.make("slide_picture", description, reference="OneSlide picture")
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
		width, height = api.frame(name)
		said = _video(description, "Portrait" if height > width else "Landscape")
		extension = VIDEOS.get((said.get("mime") or "").split(";")[0].strip(), "mp4")
		kept = api._kept(name, f"video-{uuid.uuid4().hex[:6]}.{extension}", base64.b64decode(said["data"]))
		doc = frappe.get_doc(api.PRESENTATION, name)
		doc.append("slides", added(kept["file_url"], what, doc.slides[-1].background if doc.slides else "", width, height))
		doc.save(ignore_permissions=True)
		tell.video(asker, name, what)
	except Exception:
		frappe.db.rollback(save_point="one_slide_video")
		frappe.log_error(title="OneSlide video")
		tell.video(asker, name, what, failed=True)


def added(src: str, what: str, background: str, width: float = convert.WIDE, height: float = convert.HIGH) -> dict:
	"""A slide holding one video across the whole of it. Pure."""
	element = {
		"id": uuid.uuid4().hex[:9], "type": "video", "src": src, "name": what, "left": 0, "top": 0,
		"width": width, "height": height, "zIndex": 1, "opacity": 100,
		"autoplay": True, "loop": True, "muted": True,
	}
	return {"client_id": str(uuid.uuid4()), "background": background or "#000000FF", "elements": play.cleaned([element])}


def _video(description: str, orientation: str) -> dict:
	from onedesk.one_ai import run

	ticket = run.begin("slide_video", description, reference="OneSlide video", orientation=orientation)
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
