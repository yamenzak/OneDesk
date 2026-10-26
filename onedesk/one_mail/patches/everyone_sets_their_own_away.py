"""Everybody sets the out-of-office of the address the workspace issued
them: OneMail User's Out of Office becomes Their Own Address, unless the
workspace already chose more for it."""

import frappe


def execute():
	from onedesk.one import rights

	if not frappe.db.exists("Role", "OneMail User") or not rights.of_app("OneMail"):
		return
	held = rights.of("OneMail", "OneMail User")
	if held.get("away", "none") == "none":
		rights.save("OneMail", "OneMail User", {**held, "away": "own"})
