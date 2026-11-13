"""Pictures and videos dropped on a slide playlist (D3 of SCRATCHPAD.md).
Media reaches a screen only inside a presentation, so each file becomes a
presentation of one slide, the picture or video filling it, filed on the
playlist in OneCloud as the patch presentations_on_screens did, and a row
that plays it. Nobody opens an editor to show a photo."""

import mimetypes
import os
from typing import Annotated

import frappe
from frappe import _

DOCTYPE = "Slide Playlist"
MOST = 50


@frappe.whitelist(methods=["POST"])
def add_media(
	playlist: Annotated[str, "The slide playlist."],
	files: Annotated[str | list, "Files uploaded to the playlist, by name."],
) -> list[str]:
	"""Each picture or video a presentation of its own, played by a new row,
	the uploaded file kept only inside it."""
	from onedesk.one_display.patches.presentations_on_screens import slide
	from onedesk.one_deck import api, play

	doc = frappe.get_doc(DOCTYPE, playlist)
	doc.check_permission("write")
	names = frappe.parse_json(files) if isinstance(files, str) else files
	made = []
	for name in (names or [])[:MOST]:
		file = frappe.get_doc("File", name)
		if file.attached_to_doctype != DOCTYPE or file.attached_to_name != playlist:
			frappe.throw(_("{0} was not added to this playlist.").format(file.file_name), frappe.PermissionError)
		kind = (mimetypes.guess_type(file.file_name or "")[0] or "").split("/")[0]
		if kind not in ("image", "video"):
			frappe.throw(_("{0} is not a picture or a video.").format(file.file_name))
		content = file.get_content()
		if len(content) > api.MOST_MEDIA:
			frappe.throw(_("{0} is too large to show on a screen.").format(file.file_name))
		title = os.path.splitext(file.file_name or "")[0] or _("Picture")
		presentation = api.make_with(f"@records/{DOCTYPE}/{playlist}", title, [{"background": "#000000FF", "elements": []}])
		held = api.presentation_of(frappe.db.get_value("File", presentation, "file_url"))
		kept = api._kept(held, file.file_name, content)
		drawn = slide(frappe._dict(kind="Image" if kind == "image" else "Video", file=kept["file_url"]))
		row = frappe.get_doc(api.PRESENTATION, held).slides[0]
		row.db_set("elements", play.cleaned(drawn["elements"]))
		doc.append("slides", {"kind": "Presentation", "presentation": presentation, "title": title})
		file.delete(ignore_permissions=True)
		made.append(presentation)
	doc.save()
	return made
