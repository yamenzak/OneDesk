"""Overtime, recorded on the day it was worked.

Overtime lives on the Attendance row: `overtime_type`, `actual_overtime_duration`
and `standard_working_hours`. A shift writes them from the check-ins when it
processes the day; `record` writes the same three when nobody clocked out, from
a dialog on the Employee or on the Attendance itself. Either way Overtime Slip
collects them later without knowing which hand wrote them, which is why there
is one place to record overtime rather than two.

The fields are read only on the form, and the row is already submitted by the
time anybody notices the overtime, so `record` writes them straight to the row
and leaves a comment saying who did it. Nothing downstream of Attendance is
posted at submit, so there is no ledger to disagree with.

`no_double_pay` is the other half of having one place: Overtime Slip lets a row
be typed with no Attendance behind it, and a period holding both would be paid
twice.
"""

import frappe
from frappe import _
from frappe.utils import flt, format_date, get_link_to_form, getdate

from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_time_difference

from onedesk.one_hr import policy

# The only status Overtime Slip collects.
COLLECTED = "Present"


def standard_hours(shift: str | None) -> float:
	"""A shift's own length, or the company's standard day.

	The reading hrms takes from the shift when it computes overtime from the
	check-ins, so a hand-recorded day and a clocked day agree.
	"""
	if shift:
		timings = frappe.db.get_value("Shift Type", shift, ["start_time", "end_time"], as_dict=True)
		if timings and timings.start_time is not None and timings.end_time is not None:
			return calculate_time_difference(timings.start_time, timings.end_time)
	return flt(policy.get("standard_working_hours"))


def _the_day(employee: str, date: str) -> dict | None:
	rows = frappe.get_all(
		"Attendance",
		filters={"employee": employee, "attendance_date": getdate(date), "docstatus": 1},
		fields=["name", "employee_name", "status", "shift", "overtime_type", "actual_overtime_duration"],
		limit=1,
	)
	return rows[0] if rows else None


@frappe.whitelist()
def day(employee: str, date: str) -> dict:
	"""What the dialog needs to know before it offers to write anything."""
	frappe.has_permission("Attendance", "read", throw=True)

	who = frappe.db.get_value("Employee", employee, "employee_name") or employee
	when = format_date(date)

	found = _the_day(employee, date)
	if not found:
		return {"ok": 0, "why": _("{0} has no attendance marked on {1}.").format(who, when)}
	if found.status != COLLECTED:
		return {
			"ok": 0,
			"why": _("{0} is marked {1} on {2}. Overtime is only paid on a day marked {3}.").format(
				who, _(found.status), when, _(COLLECTED)
			),
		}
	return {
		"ok": 1,
		"attendance": found.name,
		"standard_hours": standard_hours(found.shift),
		"overtime_type": found.overtime_type,
		"hours": found.actual_overtime_duration,
	}


@frappe.whitelist(methods=["POST"])
def record(employee: str, date: str, overtime_type: str, hours: float) -> str:
	"""Write the overtime onto the day, and say so in the record's comments."""
	frappe.has_permission("Attendance", "write", throw=True)

	hours = flt(hours)
	if hours <= 0:
		frappe.throw(_("Enter the overtime hours."))

	most = flt(frappe.db.get_value("Overtime Type", overtime_type, "maximum_overtime_hours_allowed"))
	if most and hours > most:
		frappe.throw(
			_("{0} allows at most {1} overtime hours a day.").format(overtime_type, most),
			title=_("Too Much Overtime"),
		)

	found = _the_day(employee, date)
	if not found or found.status != COLLECTED:
		frappe.throw(day(employee, date).get("why") or _("There is no day to record this against."))

	attendance = frappe.get_doc("Attendance", found.name)
	attendance.db_set(
		{
			"overtime_type": overtime_type,
			"actual_overtime_duration": hours,
			"standard_working_hours": standard_hours(found.shift),
		}
	)
	attendance.add_comment(
		"Comment",
		_("Overtime recorded by hand: {0} hours, {1}.").format(hours, overtime_type),
	)
	return attendance.name


def no_double_pay(doc, method=None) -> None:
	"""Refuse an Overtime Slip row that the day already carries.

	A row with a `reference_document` came from an Attendance and is the same
	figure. A row typed by hand for a date whose Attendance already says
	overtime is a second claim on one day's work.
	"""
	for row in doc.overtime_details:
		if row.reference_document or not row.date:
			continue
		found = _the_day(doc.employee, row.date)
		if found and found.overtime_type:
			frappe.throw(
				_("{0} already records {1} hours of overtime on {2}. Remove this row.").format(
					get_link_to_form("Attendance", found.name), found.actual_overtime_duration, row.date
				),
				title=_("Overtime Recorded Twice"),
			)
