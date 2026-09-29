"""AI Usage's own total row is the only one: the site's copy of the report
kept frappe's as well, which added the report's total into itself."""

import frappe


def execute():
	frappe.db.set_value("Report", "AI Usage", "add_total_row", 0, update_modified=False)
