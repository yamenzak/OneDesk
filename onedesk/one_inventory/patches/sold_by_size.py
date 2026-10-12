"""Measured By became Sold by Size, No, Length or Area (one_inventory/
measure.py). An item that said Piece says No, and one counted in a length or
an area is sold by it, as a new one is."""

import frappe

from onedesk.one_inventory.measure import unit_kind


def execute():
	frappe.db.sql(
		"""update `tabItem` set one_measured_by = 'No'
		where ifnull(one_measured_by, '') in ('', 'Piece')"""
	)
	for item in frappe.get_all("Item", filters={"one_measured_by": "No"}, fields=["name", "stock_uom"]):
		kind = unit_kind(item.stock_uom)
		if kind:
			frappe.db.set_value("Item", item.name, "one_measured_by", kind, update_modified=False)
