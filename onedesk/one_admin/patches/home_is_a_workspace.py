"""OneAdmin's Home is frappe's `One Admin` workspace, as One's Home is: its
number cards, and what needs the operator as a Custom HTML Block. For a while
it was the `oneadmin` page, which goes, and the Stuck card is Failed now.
The workspace itself comes back from its file on migrate."""

import frappe


def execute():
	if frappe.db.exists("Page", "oneadmin"):
		frappe.delete_doc("Page", "oneadmin", force=True, ignore_permissions=True)
	if frappe.db.get_value("Number Card", "Stuck", "module") == "One Admin":
		frappe.delete_doc("Number Card", "Stuck", force=True, ignore_permissions=True)
