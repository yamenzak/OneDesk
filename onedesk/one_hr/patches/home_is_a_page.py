"""OneHR's Home is the `onehr` page, as OneCRM's is `onecrm`: everybody's day,
HR's figures and story, Today and the directory. The `OneHR` workspace it
replaces goes; its shortcuts are the page's three buttons, and its three
lists are Today."""

import frappe


def execute():
	if frappe.db.get_value("Workspace", "OneHR", "module") == "One HR":
		frappe.delete_doc("Workspace", "OneHR", force=True, ignore_permissions=True)
