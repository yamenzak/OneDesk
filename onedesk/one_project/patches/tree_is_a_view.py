"""The Project Tree report goes: the Projects list's Tree view shows the same
tree (public/js/one_project/project_tree.js, tree.py `nodes`), and its rail row went
with it. A saved copy of the report goes too; nothing links to it."""

import frappe


def execute():
	if frappe.db.exists("Report", "Project Tree"):
		frappe.delete_doc("Report", "Project Tree", force=True, ignore_permissions=True)
