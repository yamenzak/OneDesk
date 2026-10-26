"""The last of OneIntake's names go (docs/AICENTER.md, stage 4): its three
record types, its notifications and its switch take reading's names, and
the section One's sidebar kept for it goes. Run before the doctypes are
synced, so they are found under the names they now have."""

import json

import frappe

RECORDS = {
	"Intake Settings": "Reading Settings",
	"Intake Action": "Reading Action",
	"Intake Lesson": "Reading Lesson",
}

NOTIFICATIONS = {
	"Intake Waiting": "Documents Waiting",
	"Intake Waiting, One Thing": "Documents Waiting, One Thing",
	"Intake Weekly": "Documents Weekly",
}

HIDDEN = "one_hidden_apps"


def execute():
	for old, new in RECORDS.items():
		if frappe.db.exists("DocType", old) and not frappe.db.exists("DocType", new):
			frappe.rename_doc("DocType", old, new, force=True)
	for old, new in NOTIFICATIONS.items():
		if not frappe.db.exists("Notification Type", old):
			continue
		if frappe.db.exists("Notification Type", new):
			frappe.delete_doc("Notification Type", old, force=True, ignore_permissions=True)
		else:
			frappe.rename_doc("Notification Type", old, new, force=True)
	hidden = json.loads(frappe.db.get_default(HIDDEN) or "[]")
	if "OneIntake" in hidden:
		frappe.db.set_default(HIDDEN, json.dumps(["Reading" if one == "OneIntake" else one for one in hidden]))
	frappe.db.delete("Sidebar Item", {"parenttype": "Sidebar", "parent": "One", "type": "Section Break", "label": "OneIntake"})
	frappe.clear_cache()
