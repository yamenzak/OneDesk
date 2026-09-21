"""Marking a day by hand, for the days the clock did not answer.

hrms's Employee Attendance Tool lists everyone with no Attendance row on a date
and writes one for whoever is ticked. It does that well; the one thing it never
reads is the ledger next to it. `clocked_in` answers who has an IN log on the
date, so a day that is half clocked and half asserted is not retyped.

A log a reviewer rejected in the review queue carries `skip_auto_attendance`
and is left out, so refusing a check-in there also keeps it out of the marking.

Overtime is not here: it belongs to one employee on one day rather than to a
list, and lives in `one_hr/overtime.py`.
"""

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
