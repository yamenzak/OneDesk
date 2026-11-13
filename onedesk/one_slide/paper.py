"""A presentation as a PDF: one page a slide, each the picture the editor
drew of it, so the paper is what the screen showed; or with notes, an A4 page
a slide, its picture above and its speaker notes below as words that can be
found and selected. Kept in OneCloud beside the presentation, or on its
record, and opened from there. AGENTS.md, Paper.
"""

import base64
import html
import io
import re

import frappe
from frappe import _

from onedesk.one_slide import api

#: The most slides one PDF is made of, and the largest picture of one.
MOST_SLIDES = 300
MOST_PICTURE = 8 * 1024 * 1024

PICTURE = re.compile(r"^data:image/(webp|png|jpeg);base64,(.+)$", re.DOTALL)


def _drawn(pictures: list[str]) -> list:
	from PIL import Image

	drawn = []
	for one in pictures:
		match = PICTURE.match(one or "")
		if not match:
			frappe.throw(_("This is not a picture."))
		content = base64.b64decode(match.group(2), validate=True)
		if len(content) > MOST_PICTURE:
			frappe.throw(_("This picture is too large."))
		drawn.append(Image.open(io.BytesIO(content)).convert("RGB"))
	if not drawn:
		frappe.throw(_("There are no slides to print."))
	return drawn


def noted(pictures: list[str], notes: list[str]) -> str:
	"""The HTML of the notes pages: each slide's picture, its number and its
	notes, a page each. Pure but for Pillow."""
	parts = []
	for number, (picture, said) in enumerate(zip(_drawn(pictures), notes, strict=False), start=1):
		out = io.BytesIO()
		picture.save(out, "JPEG", quality=88)
		src = "data:image/jpeg;base64," + base64.b64encode(out.getvalue()).decode()
		words = html.escape(said or "")
		parts.append(
			f'<section><img src="{src}"><p class="number">{number}</p>'
			f'<div class="notes" dir="auto">{words}</div></section>'
		)
	return (
		'<!DOCTYPE html><html><head><meta charset="utf-8"><style>'
		"body{margin:0;font-family:Inter,'Noto Sans','Noto Sans Arabic','DejaVu Sans',sans-serif;color:#1f2328}"
		"section{page-break-after:always}section:last-child{page-break-after:auto}"
		"img{display:block;width:100%;border:1px solid #d0d7de}"
		".number{margin:6px 0 10px;font-size:9pt;color:#6e7781}"
		".notes{white-space:pre-wrap;font-size:12pt;line-height:1.5}"
		f"</style></head><body>{''.join(parts)}</body></html>"
	)


def notes_pages(pictures: list[str], notes: list[str]) -> bytes:
	"""The notes pages as one PDF, on A4."""
	from frappe.utils.pdf import get_pdf

	margins = {f"margin-{side}": "15mm" for side in ("top", "bottom", "left", "right")}
	return get_pdf(noted(pictures, notes), {"page-size": "A4", **margins})


def pages(pictures: list[str]) -> bytes:
	"""The pictures, a page each, as one PDF. Pure but for Pillow."""
	drawn = _drawn(pictures)
	out = io.BytesIO()
	# photographed at twice the slide's size, so a page is the slide at 96 to the
	# inch: an A4 presentation prints on A4
	drawn[0].save(out, "PDF", save_all=True, append_images=drawn[1:], resolution=192)
	return out.getvalue()


@frappe.whitelist(methods=["POST"])
def pdf(name: str, pictures: str | list, notes: int = 0) -> dict:
	"""The presentation as a PDF beside it in OneCloud, or on its record:
	the slides alone, or with `notes`, each slide above its speaker notes."""
	item = api._may(name, "read")
	pictures = frappe.parse_json(pictures) if isinstance(pictures, str) else pictures
	if len(pictures or []) > MOST_SLIDES:
		frappe.throw(_("This presentation has too many slides to print at once."))
	if int(notes or 0):
		said = [row.notes or "" for row in frappe.get_doc(api.PRESENTATION, name).slides]
		content = notes_pages(pictures, said)
		title = _("{0} with notes").format(item["file_name"]) + ".pdf"
	else:
		content = pages(pictures)
		title = f"{item['file_name']}.pdf"
	return beside(item, title, content)


def beside(item: dict, title: str, content: bytes) -> dict:
	"""A file made from a presentation, kept beside it in OneCloud or on its record."""
	from onedesk.one_cloud import api as cloud
	from onedesk.one_cloud import namespace as ns

	file = {"doctype": "File", "content": content, "is_private": 1}
	if item.get("attached_to_doctype") and item.get("attached_to_name"):
		file.update(attached_to_doctype=item["attached_to_doctype"], attached_to_name=item["attached_to_name"], file_name=title)
	else:
		where = item.get("folder") or ns.HOME
		file.update(folder=where, file_name=ns.unique_name(title, cloud._taken(where)))
	made = frappe.get_doc(file)
	made.flags.ignore_permissions = True
	made.insert()
	return {"name": made.name, "file_name": made.file_name, "url": made.file_url}
