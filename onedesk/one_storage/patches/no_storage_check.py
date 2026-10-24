"""The Storage Check is gone: the control plane links storage, and files left
on the disk move by themselves (store.daily). Frappe keeps a standard Report
whose folder is removed, so it is deleted here."""

import frappe


def execute():
	if frappe.db.exists("Report", "Storage Check"):
		frappe.delete_doc("Report", "Storage Check", force=True, ignore_permissions=True)
