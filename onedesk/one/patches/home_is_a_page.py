"""One's Home is the `one` page, as OneHR's is `onehr`: what waits for the
reader in each app, the first few of each, and for administrators what in
the workspace needs them. The `One` workspace it replaces goes, with its
five number cards and the One Needs You block, which the page draws itself."""

import frappe

CARDS = ("Tasks Due or Late", "Meetings Today", "Documents Waiting", "OneAI Suggestions", "Approvals Waiting")


def execute():
	if frappe.db.get_value("Workspace", "One", "module") == "One":
		frappe.delete_doc("Workspace", "One", force=True, ignore_permissions=True)
	for name in CARDS:
		if frappe.db.get_value("Number Card", name, "module") == "One":
			frappe.delete_doc("Number Card", name, force=True, ignore_permissions=True)
	if frappe.db.exists("Custom HTML Block", "One Needs You"):
		frappe.delete_doc("Custom HTML Block", "One Needs You", force=True, ignore_permissions=True)
