"""Sizes were millimetres, always; now a line says its size unit (one_size_uom),
from the item or the workspace (measure.size_unit). The workspace's is
millimetres until somebody changes it, and every line that already has a
size says millimetres, which is what it was typed in."""

import frappe

from onedesk.one_inventory.measure import LINES, SIZE_UNIT


def execute():
	if not frappe.db.get_single_value("Stock Settings", "one_size_uom"):
		frappe.db.set_single_value("Stock Settings", "one_size_uom", SIZE_UNIT)
	for doctype in LINES:
		if not frappe.db.table_exists(doctype) or not frappe.db.has_column(doctype, "one_size_uom"):
			continue
		frappe.db.sql(
			f"""update `tab{doctype}` set one_size_uom = %s
			where ifnull(one_size_uom, '') = '' and ifnull(one_length, 0) != 0""",
			SIZE_UNIT,
		)
