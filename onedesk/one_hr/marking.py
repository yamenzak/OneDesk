"""Marking a day by hand, for the days the clock did not answer.

hrms's Employee Attendance Tool writes Attendance rows for a list of employees
on one date. Two things are added here.

`clocked_in` reads the ledger the tool ignores: who has an IN log on the date,
so a person does not have to be told what the passkey already proved. A log a
reviewer rejected carries `skip_auto_attendance` and is left out.

`mark` writes the same rows the tool writes, plus the three overtime fields.
They are read only on the form because the shift normally computes them from
the check-ins (`hrms/hr/doctype/employee_checkin`), so the manual lane has to
set them before the row is submitted. Overtime Slip then collects them: it
reads submitted Attendance where the status is Present and an Overtime Type is
set, which is the same row either way.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate

from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_time_difference

# What Overtime Slip looks for. Marking anything else with overtime would write
# a row no slip would ever collect.
OVERTIME_STATUS = "Present"


def _listify(value) -> list:
	if isinstance(value, str):
		value = json.loads(value)
	return value or []


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


def standard_hours(shift: str | None) -> float:
	"""A shift's own length, or the company's standard day.

	The same reading hrms takes from the shift when it computes overtime from
	the check-ins, so a hand-marked day and a clocked day agree.
	"""
	if shift:
		timings = frappe.db.get_value("Shift Type", shift, ["start_time", "end_time"], as_dict=True)
		if timings and timings.start_time is not None and timings.end_time is not None:
			return calculate_time_difference(timings.start_time, timings.end_time)
	return flt(frappe.db.get_single_value("HR Settings", "standard_working_hours"))


def _check_overtime(overtime_type: str, hours: float) -> None:
	most = flt(frappe.db.get_value("Overtime Type", overtime_type, "maximum_overtime_hours_allowed"))
	if most and hours > most:
		frappe.throw(
			_("{0} allows at most {1} overtime hours a day.").format(overtime_type, most),
			title=_("Too Much Overtime"),
		)


@frappe.whitelist(methods=["POST"])
def mark(
	employees: list | str,
	status: str,
	date: str,
	shift: str | None = None,
	late_entry: int | None = 0,
	early_exit: int | None = 0,
	overtime_type: str | None = None,
	overtime_hours: float | None = 0,
) -> int:
	"""Write one Attendance row per employee, with overtime if it was given."""
	frappe.has_permission("Attendance", "create", throw=True)

	employees = _listify(employees)
	overtime_hours = flt(overtime_hours)

	if overtime_type and status != OVERTIME_STATUS:
		frappe.throw(_("Overtime can only be recorded on a day marked {0}.").format(_(OVERTIME_STATUS)))
	if overtime_type and overtime_hours <= 0:
		frappe.throw(_("Enter the overtime hours."))
	if overtime_type:
		_check_overtime(overtime_type, overtime_hours)

	for employee in employees:
		attendance = frappe.get_doc(
			doctype="Attendance",
			employee=employee,
			attendance_date=getdate(date),
			status=status,
			late_entry=late_entry,
			early_exit=early_exit,
			shift=shift,
		)
		if overtime_type:
			attendance.overtime_type = overtime_type
			attendance.actual_overtime_duration = overtime_hours
			attendance.standard_working_hours = standard_hours(shift)
		attendance.insert()
		attendance.submit()

	return len(employees)
