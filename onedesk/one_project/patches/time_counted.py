"""Projects made before a project said how its time is counted were counted
by timesheets, so that's what they keep (hours.py)."""

import frappe


def execute():
	if not frappe.db.has_column("Project", "one_time"):
		return
	frappe.db.sql("update `tabProject` set one_time = 'Timesheets' where ifnull(one_time, '') = ''")
	if not frappe.db.get_single_value("Projects Settings", "one_time_default"):
		frappe.db.set_single_value("Projects Settings", "one_time_default", "Timesheets")
