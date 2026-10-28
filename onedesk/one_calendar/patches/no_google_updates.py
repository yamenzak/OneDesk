"""Google Calendar sync is gone, so the notification that told of its updates
goes with it."""

import frappe


def execute():
	if frappe.db.exists("Notification Type", "Google Calendar Updates"):
		frappe.delete_doc("Notification Type", "Google Calendar Updates", force=True, ignore_permissions=True)
