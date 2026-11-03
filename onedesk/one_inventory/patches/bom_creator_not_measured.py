"""ERPNext's BOM Creator is drawn on its design view now, which shows none of
a part's other fields, so a part is no longer measured there; the sizes are
on the BOM it makes (one_inventory/measure.py)."""

import frappe


def execute():
	for name in frappe.get_all(
		"Custom Field", filters={"dt": "BOM Creator Item", "fieldname": ["like", "one\\_%"]}, pluck="name"
	):
		frappe.delete_doc("Custom Field", name, ignore_permissions=True, force=True)
