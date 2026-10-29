"""A task opens on its form now, with a head (one_task/heads.py), so
OneTask's own page of one is gone."""

import frappe


def execute():
	if frappe.db.exists("Page", "task-view"):
		frappe.delete_doc("Page", "task-view", force=True, ignore_permissions=True)
