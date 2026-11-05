"""ERPNext's stock reports that it runs in the background, shown at once
instead, after every sync and migrate. ERPNext prepares them for stores
with millions of entries; a small business's open in a second, and frappe
turns preparing back on by itself for any report that runs too long
(Report.execute_script_report's watcher)."""

import frappe

AT_ONCE = ("Stock Balance", "Serial and Batch Wise Stock Balance", "Negative Batch Report")


def settle() -> None:
	for name in AT_ONCE:
		if frappe.db.get_value("Report", name, "prepared_report"):
			frappe.db.set_value("Report", name, "prepared_report", 0, update_modified=False)
