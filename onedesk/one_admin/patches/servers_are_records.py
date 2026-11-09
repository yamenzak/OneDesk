"""Servers were rows in Settings; each is now a record, named for itself."""

import frappe


def execute():
	for row in frappe.get_all("Workspace Server", fields=["name", "server", "tenant"]):
		cost = 12 if row.server == "admin" else 44 if row.tenant else 24
		frappe.db.set_value("Workspace Server", row.name, {"provider": "AWS", "status": "Up", "monthly_cost": cost}, update_modified=False)
		if row.name != row.server:
			frappe.rename_doc("Workspace Server", row.name, row.server, force=True)
