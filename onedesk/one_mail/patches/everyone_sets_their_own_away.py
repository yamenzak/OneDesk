"""Everybody sets the out-of-office of the address the workspace issued
them: OneMail User's Out of Office becomes Their Own Address, unless the
workspace already chose more for it."""

import frappe


def execute():
	from onedesk.one import abilities

	if not frappe.db.exists("Role", "OneMail User") or not abilities.of_app("OneMail"):
		return
	held = abilities.of("OneMail", "OneMail User")
	if held.get("away", "none") == "none":
		abilities.save("OneMail", "OneMail User", {**held, "away": "own"})
