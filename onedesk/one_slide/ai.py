"""What OneAI makes in a presentation (AGENTS.md, OneAI): from the editor's
menu, a slide designed from a sentence, a picture, and a video that arrives on
a new slide (OneSlide's own jobs); from OneAI's panel, a whole deck, a slide's
words or a slide made again, each as a card the reader approves."""

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
	"from_powerpoint.open_file": "It answers Open on a PowerPoint file in OneCloud, which then shows the presentation.",
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
	"data.save_sources": "A presentation's sources are picked in the editor's Data from Records, beside the slides they fill.",
	"data.freeze": "Writing the data in for good is the person's call, from the editor's File menu.",
	"data.for_each": "Making a copy on each record is the person's call, from the editor's File menu, with the records picked.",
	"shared.present_live": "Presenting live is the presenter's own act, from the editor's Present menu.",
	"shared.stop_live": "Presenting live ends when the presenter's slideshow ends.",
	"shared.viewed": "It is a guest's page saying how long each slide was on screen.",
	"remote.pair": "A phone is paired by the presenter scanning a code in the presenter view.",
	"remote.pair_link": "A phone is paired by somebody in front of a page showing the presentation through a link.",
	"remote.unpair": "A phone remote ends when the screen it drives closes.",
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


def _video(description: str, orientation: str, job: str = "slide_video", reference: str = "OneSlide video") -> dict:
	"""A video begun and waited for, collected every few seconds for at most
	a quarter of an hour."""
	from onedesk.one_ai import run

	ticket = run.begin(job, description, reference=reference, orientation=orientation)
	if not ticket:
		raise frappe.ValidationError("no video was begun")
	waited = 0
	while waited < ASK_FOR:
		time.sleep(ASK_EVERY)
		waited += ASK_EVERY
		said = run.collect(ticket, reference=reference)
		if said.get("done"):
			if not said.get("data"):
				raise frappe.ValidationError("the video came back empty")
			return said
	raise frappe.ValidationError("the video took too long")


# What OneAI's panel does with a presentation: reads it, and writes a deck,
# a slide's words or a slide made again as cards the reader approves
# (one_ai/proposals.py, Setup; approved below). AGENTS.md, OneAI.

#: How much of the open presentation the panel is told up front, and the
#: most slides one card writes.
MOST_SEEN = 3000
MOST_SLIDES = 30


def _readable(presentation: str) -> dict | None:
	try:
		return api._may(presentation, "read")
	except (frappe.PermissionError, frappe.DoesNotExistError):
		return None


def _plain(html) -> str:
	from frappe.utils import strip_html

	html = re.sub(r"</(p|h[1-6]|li)>", "\n", str(html or ""))
	return "\n".join(line.strip() for line in strip_html(html).splitlines() if line.strip())


def _said_on(elements: str | list) -> list[dict]:
	"""A slide's words, element by element."""
	drawn = json.loads(elements or "[]") if isinstance(elements, str) else elements or []
	return [{"id": one["id"], "text": _plain(one["content"])} for one in drawn if isinstance(one, dict) and one.get("id") and isinstance(one.get("content"), str) and _plain(one["content"])]


def _row(doc, slide: str):
	return next((row for row in doc.slides if row.client_id == slide or str(row.idx) == str(slide)), None)


def read_presentation(presentation: Annotated[str, "The presentation's id, from the page the reader is on."]) -> dict:
	"""What a presentation says: each slide's id, number, kind, words by
	element and speaker notes, and the records its words come from."""
	from onedesk.one_slide import data

	item = _readable(presentation)
	if not item:
		return {"error": f"No presentation the reader may open is {presentation}."}
	doc = frappe.get_doc(api.PRESENTATION, presentation)
	return {
		"title": item["file_name"],
		"size": list(api.frame(presentation)),
		"slides": [{"id": row.client_id, "number": row.idx, "kind": row.get("kind") or "", "texts": _said_on(row.elements), "notes": row.notes or ""} for row in doc.slides],
		"sources": data.cleaned(doc.get("sources")),
	}


def _cleaned_slides(slides) -> list[dict] | str:
	from onedesk.one_slide import decks

	if isinstance(slides, str):
		try:
			slides = json.loads(slides)
		except ValueError:
			return "slides is a JSON list."
	if not isinstance(slides, list) or not slides:
		return "slides is a list of {kind, words, notes}."
	out = []
	for one in slides[:MOST_SLIDES]:
		if not isinstance(one, dict) or one.get("kind") not in decks.KINDS:
			return f"Each slide's kind is one of {', '.join(decks.KINDS)}."
		words = one.get("words") if isinstance(one.get("words"), dict) else {}
		out.append({"kind": one["kind"], "words": json.loads(json.dumps(words, default=str)[:20_000]), "notes": str(one.get("notes") or "")[:4000]})
	return out


def _headline(one: dict) -> str:
	words = one["words"]
	return str(words.get("title") or words.get("quote") or words.get("left") or "")[:120]


def draft_deck(
	presentation: Annotated[str, "The presentation's id."],
	slides: Annotated[
		list[dict],
		"The slides in order, each {kind, words, notes}. kind is one of the kinds the page lists; words are the "
		"kind's words (the page says which); notes are what the speaker says. A value that comes from a record is "
		"written as its chip, such as {this.grand_total}, never typed.",
	],
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a whole deck as a card the reader approves: each slide built
	in the business's colour from One's kinds of slide, added after the
	slides there are (or in place of a blank first one). Read the records
	it is about first, and put chips where a value comes from a record."""
	from onedesk.one_ai import proposals
	from onedesk.one_slide import decks

	item = _readable(presentation)
	if not item:
		return {"error": f"No presentation the reader may open is {presentation}."}
	try:
		api._may(presentation, "write")
	except frappe.PermissionError:
		return {"error": "The reader may not change this presentation."}
	cleaned = _cleaned_slides(slides)
	if isinstance(cleaned, str):
		return {"mend": "draft_deck", "error": cleaned}
	kinds = decks.kind_labels()
	changes = {
		"what": "deck",
		"title": _("Write {0} slides in {1}").format(len(cleaned), item["file_name"]),
		"presentation": presentation,
		"slides": cleaned,
		"summary": [{"label": f"{at}. {kinds.get(one['kind'], one['kind'])}", "value": _headline(one)} for at, one in enumerate(cleaned, start=1)],
	}
	return {
		"proposal": proposals.propose("Setup", api.PRESENTATION, changes=changes, record=presentation, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it writes. Nothing changes until they approve it.",
	}


def write_slide(
	presentation: Annotated[str, "The presentation's id."],
	slide: Annotated[str, "The slide's id (or its number), from read_presentation or the page."],
	texts: Annotated[dict, "New words for the slide's texts, by element id: {id: words}, lines split by \\n."],
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest new words for a slide, keeping each text's look: to rewrite,
	shorten, translate or fix it. Read it first."""
	from onedesk.one_ai import proposals

	item = _readable(presentation)
	if not item:
		return {"error": f"No presentation the reader may open is {presentation}."}
	try:
		api._may(presentation, "write")
	except frappe.PermissionError:
		return {"error": "The reader may not change this presentation."}
	row = _row(frappe.get_doc(api.PRESENTATION, presentation), slide)
	if not row:
		return {"mend": "write_slide", "error": f"No slide {slide} in that presentation; read_presentation lists them."}
	texts = frappe.parse_json(texts) if isinstance(texts, str) else texts
	held = {one["id"]: one["text"] for one in _said_on(row.elements)}
	if not isinstance(texts, dict) or not texts or set(texts) - set(held):
		return {"mend": "write_slide", "error": f"texts is {{id: words}} for the slide's texts, whose ids are {', '.join(held)}."}
	texts = {key: str(value)[:4000] for key, value in texts.items()}
	changes = {
		"what": "slide",
		"title": _("Rewrite slide {0} in {1}").format(row.idx, item["file_name"]),
		"presentation": presentation,
		"slide": row.client_id,
		"texts": texts,
		"summary": [{"label": held[key][:80], "value": value[:200]} for key, value in texts.items()],
	}
	return {
		"proposal": proposals.propose("Setup", api.PRESENTATION, changes=changes, record=presentation, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it changes. Nothing changes until they approve it.",
	}


def remake_slide(
	presentation: Annotated[str, "The presentation's id."],
	slide: Annotated[str, "The slide's id (or its number)."],
	kind: Annotated[str, "The kind of slide to make it, such as timeline or figures."],
	words: Annotated[dict, "The kind's words, from what the slide says now."],
	notes: Annotated[str, "What the speaker says, if it changes."] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a slide made again as another kind of slide, with its words
	carried over: a list into a timeline, numbers into figures."""
	from onedesk.one_ai import proposals
	from onedesk.one_slide import decks

	item = _readable(presentation)
	if not item:
		return {"error": f"No presentation the reader may open is {presentation}."}
	try:
		api._may(presentation, "write")
	except frappe.PermissionError:
		return {"error": "The reader may not change this presentation."}
	row = _row(frappe.get_doc(api.PRESENTATION, presentation), slide)
	if not row:
		return {"mend": "remake_slide", "error": f"No slide {slide} in that presentation; read_presentation lists them."}
	cleaned = _cleaned_slides([{"kind": kind, "words": frappe.parse_json(words) if isinstance(words, str) else words, "notes": notes or row.notes or ""}])
	if isinstance(cleaned, str):
		return {"mend": "remake_slide", "error": cleaned}
	changes = {
		"what": "remake",
		"title": _("Make slide {0} a {1}").format(row.idx, decks.kind_labels().get(kind, kind)),
		"presentation": presentation,
		"slide": row.client_id,
		**cleaned[0],
		"summary": [{"label": _("Slide {0}").format(row.idx), "value": _headline(cleaned[0])}],
	}
	return {
		"proposal": proposals.propose("Setup", api.PRESENTATION, changes=changes, record=presentation, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it changes. Nothing changes until they approve it.",
	}


def _built(presentation: str, one: dict) -> tuple[str, str]:
	"""A kind of slide built in the business's colour at the presentation's
	size: its background and elements, as kept."""
	from onedesk.one_slide import decks, resize

	drawn = decks.build(one["kind"], one["words"], decks.brand())
	elements = drawn["elements"]
	width, height = api.frame(presentation)
	if (width, height) != (decks.WIDE, decks.HIGH):
		elements = resize.scaled(elements, width / decks.WIDE, height / decks.HIGH)
	return drawn["background"], play.cleaned(elements)


def approved(changes: dict) -> str:
	"""A presentation card approved, as the person who pressed Approve. What
	the slides were is kept as a version first; an open editor reloads."""
	from frappe.utils import escape_html

	from onedesk.one_slide import layouts, versions

	name = changes["presentation"]
	api._may(name, "write")
	doc = frappe.get_doc(api.PRESENTATION, name)
	versions.keep_now(doc, _("Before OneAI wrote slides"))
	if changes["what"] == "deck":
		blank = len(doc.slides) == 1 and not _said_on(doc.slides[0].elements)
		if blank:
			doc.slides = []
		for one in changes["slides"]:
			background, elements = _built(name, one)
			doc.append("slides", {"client_id": uuid.uuid4().hex[:10], "background": background, "elements": elements, "notes": one.get("notes") or "", "kind": one["kind"], "transition": "Fade", "transition_duration": 0.6})
	else:
		row = _row(doc, changes["slide"])
		if not row:
			frappe.throw(_("Could not change the slide: it is no longer in the presentation."))
		if changes["what"] == "slide":
			drawn = json.loads(row.elements or "[]")
			for one in drawn:
				said = changes["texts"].get(one.get("id")) if isinstance(one, dict) else None
				if said is not None:
					one["content"] = layouts.poured(one["content"], "".join(f"<p>{escape_html(line)}</p>" for line in said.split("\n")))
			row.elements = json.dumps(drawn)
		else:
			row.background, row.elements = _built(name, changes)
			row.kind, row.notes = changes["kind"], changes.get("notes") or row.notes
	doc.save(ignore_permissions=True)
	frappe.publish_realtime("one_slide_written", {"presentation": name}, user=frappe.session.user, after_commit=True)
	return name


def page(said: dict) -> str | None:
	"""The sentence the model is told on a presentation's page: which one,
	its slides, the record it is on and its chips, the kinds of slide and
	deck it can follow, and the slide the reader has open."""
	from onedesk.one_slide import data, decks

	if said.get("page") != "presentation":
		return None
	name = (said.get("record") or "").strip()
	item = _readable(name) if name else None
	if not item:
		return "The reader is on a presentation's page in OneSlide."
	read = read_presentation(name)
	shown = "; ".join(f'{one["number"]}. {(one["texts"][0]["text"] if one["texts"] else "(blank)")[:80]}' for one in read["slides"])
	where = f'The reader has the presentation "{item["file_name"]}" open in OneSlide (its id is {name}); its slides are: {shown[:MOST_SEEN]}'
	if item.get("attached_to_doctype") and item.get("attached_to_name"):
		where += f'. It is filed on {item["attached_to_doctype"]} {item["attached_to_name"]}; read that record and what it links to before writing about it'
	sources = data.cleaned(frappe.db.get_value(api.PRESENTATION, name, "sources"))
	if sources:
		where += ". Its words can come from records as chips, filled as whoever looks: " + "; ".join(
			f'{{{one["key"]}.field}} is {"a list of " if one["kind"] == "list" else ""}{one.get("doctype") or "the record it is filed on"}' for one in sources
		) + ' (a list also has {key.count}, {key.sum.field} and {key.1.field}); put a chip wherever a value comes from one'
	where += ". Kinds of slide and their words: " + "; ".join(f"{kind}: {words}" for kind, words in decks.WORDS.items())
	where += ". Decks One knows, as kinds in order: " + "; ".join(f'{key}: {", ".join(kind for kind, _w in held)}' for key, held in decks.DECKS.items())
	selected = said.get("selection") if isinstance(said.get("selection"), dict) else {}
	if selected.get("presentation") == name and selected.get("slide"):
		row = next((one for one in read["slides"] if one["id"] == selected["slide"]), None)
		if row:
			where += f'.\nThe reader has slide {row["number"]} open (its id is {row["id"]}), whose texts are {json.dumps(row["texts"])[:MOST_SEEN]}. A request about "this slide" means it'
	return where + (
		".\ndraft_deck writes a whole deck as a card; write_slide rewrites, shortens or translates a slide's words; "
		"remake_slide makes a slide another kind, such as a timeline."
	)
