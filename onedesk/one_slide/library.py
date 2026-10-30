"""The slide library: One's shelf, a slide of every kind from the decks One
ships (decks.py), and the company's, slides a manager kept with Save to
Library (AGENTS.md, Decks and the library)."""

import json
import uuid
from typing import Annotated

import frappe
from frappe import _

#: Where the company's shelf is kept: a template presentation no theme list shows.
KEY = "one_slide_library"


def held() -> str | None:
	name = frappe.db.get_default(KEY)
	return name if name and frappe.db.exists("Presentation", name) else None


def _made() -> str:
	"""The company's shelf, made the first time a slide is kept on it."""
	from onedesk.one_slide import decks

	if held():
		return held()
	doc = frappe.get_doc({"doctype": "Presentation", "title": _("Slide Library"), "is_template": 1, "width": decks.WIDE, "height": decks.HIGH})
	doc.flags.ignore_permissions = True
	doc.insert()
	frappe.db.set_default(KEY, doc.name)
	return doc.name


def _may_keep() -> bool:
	from onedesk.one import rights

	return rights.held("Presentation", "slide_template")


@frappe.whitelist()
@frappe.read_only()
def shelves() -> dict:
	"""Both shelves, each slide with its kind, ready to insert like a layout."""
	from onedesk.one_slide import decks

	look = decks.brand()
	one, seen = [], set()
	for deck in decks.DECKS:
		for row in decks.slides(deck, look):
			if row["kind"] in seen:
				continue
			seen.add(row["kind"])
			one.append(_item(decks.NAMES[deck], row["client_id"], row, decks.WIDE, decks.HIGH))
	one.sort(key=lambda item: decks.KINDS.index(item["kind"]))
	yours = []
	if held():
		width, height = frappe.db.get_value("Presentation", held(), ["width", "height"])
		for row in frappe.get_all(
			"Presentation Slide",
			filters={"parent": held(), "parenttype": "Presentation"},
			fields=["client_id", "background", "elements", "kind"],
			order_by="idx asc",
		):
			yours.append(_item(held(), row.client_id, row, width or decks.WIDE, height or decks.HIGH))
	return {"kinds": decks.kind_labels(), "one": one, "yours": yours, "may_keep": _may_keep()}


def _item(parent, client_id, row, width, height) -> dict:
	return {
		"parent": parent,
		"client_id": client_id,
		"background": row.get("background"),
		"elements": row.get("elements"),
		"kind": row.get("kind") or "",
		"width": width,
		"height": height,
		"thumbnail": "",
	}


@frappe.whitelist(methods=["POST"])
def keep(
	name: Annotated[str, "The presentation the slide is on."],
	client_id: Annotated[str, "The slide."],
	kind: Annotated[str, "Which kind of slide it is, one of the library's kinds."],
) -> dict:
	"""A slide put on the company's shelf, with copies of its pictures."""
	from onedesk.one_slide import api, decks, resize

	api._may(name, "read")
	if not _may_keep():
		frappe.throw(_("Your role doesn't keep slides in the library. Ask a workspace administrator."), frappe.PermissionError)
	if kind not in decks.KINDS:
		frappe.throw(_("There is no slide of that kind."))
	row = frappe.db.get_value("Presentation Slide", {"parent": name, "client_id": client_id}, ["background", "elements"], as_dict=True)
	if not row:
		frappe.throw(_("Could not keep the slide: save the presentation first."))
	shelf = frappe.get_doc("Presentation", _made())
	drawn = json.loads(row.elements or "[]")
	api._new_ids(drawn)
	for one in drawn:
		api._adopted(shelf.name, one)
	before, after = api.frame(name), (shelf.width or decks.WIDE, shelf.height or decks.HIGH)
	if before != after:
		drawn = resize.scaled(drawn, after[0] / before[0], after[1] / before[1])
	shelf.append("slides", {"client_id": str(uuid.uuid4()), "background": row.background, "elements": json.dumps(drawn), "kind": kind})
	shelf.save(ignore_permissions=True)
	return shelves()


@frappe.whitelist(methods=["POST"])
def forget(client_id: Annotated[str, "A slide on the company's shelf."]) -> dict:
	"""A slide taken off the company's shelf."""
	if not _may_keep():
		frappe.throw(_("Your role doesn't keep slides in the library. Ask a workspace administrator."), frappe.PermissionError)
	if held():
		shelf = frappe.get_doc("Presentation", held())
		shelf.set("slides", [row for row in shelf.slides if row.client_id != client_id])
		shelf.save(ignore_permissions=True)
	return shelves()
