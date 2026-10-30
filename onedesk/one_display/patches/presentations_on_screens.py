"""A slide playlist plays presentations (stage 5 of docs/ONESLIDE.md). Each
picture, video and designed slide a playlist held becomes a one-slide
presentation filed on the playlist in OneCloud, and the row plays it."""

import json

import frappe


def execute():
	if not frappe.db.has_column("Display Slide", "design"):
		return
	rows = frappe.db.sql(
		"""select name, parent, kind, file, html, design, title from `tabDisplay Slide`
		where kind in ('Image', 'Video', 'Design') and parenttype = 'Slide Playlist'""",
		as_dict=True,
	)
	for row in rows:
		file = presentation(row)
		frappe.db.set_value(
			"Display Slide", row.name, {"kind": "Presentation", "presentation": file, "title": row.title or frappe.db.get_value("File", file, "file_name")}
		)


def presentation(row) -> str:
	"""The row's slide, as a presentation of one slide on its playlist."""
	from onedesk.one_slide import api

	return api.make_with(f"@records/Slide Playlist/{row.parent}", row.title or row.kind, [slide(row)])


def slide(row) -> dict:
	"""One playlist row as one Suite slide. Pure but for the converter's QR."""
	from frappe.utils.html_utils import sanitize_html

	from onedesk.one_slide import convert

	whole = {"id": "whole", "left": 0, "top": 0, "width": convert.WIDE, "height": convert.HIGH, "zIndex": 1, "opacity": 100}
	if row.kind == "Image":
		return {"background": "#000000FF", "elements": [{**whole, "type": "image", "src": row.file or ""}]}
	if row.kind == "Video":
		return {"background": "#000000FF", "elements": [{**whole, "type": "video", "src": row.file or "", "autoplay": True, "loop": True, "muted": True}]}
	if row.design:
		return convert.slide(json.loads(row.design))
	words = sanitize_html(row.html or "", always_sanitize=True)
	return {"background": "#000000FF", "elements": [{**whole, "type": "text", "content": words, "height": None}]}
