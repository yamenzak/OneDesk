"""Marking a day by hand, for the days the clock did not answer."""

import frappe
from frappe.utils import getdate


@frappe.whitelist()
def clocked_in(date: str) -> list[str]:
	"""The employees with an IN log on `date`."""
	frappe.has_permission("Employee Checkin", "read", throw=True)

	rows = frappe.get_all(
		"Employee Checkin",
		filters=[
			["log_type", "=", "IN"],
			["skip_auto_attendance", "=", 0],
			["time", ">=", f"{getdate(date)} 00:00:00"],
			["time", "<=", f"{getdate(date)} 23:59:59"],
		],
		pluck="employee",
	)
	return sorted(set(rows))
