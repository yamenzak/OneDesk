"""A shift that starts at a one-digit hour was written "7:00:" on every request
already made; written again as the time it is."""

import frappe

from onedesk.one_hr import shift


def execute():
	if not frappe.get_meta("Shift Request").has_field("one_when"):
		return
	for name, kind in frappe.get_all("Shift Request", fields=["name", "shift_type"], as_list=True):
		frappe.db.set_value("Shift Request", name, "one_when", shift.hours(kind), update_modified=False)
