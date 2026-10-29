"""My Tasks and the Inbox are frappe's Kanban now (one_task/board.py), so
OneTask's own page of them is gone."""

import frappe


def execute():
	if frappe.db.exists("Page", "my-tasks"):
		frappe.delete_doc("Page", "my-tasks", force=True, ignore_permissions=True)
