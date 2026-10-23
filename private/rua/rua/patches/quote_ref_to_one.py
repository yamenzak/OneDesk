import frappe


def execute():
	"""Supplier's Quote No moved into One (one_quote_ref): what Rua's own
	field held is copied over, and Rua's field goes."""
	if frappe.db.has_column("Purchase Order", "rua_quote_ref") and frappe.db.has_column("Purchase Order", "one_quote_ref"):
		frappe.db.sql(
			"""update `tabPurchase Order` set one_quote_ref = rua_quote_ref
			where ifnull(rua_quote_ref, '') != '' and ifnull(one_quote_ref, '') = ''"""
		)
	if frappe.db.exists("Custom Field", "Purchase Order-rua_quote_ref"):
		frappe.delete_doc("Custom Field", "Purchase Order-rua_quote_ref", ignore_permissions=True, force=True)
