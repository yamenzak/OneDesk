"""Live co-editing's one question to the server: may this person into this
workbook's or document's room, and may they write? Asked by
realtime/handlers.js as the socket's own session, once a room. README,
live.py.
"""

import frappe

from onedesk.one_sheet import api


@frappe.whitelist()
def admit(kind: str, name: str) -> dict:
	"""The room's name, who the person is, and whether they may change cells
	or text."""
	from onedesk.one_storage import namespace as ns

	from onedesk.one_doc import api as writing

	held = {"workbook": api, "document": writing}.get(kind)
	if not held or not frappe.db.exists(held.WORKBOOK if kind == "workbook" else held.DOCUMENT, name):
		return {"ok": False}
	try:
		item = held._may(name, "read")
	except (frappe.PermissionError, frappe.DoesNotExistError):
		frappe.clear_last_message()
		return {"ok": False}
	user = frappe.session.user
	return {
		"ok": True,
		"name": name,
		"write": ns.may(item, "write"),
		"who": {
			"user": user,
			"fullName": frappe.utils.get_fullname(user),
			"image": frappe.db.get_value("User", user, "user_image") or "",
		},
	}


def boot(bootinfo) -> None:
	"""extend_bootinfo: workbooks open live wherever the desk has its socket."""
	bootinfo.one_sheet_live = frappe.session.user != "Guest"
