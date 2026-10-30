"""Designed slides: a slide drawn as blocks on a 1920 × 1080 canvas, kept
as JSON on the slide. What a block may hold is blocks.py's; the drawing is
public/js/one_display/blocks.js, the same on the screen and in the designer
(frontend/src/display/designer/). This file reads and writes a playlist's
slides for the designer."""

import json
from typing import Annotated

import frappe
from frappe import _
from frappe.utils import cint

from onedesk.one_display import blocks

DOCTYPE = "Slide Playlist"
KEPT = ("kind", "title", "duration", "fit", "file", "url", "from_date", "to_date", "paused")

clean = blocks.clean


def qrs(design: dict) -> dict:
	"""Every QR code a design draws, as SVG by the address it opens: drawn
	here, so neither a screen nor the designer needs a QR library."""
	from onedesk.one_display.programme import _qr

	links = {one["link"] for one in design.get("blocks") or [] if one.get("kind") == "qr" and one.get("link")}
	return {link: _qr(link) for link in links}


def _row(row) -> dict:
	design = None
	if row.kind == "Design" and row.get("design"):
		try:
			design = clean(row.design)
		except ValueError:
			design = None
	return {
		"id": row.name,
		**{key: row.get(key) for key in KEPT},
		"design": design,
		"html": row.html if row.kind == "Design" and not design else None,
	}


@frappe.whitelist()
def get(playlist: Annotated[str, "The slide playlist."]) -> dict:
	"""A playlist's slides as the designer draws them."""
	doc = frappe.get_doc(DOCTYPE, playlist)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"writable": doc.has_permission("write"),
		"slides": [_row(row) for row in doc.slides],
		"schema": blocks.described(),
	}


@frappe.whitelist(methods=["POST"])
def save(
	playlist: Annotated[str, "The slide playlist."],
	slides: Annotated[str | list, "Its slides, in order, in the shape get() gives."],
	loaded: Annotated[str | list | None, "The ids of the slides the designer was given."] = None,
) -> dict:
	"""Write the designer's slides over the playlist's, keeping each row it
	knows by its id. A slide
	added since the designer loaded (a video OneAI made meanwhile) is kept at
	the end rather than lost."""
	doc = frappe.get_doc(DOCTYPE, playlist)
	doc.check_permission("write")
	given = json.loads(slides) if isinstance(slides, str) else slides
	seen = set((json.loads(loaded) if isinstance(loaded, str) else loaded) or [row.name for row in doc.slides])
	known = {row.name: row for row in doc.slides}
	rows = []
	for one in given or []:
		values = {key: one.get(key) for key in KEPT}
		if values["kind"] not in ("Image", "Video", "Web Page", "Design"):
			frappe.throw(_("A slide is a picture, a video, a page or a design."))
		values["duration"] = cint(values["duration"]) or None
		if values["kind"] == "Design" and one.get("design"):
			values["design"] = json.dumps(clean(one["design"]), ensure_ascii=False)
		row = known.get(one.get("id"))
		if row:
			row.update(values)
			rows.append(row)
		else:
			rows.append(doc.append("slides", values))
	rows += [row for row in doc.slides if row.name not in seen and row not in rows]
	doc.set("slides", rows)
	doc.save()
	return get(playlist)


@frappe.whitelist()
def qr(link: Annotated[str, "What the code opens."]) -> str:
	"""A QR code as SVG, for the designer to draw while it is edited."""
	frappe.has_permission(DOCTYPE, "read", throw=True)
	from onedesk.one_display.programme import _qr

	return _qr((link or "")[:1000]) if link else ""


def drawn(doc, method=None) -> None:
	"""A designed slide keeps only what blocks.py allows, and no HTML of its
	own: the screen draws it from its blocks (Slide Playlist's validate)."""
	for row in doc.slides:
		if row.kind == "Design" and row.get("design"):
			row.design = json.dumps(clean(row.design), ensure_ascii=False)
			row.html = None
