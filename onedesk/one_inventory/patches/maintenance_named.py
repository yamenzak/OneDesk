"""A service log names its asset (one_inventory/maintenance.py `named`), so
the list and the calendar say which pickup it is. The logs made before are
named once."""

import frappe


def execute():
	for log in frappe.get_all("Asset Maintenance Log", filters={"one_asset_title": ["is", "not set"]}, fields=["name", "asset_name"]):
		if log.asset_name:
			title = frappe.db.get_value("Asset", log.asset_name, "asset_name") or log.asset_name
			frappe.db.set_value("Asset Maintenance Log", log.name, "one_asset_title", title, update_modified=False)
