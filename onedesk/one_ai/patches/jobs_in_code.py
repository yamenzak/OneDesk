"""What OneAI does and is told is code now (one_ai/jobs.py, docs/AICENTER.md),
so the action records and each workspace's choices for them are removed, with
the notification that told of a change to them."""

import frappe


def execute():
	for doctype in ("AI Action Setting", "AI Action"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
	if frappe.db.exists("Notification Type", "OneAI Changed"):
		frappe.delete_doc("Notification Type", "OneAI Changed", force=True, ignore_permissions=True)
