"""Ask in a workbook and Ask in a document were their own actions, each with
its own button in the editor. OneAI is asked in its panel now, which is told
what is selected, so the two actions go."""

import frappe


def execute():
	for key in ("sheet_assist", "doc_assist"):
		if frappe.db.exists("AI Action", key):
			frappe.delete_doc("AI Action", key, ignore_permissions=True, force=True)
