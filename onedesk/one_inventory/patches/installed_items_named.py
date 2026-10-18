"""An installation note's line keeps its item's name (`one_item_name`), which
it prints by; ERPNext's keeps only the code. Lines made before say it too."""

import frappe


def execute():
	frappe.db.sql(
		"""update `tabInstallation Note Item` line join `tabItem` item on item.name = line.item_code
		set line.one_item_name = item.item_name
		where ifnull(line.one_item_name, '') = ''"""
	)
