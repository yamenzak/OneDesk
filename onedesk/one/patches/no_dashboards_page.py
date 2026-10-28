"""Dashboards left One: each app's are on its own rail, and they are made and
changed in OneStudio, so One's page of every dashboard is gone."""

import frappe


def execute():
	if frappe.db.exists("Page", "dashboards"):
		frappe.delete_doc("Page", "dashboards", force=True, ignore_permissions=True)
