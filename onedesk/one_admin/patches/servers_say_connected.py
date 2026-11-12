"""A connected machine says so: until now only its provider, Oracle, told it
from a box OneAdmin ordered, and a machine on any cloud reports its own."""

import frappe


def execute():
	frappe.reload_doc("one_admin", "doctype", "workspace_server")
	for name in frappe.get_all("Workspace Server", filters={"provider": ("!=", "AWS")}, pluck="name"):
		frappe.db.set_value("Workspace Server", name, "connected", 1, update_modified=False)
	for name in frappe.get_all("Workspace Server", filters={"server": ("like", "machine-%")}, pluck="name"):
		frappe.db.set_value("Workspace Server", name, "connected", 1, update_modified=False)
