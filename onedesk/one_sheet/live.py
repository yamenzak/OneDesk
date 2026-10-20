"""Live co-editing's one question to the server: may this person into this
workbook's room, and may they write? Asked by realtime/handlers.js as the
socket's own session, once a room. README, live.py.
"""

import frappe

from onedesk.one_sheet import api


@frappe.whitelist()
def admit(kind: str, name: str) -> dict:
	"""The room's name, who the person is, and whether they may change cells."""
	from onedesk.one_storage import namespace as ns

	if kind != "workbook" or not frappe.db.exists(api.WORKBOOK, name):
		return {"ok": False}
	try:
		item = api._may(name, "read")
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
	"""extend_bootinfo: workbooks open live wherever the desk has its socket,
	and offer Ask where OneAI may answer."""
	from onedesk.one import account, apps

	bootinfo.one_sheet_live = frappe.session.user != "Guest"
	bootinfo.ai_assist_enabled = bootinfo.one_sheet_live and apps.ai_on() and account.configured()
