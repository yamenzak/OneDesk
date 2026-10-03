"""A collection now sits in a group of its app's rail the administrator
chooses (record_types._place). Those made before are in Your Records, and a
group a rail layer added that has nothing left in it goes: OneCRM kept an
empty Your Records after its collection moved."""

import frappe

from onedesk.one_studio import record_types


def execute():
	frappe.reload_doc("one_studio", "doctype", "record_type")
	frappe.db.set_value(
		record_types.RECORD_TYPE, {"rail_group": ("is", "not set")}, "rail_group", record_types.YOUR_RECORDS
	)
	for name in frappe.get_all("Custom Sidebar", pluck="name"):
		layer = frappe.get_doc("Custom Sidebar", name)
		kept = record_types._without_empty_groups(layer.sidebar_items)
		if len(kept) != len(layer.sidebar_items):
			layer.set("sidebar_items", kept)
			layer.save(ignore_permissions=True)
