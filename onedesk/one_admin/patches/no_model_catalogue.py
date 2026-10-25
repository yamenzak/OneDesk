"""The model catalogue goes: models are code now (one_ai/models.py,
docs/AICENTER.md). Its two record types are removed from the database."""

import frappe


def execute():
	for doctype in ("AI Model", "AI Model Rate"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
