"""OneAdmin's Home was frappe's `One Admin` workspace, with four number cards
and three quick lists. It is the `oneadmin` page now (one_admin/home.py),
because frappe offers every workspace to Workspace Manager and a page's roles
are its own. The workspace and its cards go from sites that had them."""

import frappe

CARDS = ("Workspaces", "Building", "Owing", "Stuck")


def execute():
	if frappe.db.exists("Workspace", "One Admin"):
		frappe.delete_doc("Workspace", "One Admin", force=True, ignore_permissions=True)
	for name in CARDS:
		if frappe.db.get_value("Number Card", name, "module") == "One Admin":
			frappe.delete_doc("Number Card", name, force=True, ignore_permissions=True)
