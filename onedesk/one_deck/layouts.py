"""Slides that remember the layout they came from, so a template's new look
can be brought into them again with their words kept (AGENTS.md, Master and
layouts)."""

import copy
import json
import re
from typing import Annotated

import frappe
from frappe import _

BLOCK = re.compile(r"<(p|h[1-6])(\s[^>]*)?>.*?</\1>", re.S)
LIST = re.compile(r"<(ul|ol)[\s>]", re.I)


def ref(template: str, client_id: str) -> str:
	return f"{template}:{client_id}"


def _words(html: str) -> list[str]:
	"""Each paragraph's words, as plain text. Pure."""
	from frappe.utils import strip_html

	found = [strip_html(match.group(0)).strip() for match in BLOCK.finditer(html or "")]
	return found or [strip_html(html or "").strip()]


def poured(look: str, words: str) -> str:
	"""A text's words in another text's look: the look's first paragraph,
	once for each paragraph of `words`. A list keeps its own markup, since a
	paragraph's look says nothing about bullets. Pure."""
	from frappe.utils import escape_html

	pattern = BLOCK.search(look or "")
	if not pattern or LIST.search(words or "") or LIST.search(look or ""):
		return words
	block = pattern.group(0)
	out = []
	for said in _words(words):
		done = []

		def one(match, said=said, done=done):
			if done:
				return "><"
			done.append(True)
			return f">{escape_html(said)}<"

		filled = re.sub(r">[^<]+<", one, block)
		out.append(filled if done else block.replace("</", f"{escape_html(said)}</", 1))
	return "".join(out)


def restyled(own: list[dict], layout: list[dict]) -> tuple[list[dict], int]:
	"""A slide's elements with the layout's look brought in, and how many
	took it. `layout` is already at the slide's size. Pure."""
	by_id = {one.get("id"): one for one in layout if isinstance(one, dict)}
	out, changed = [], 0
	for one in own:
		source = by_id.get(one.get("from")) if isinstance(one, dict) else None
		if not source or source.get("type") != one.get("type"):
			out.append(one)
			continue
		new = copy.deepcopy(source)
		new["id"], new["from"] = one["id"], one["from"]
		if one.get("type") == "text":
			new["content"] = poured(source.get("content") or "", one.get("content") or "")
		for key in ("src", "poster", "attrs", "name", "hidden", "locked", "connector"):
			if key in one:
				new[key] = one[key]
			else:
				new.pop(key, None)
		changed += new != one
		out.append(new)
	return out, changed


@frappe.whitelist(methods=["POST"])
def restyle(name: Annotated[str, "The presentation whose slides take their layouts' look again."]) -> dict:
	"""Bring every slide's layout's look in again, keeping its words. What it
	was is kept as a version first."""
	from onedesk.one_deck import api, resize, versions

	api._may(name, "write")
	doc = frappe.get_doc(api.PRESENTATION, name)
	size = api.frame(name)
	templates, restyled_slides = {}, 0
	plan = []
	for row in doc.slides:
		template, _sep, client_id = (row.get("layout") or "").partition(":")
		if not template or not client_id:
			continue
		if template not in templates:
			templates[template] = _layouts(template)
		layout = templates[template].get(client_id)
		if not layout:
			continue
		drawn = json.loads(layout["elements"] or "[]")
		before = (layout["width"], layout["height"])
		if before != size:
			drawn = resize.scaled(drawn, size[0] / before[0], size[1] / before[1])
		own, changed = restyled(json.loads(row.elements or "[]"), drawn)
		background = layout["background"] or row.background
		if changed or background != row.background:
			plan.append((row, own, background))
	if not plan:
		return {"restyled": 0}
	versions.keep_now(doc, _("Before restyling from layouts"))
	for row, own, background in plan:
		row.elements = json.dumps(own)
		row.background = background
		restyled_slides += 1
	doc.save(ignore_permissions=True)
	return {"restyled": restyled_slides}


def _layouts(template: str) -> dict:
	"""A template's slides by client_id, if the reader may use it."""
	from onedesk.one_deck import api, decks

	if decks.deck_of(template):
		# a deck One ships is read as it is built now, in the business's brand
		rows = decks.slides(decks.deck_of(template))
		return {row["client_id"]: {**row, "width": decks.WIDE, "height": decks.HIGH} for row in rows}
	held = frappe.db.get_value(api.PRESENTATION, template, ["is_template", "width", "height"], as_dict=True)
	if not held or not held.is_template:
		return {}
	if template not in api._system():
		try:
			api._may(template, "read")
		except (frappe.PermissionError, frappe.DoesNotExistError):
			return {}
	rows = frappe.get_all(
		api.SLIDE,
		filters={"parent": template, "parenttype": api.PRESENTATION},
		fields=["client_id", "elements", "background"],
	)
	return {row.client_id: {**row, "width": held.width or 960, "height": held.height or 540} for row in rows if row.client_id}
