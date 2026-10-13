"""To Order was a report and is a page (one_inventory/page/to_order); the
report's record goes with its files."""

import frappe


def execute():
	frappe.delete_doc("Report", "To Order", ignore_missing=True, force=True)
