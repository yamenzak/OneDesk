"""Ready to Submit is a report now: frappe keeps a standard Page whose folder
is removed, so it is deleted here."""

import frappe


def execute():
	if frappe.db.exists("Page", "ready-to-submit"):
		frappe.delete_doc("Page", "ready-to-submit", force=True, ignore_permissions=True)
