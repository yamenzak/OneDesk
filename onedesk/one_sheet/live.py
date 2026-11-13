"""Live co-editing's questions to the server: may this person into this
workbook's or document's room, and may they write? Asked by
realtime/handlers.js as the socket's own session, once a room; then told
every minute that they are still there, and when they leave, so the File's
lease (one_cloud/lease.py) knows who is in it. AGENTS.md, live.py.
"""

import json

import frappe

from onedesk.one_sheet import api

MOST_ROOMS = 20


def _held(kind: str):
	from onedesk.one_doc import api as writing

	return {"workbook": (api, api.WORKBOOK), "document": (writing, writing.DOCUMENT)}.get(kind)


def _item(kind: str, name: str) -> dict | None:
	held = _held(kind)
	if not held or not name or not frappe.db.exists(held[1], name):
		return None
	try:
		return held[0]._may(name, "read")
	except (frappe.PermissionError, frappe.DoesNotExistError):
		frappe.clear_last_message()
		return None


@frappe.whitelist()
def admit(kind: str, name: str, sid: str = "") -> dict:
	"""The room's name, who the person is, and whether they may change cells
	or text: never while somebody has the file alone in OneOS or on the
	drive, or while it opens read-only (one_cloud/saving.py)."""
	from onedesk.one_cloud import lease, opening, saving
	from onedesk.one_cloud import namespace as ns

	item = _item(kind, name)
	if not item:
		return {"ok": False}
	write = saving.state(_held(kind)[1], name, item, ns.may(item, "write"))["can_write"]
	lease.arrive(item["name"], sid, write, kind)
	if write:
		opening.redraw(item["name"])
	user = frappe.session.user
	return {
		"ok": True,
		"name": name,
		"write": write,
		"who": {
			"user": user,
			"fullName": frappe.utils.get_fullname(user),
			"image": frappe.db.get_value("User", user, "user_image") or "",
		},
	}


@frappe.whitelist()
def here(rooms: str, sid: str = "") -> None:
	"""The person's editor is still in these rooms ([[kind, name], …])."""
	from onedesk.one_cloud import lease, saving
	from onedesk.one_cloud import namespace as ns

	for kind, name in (json.loads(rooms or "[]") or [])[:MOST_ROOMS]:
		item = _item(kind, name)
		if item:
			lease.arrive(item["name"], sid, saving.state(_held(kind)[1], name, item, ns.may(item, "write"))["can_write"], kind)


@frappe.whitelist()
def leave(kind: str, name: str, sid: str = "") -> None:
	"""The person's editor left the room."""
	from onedesk.one_cloud import lease, opening

	item = _item(kind, name)
	if item:
		lease.leave(item["name"], sid)
		opening.redraw(item["name"])


def boot(bootinfo) -> None:
	"""extend_bootinfo: workbooks open live wherever the desk has its socket."""
	bootinfo.one_sheet_live = frappe.session.user != "Guest"
