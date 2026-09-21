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

The rest of this file is the slip itself. Three things about HRMS's screen are
worth knowing before reading it:

**Its Fetch button saved the document.** `get_emp_and_overtime_details` ends in
`self.save()`, so pressing Fetch on a new form inserted a real slip and left the
person looking at the unsaved blank one — press it twice and it answers that
"Overtime Slip: HR-OT-SLIP-00001 has been created" about a record nobody
knowingly made. `collect` reads the same attendance and *returns* it; the form
fills the grid and the person saves when they mean to.

**It never said what it would pay.** Everything on the screen is hours, and
submitting writes Additional Salary from the type's rate and multipliers. The
amount is worked out before the save and written onto the slip, using HRMS's own
`get_overtime_component_amounts` rather than a second copy of the arithmetic.

**It refused a slip for anybody with no salary structure**, because the only
thing it wanted the structure for was the payroll frequency that sets the two
dates. `dates` falls back to the calendar month, which is what a fixed hourly
rate needs and all it ever needed.
"""

import frappe
from frappe import _
from frappe.utils import flt, format_date, get_first_day, get_last_day, get_link_to_form, getdate

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


def before_validate(doc, method=None) -> None:
	"""Everything the screen used to leave for somebody to work out."""
	_dates(doc)
	_standard_hours(doc)
	doc.total_overtime_duration = sum(flt(row.overtime_duration) for row in doc.overtime_details)
	doc.one_amount, doc.one_pay_note = _payable(doc)


@frappe.whitelist()
def dates(employee: str, posting_date: str) -> dict:
	"""The period this slip covers, without refusing anybody.

	The payroll frequency where the employee has a salary structure, and the
	calendar month where they do not. HRMS threw here — and named the date it
	was in the middle of working out, so the message read "for date None" — even
	though a fixed hourly rate needs no structure at all.
	"""
	from hrms.payroll.doctype.payroll_entry.payroll_entry import get_start_end_dates
	from hrms.payroll.doctype.salary_structure_assignment.salary_structure_assignment import (
		get_assigned_salary_structure,
	)

	structure = get_assigned_salary_structure(employee, posting_date)
	if structure:
		frequency = frappe.db.get_value("Salary Structure", structure, "payroll_frequency")
		found = get_start_end_dates(
			frequency, posting_date, frappe.db.get_value("Employee", employee, "company")
		)
		return {"start_date": str(found.start_date), "end_date": str(found.end_date)}

	return {
		"start_date": str(get_first_day(posting_date)),
		"end_date": str(get_last_day(posting_date)),
	}


@frappe.whitelist()
def collect(employee: str, start_date: str, end_date: str) -> dict:
	"""Every day of overtime in the period, and what the type's maximum trimmed.

	Returns rather than writes. Trimming is reported rather than silent: a
	six-hour day against a four-hour maximum used to be written as four with
	nothing anywhere saying the other two were dropped.
	"""
	frappe.has_permission("Attendance", "read", throw=True)

	rows, trimmed = [], []
	most_by_type: dict[str, float] = {}

	for found in _days(employee, start_date, end_date):
		if found.overtime_type not in most_by_type:
			most_by_type[found.overtime_type] = flt(
				frappe.db.get_value("Overtime Type", found.overtime_type, "maximum_overtime_hours_allowed")
			)
		most = most_by_type[found.overtime_type]
		worked = flt(found.actual_overtime_duration)
		hours = min(worked, most) if most else worked
		if hours <= 0:
			continue

		if most and worked > most:
			trimmed.append({"date": str(found.attendance_date), "worked": worked, "paid": hours})

		rows.append(
			{
				"reference_document": found.name,
				"date": str(found.attendance_date),
				"overtime_type": found.overtime_type,
				"overtime_duration": hours,
				"one_actual": worked,
				"standard_working_hours": flt(found.standard_working_hours)
				or standard_hours(found.shift),
				"maximum_overtime_hours_allowed": most,
			}
		)

	return {"rows": rows, "trimmed": trimmed}


def _days(employee: str, start_date: str, end_date: str) -> list[frappe._dict]:
	return frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": COLLECTED,
			"attendance_date": ["between", [getdate(start_date), getdate(end_date)]],
			"overtime_type": ["is", "set"],
		},
		fields=[
			"name",
			"attendance_date",
			"shift",
			"overtime_type",
			"actual_overtime_duration",
			"standard_working_hours",
		],
		order_by="attendance_date asc",
	)


def _dates(doc) -> None:
	if doc.start_date and doc.end_date:
		return
	if not (doc.employee and doc.posting_date):
		return
	doc.update(dates(doc.employee, doc.posting_date))


def _standard_hours(doc) -> None:
	"""How long a day is, on every row, whoever typed it.

	Mandatory on HRMS's row with no hint of what to enter, and zero passes a
	mandatory check — which divides by zero on submit for a type priced off a
	salary component.
	"""
	shift = frappe.db.get_value("Employee", doc.employee, "default_shift") if doc.employee else None
	for row in doc.overtime_details:
		if flt(row.standard_working_hours) > 0:
			continue
		row.standard_working_hours = standard_hours(shift)
		if flt(row.standard_working_hours) <= 0:
			frappe.throw(
				_("Set Standard Working Hours in Attendance Settings before claiming overtime.")
			)


def _payable(doc) -> tuple[float, str]:
	"""What submitting this will pay, worked out with HRMS's own arithmetic.

	Its `get_overtime_component_amounts` is the same method `on_submit` uses, so
	the figure on the screen is the figure that will be written rather than a
	second implementation that will drift from it. It can legitimately fail —
	a type priced off a salary component needs a salary structure — and a slip
	is still worth saving when it does, so the reason is shown instead.
	"""
	if not doc.overtime_details:
		return 0.0, ""

	said = len(frappe.local.message_log)
	try:
		amounts = doc.get_overtime_component_amounts()
	except Exception:
		del frappe.local.message_log[said:]
		return 0.0, _("Overtime pay cannot be worked out until this employee has a salary structure.")

	del frappe.local.message_log[said:]
	total = sum(flt(amount) for amount in amounts.values())
	if not total:
		return 0.0, _("This overtime type has no rate set, so it pays nothing.")
	return total, ""
