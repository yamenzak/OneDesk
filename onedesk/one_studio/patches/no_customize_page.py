"""The Customize page is gone: Custom Fields (Workspace Field) lists every
field, and a field is changed through OneAI. Frappe keeps a standard Page
whose folder is removed, so it is deleted here."""

import frappe


def execute():
	if frappe.db.exists("Page", "customize"):
		frappe.delete_doc("Page", "customize", force=True, ignore_permissions=True)
