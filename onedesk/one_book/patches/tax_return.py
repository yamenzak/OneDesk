"""The return any country can read is the Tax Return: it was named for VAT,
which only some countries charge. The report made under the old name goes."""

import frappe


def execute():
	if frappe.db.exists("Report", "VAT Return"):
		frappe.delete_doc("Report", "VAT Return", force=True, ignore_permissions=True)
