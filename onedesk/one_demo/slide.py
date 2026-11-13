"""A presentation in the company's files: the tender presentation for the
Bayview tower facade, four slides on the Light theme's own layouts, so the
demo opens on a deck that looks like somebody made it. Shared with Karim."""

import json
import uuid

import frappe

from onedesk.one_demo.base import as_user
from onedesk.one_slide import api, setup

OWNER = "wsadmin@one.test"
CHECKER = "karim@one.test"
NAME = "bayview-pitch"
TITLE = "Bayview tower facade"

#: Each slide: the Light theme's layout it is drawn on, then what its text
#: boxes say in order; a list is the points of a bulleted box.
SLIDES = (
	(2, ("Bayview tower facade", "Tender presentation · Sahara Glass & Aluminium")),
	(5, ("What we will build", ["Unitised curtain wall, floors 2 to 18", "420 m² of double glazed units", "Mullions powder coated to RAL 7016"])),
	(5, ("Programme", ["Shop drawings in three weeks", "Forty-five working days on site", "Handover floor by floor from level 2"])),
	(4, ("Thank you", "Questions are welcome")),
)


def run(password=None):
	if not frappe.db.exists(api.PRESENTATION, NAME):
		_make()
	file = frappe.db.get_value(api.PRESENTATION, NAME, "file")
	if frappe.db.exists("User", CHECKER) and not frappe.db.exists("DocShare", {"share_doctype": "File", "share_name": file, "user": CHECKER}):
		frappe.share.add_docshare("File", file, CHECKER, read=1, write=1, notify=0, flags={"ignore_share_permission": True})


def _make():
	from onedesk.one_cloud import namespace as ns

	layouts = setup.system()[0]["slides"]
	with as_user(OWNER):
		doc = frappe.get_doc({"doctype": api.PRESENTATION, "title": TITLE, "theme": api.LIGHT})
		for layout, words in SLIDES:
			row = layouts[layout]
			doc.append(
				"slides",
				{"client_id": str(uuid.uuid4()), "background": row["background"], "elements": json.dumps(_said(json.loads(row["elements"]), words))},
			)
		doc.flags.ignore_permissions = True
		doc.insert(set_name=NAME)
		file = frappe.get_doc({"doctype": "File", "file_url": api.URL + NAME, "is_private": 1, "folder": ns.HOME, "file_name": TITLE})
		file.flags.ignore_permissions = True
		file.insert()
		doc.db_set("file", file.name)


def _said(elements: list, words) -> list:
	"""The layout's text boxes, saying `words` in their own styles."""
	texts = iter(words)
	for one in elements:
		if one.get("type") != "text":
			continue
		said = next(texts, None)
		if said is None:
			continue
		one["id"] = uuid.uuid4().hex[:9]
		one["content"] = _bullets(one["content"], said) if isinstance(said, list) else _retold(one["content"], said)
	return elements


def _retold(html: str, said: str) -> str:
	"""The first run of words in a layout's box, replaced; its style kept."""
	start = html.index(">", html.index("<span")) + 1
	end = html.index("</span>", start)
	inner = html[start:end]
	words = inner.replace("<strong>", "").replace("</strong>", "")
	return html[:start] + inner.replace(words, frappe.utils.escape_html(said)) + html[end:]


def _bullets(html: str, points: list) -> str:
	item = html[html.index("<li") : html.index("</li>") + len("</li>")]
	return "<ul>" + "".join(_retold(item, point) for point in points) + "</ul>"
