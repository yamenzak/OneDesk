"""Servers' cards are a view of the Workspace Server list now, beside List
and Report (one_interface/views.js), and its default, so the
`oneadmin-servers` page that drew them goes."""

import frappe


def execute():
	frappe.delete_doc("Page", "oneadmin-servers", ignore_missing=True, force=True, ignore_permissions=True)
