"""A next step's reminder is One's Next Step Due notification now
(next.due), so the frappe Reminders it used to make, not yet sent, go."""

import frappe


def execute():
	frappe.db.delete("Reminder", {"reminder_doctype": ["in", ["Lead", "Opportunity"]], "notified": 0})
