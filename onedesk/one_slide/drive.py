"""A presentation on the network drive: "Name.pptx", made from the record
each time it is read, and a save from PowerPoint, Keynote or LibreOffice
read back into the same presentation (AGENTS.md, On the drive)."""

import io
import json

import frappe
from frappe import _

from onedesk.one_slide import api, data, from_powerpoint, master, play, powerpoint, versions

SUFFIX = ".pptx"
CACHE = "one_slide_pptx"
KEPT_FOR = 600


def stamp(name: str) -> str:
	"""When what the file is made from last changed: the presentation, or its master."""
	held = [frappe.db.get_value(api.PRESENTATION, name, "modified")]
	under = master.of(name)
	if under:
		held.append(frappe.db.get_value(api.PRESENTATION, under, "modified"))
	return max(str(one or "") for one in held)


def _key(name: str) -> str:
	return f"{name}:{stamp(name)}:{frappe.session.user}"


def held(name: str) -> bytes | None:
	"""The file already made for this reader since the presentation last changed."""
	return frappe.cache.hget(CACHE, _key(name))


def pptx(name: str) -> bytes:
	"""`powerpoint.build` for the reader, kept until the presentation changes:
	words from records are filled as the reader may see them."""
	key = _key(name)
	made = frappe.cache.hget(CACHE, key)
	if made:
		return made
	made = powerpoint.build(name, frappe.session.user)[0]
	frappe.cache.hset(CACHE, key, made)
	frappe.cache.expire(CACHE, KEPT_FOR)
	return made


def lost_words(lost: list[int]) -> str:
	"""The slide numbers that lost something, as kept on the presentation. Pure."""
	return ", ".join(str(one) for one in sorted(set(lost)))


def write(name: str, content: bytes) -> list[int]:
	"""A save from the drive: the file's slides become the presentation's,
	its name, sharing, links and master kept, what it was kept as a version
	first, and the slides that had something the editor has nothing like
	noted on it for the editor to say. A presentation with words from
	records is not written from outside, which would keep the words and lose
	where they come from."""
	item = api._may(name, "write")
	if data.cleaned(frappe.db.get_value(api.PRESENTATION, name, "sources")):
		frappe.throw(_("A presentation with words from records can only be edited in OneSlide."), frappe.PermissionError)
	try:
		from pptx import Presentation as Deck

		Deck(io.BytesIO(content))
	except Exception:
		frappe.throw(_("This file is not a presentation."))
	width, height, slides, lost = from_powerpoint.read(
		content, lambda file_name, blob: api.MEDIA + api._kept(name, file_name, blob)["name"], mastered=bool(master.of(name))
	)
	versions._keep(name, _("Before a save from the drive"))
	doc = frappe.get_doc(api.PRESENTATION, name)
	doc.width, doc.height = round(width), round(height)
	doc.set("slides", [{**one, "background": play.background(one["background"]), "elements": play.cleaned(json.dumps(one["elements"]))} for one in slides])
	doc.byte_size = sum(len(row.elements or "") for row in doc.slides)
	doc.lost = lost_words(lost)
	doc.save(ignore_permissions=True)
	frappe.db.set_value("File", item["name"], "file_size", doc.byte_size, update_modified=True)
	return lost
