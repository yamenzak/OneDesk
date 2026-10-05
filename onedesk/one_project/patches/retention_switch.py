"""Hold Retention is off for a new workspace. One already holding retention on
an order keeps it on, so nothing it uses goes away (retention.py)."""

import frappe


def execute():
	for doctype in ("Sales Order", "Purchase Order"):
		if frappe.db.has_column(doctype, "one_retention") and frappe.db.exists(
			doctype, {"one_retention": [">", 0], "docstatus": ["<", 2]}
		):
			frappe.db.set_single_value("Projects Settings", "one_retention", 1)
			return
