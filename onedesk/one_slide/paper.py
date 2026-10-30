"""A presentation as a PDF: one page a slide, each the picture the editor
drew of it, so the paper is what the screen showed. Kept in OneCloud beside
the presentation, or on its record, and opened from there. AGENTS.md, Paper.
"""

import base64
import io
import re

import frappe
from frappe import _

from onedesk.one_slide import api

#: The most slides one PDF is made of, and the largest picture of one.
MOST_SLIDES = 300
MOST_PICTURE = 8 * 1024 * 1024

PICTURE = re.compile(r"^data:image/(webp|png|jpeg);base64,(.+)$", re.DOTALL)


def pages(pictures: list[str]) -> bytes:
	"""The pictures, a page each, as one PDF. Pure but for Pillow."""
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
	out = io.BytesIO()
	drawn[0].save(out, "PDF", save_all=True, append_images=drawn[1:], resolution=144)
	return out.getvalue()


@frappe.whitelist(methods=["POST"])
def pdf(name: str, pictures: str | list) -> dict:
	"""The presentation as a PDF beside it in OneCloud, or on its record."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	item = api._may(name, "read")
	pictures = frappe.parse_json(pictures) if isinstance(pictures, str) else pictures
	if len(pictures or []) > MOST_SLIDES:
		frappe.throw(_("This presentation has too many slides to print at once."))
	content = pages(pictures)
	title = f"{item['file_name']}.pdf"
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
