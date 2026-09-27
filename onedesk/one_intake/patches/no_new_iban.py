"""New IBAN is no longer a notification: the bill it was about waits in
OneIntake instead (planning._hold_iban), and Intake Waiting says so. Its
type goes, and with it everybody's choice of it."""

import frappe


def execute():
	if frappe.db.exists("Notification Type", "New IBAN"):
		frappe.db.delete("Notification Type Preference", {"notification_type": "New IBAN"})
		frappe.delete_doc("Notification Type", "New IBAN", ignore_permissions=True, force=True)
