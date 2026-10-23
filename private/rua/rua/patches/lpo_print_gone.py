import frappe

from onedesk.one import layer

GONE = "Rua LPO"


def execute():
	"""Rua's own LPO print is gone: purchase orders print with One's again."""
	held = frappe.db.get_value("Property Setter", {"doc_type": "Purchase Order", "property": "default_print_format"}, "value")
	if held == GONE:
		layer.set_default("Purchase Order", "default_print_format", "One Purchase Order")
	if frappe.db.exists("Print Format", GONE):
		frappe.delete_doc("Print Format", GONE, ignore_permissions=True, force=True)
