"""Every day that was marked, against the shift it was meant to be.

HRMS's `Shift Attendance` showed one row where the month held twenty-seven,
and said nothing about the twenty-six it dropped. Two inner joins did it:

    .inner_join(shift_type).on(attendance.shift == shift_type.name)
    .inner_join(checkin).on(checkin.attendance == attendance.name)

The first throws away every Attendance with no shift on it — which is most of
them on a site that marks attendance by hand or runs one unassigned shift. The
second throws away every day with no `Employee Checkin` pointing at it, and the
checkbox that puts those back ("Include Shift Attendance Without Checkins") is
off by default and reads like it adds something extra rather than restoring what
was cut.

A number that has quietly discarded its own denominator is worse than no number:
"Late Entries 0" looked like nobody was late and meant twenty-six days were never
counted. So every join here is a left join, every day in the period is a row, and
a day with no shift says so with an empty cell.

The arithmetic is still theirs — `update_late_entry` and `update_early_exit`
know about grace periods and this does not re-derive them — and it is only
applied to the rows that have a shift window to measure against.
"""

import frappe
from frappe import _
from frappe.query_builder import Criterion
from frappe.query_builder.functions import Max

from erpnext.accounts.utils import build_qb_match_conditions

from hrms.hr.report.shift_attendance import shift_attendance as upstream


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	rows = _rows(filters)
	_format(rows, filters)
	return _columns(), rows, None, None, _totals(rows)


def _rows(filters) -> list[frappe._dict]:
	"""Every submitted Attendance in the period. Nothing is joined away.

	The shift window comes from the check-in that carries it, which is where
	HRMS keeps it — `Max` over the group because several check-ins can point at
	one day and they all carry the same window.
	"""
	attendance = frappe.qb.DocType("Attendance")
	shift = frappe.qb.DocType("Shift Type")
	checkin = frappe.qb.DocType("Employee Checkin")

	query = (
		frappe.qb.from_(attendance)
		.left_join(shift)
		.on(attendance.shift == shift.name)
		.left_join(checkin)
		.on(checkin.attendance == attendance.name)
		.select(
			attendance.name,
			attendance.employee,
			attendance.employee_name,
			attendance.shift,
			attendance.attendance_date,
			attendance.status,
			attendance.in_time,
			attendance.out_time,
			attendance.working_hours,
			attendance.late_entry,
			attendance.early_exit,
			attendance.department,
			shift.enable_late_entry_marking,
			shift.late_entry_grace_period,
			shift.enable_early_exit_marking,
			shift.early_exit_grace_period,
			Max(checkin.shift_start).as_("shift_start"),
			Max(checkin.shift_end).as_("shift_end"),
		)
		.where(attendance.docstatus == 1)
		.groupby(attendance.name)
		.orderby(attendance.attendance_date)
		.orderby(attendance.employee)
	)

	if filters.from_date:
		query = query.where(attendance.attendance_date >= filters.from_date)
	if filters.to_date:
		query = query.where(attendance.attendance_date <= filters.to_date)
	for field in ("employee", "shift", "department", "status"):
		if filters.get(field):
			query = query.where(attendance[field] == filters[field])

	# Ticked means "only these"; unticked is not a request for the days that
	# were on time, which is what filtering on 0 would have asked for.
	if filters.late_entry:
		query = query.where(attendance.late_entry == 1)
	if filters.early_exit:
		query = query.where(attendance.early_exit == 1)

	query = query.where(Criterion.all(build_qb_match_conditions("Attendance")))
	return query.run(as_dict=True)


def _format(rows: list, filters) -> None:
	"""HRMS's own formatting, applied only where there is something to measure."""
	for row in rows:
		if row.shift_start and row.shift_end:
			upstream.update_late_entry(row, filters.consider_grace_period)
			upstream.update_early_exit(row, filters.consider_grace_period)
			row.shift_hours = _window(row.shift_start, row.shift_end)
		else:
			row.shift_hours = ""

		row.working_hours = upstream.format_float_precision(row.working_hours)
		row.in_time, row.out_time = upstream.format_in_out_time(
			row.in_time, row.out_time, row.attendance_date
		)
		row.status = _said(row)


def _said(row) -> str:
	"""The status, and whether the day was late or short.

	`Late By` can only be filled where the shift window is known, and a day can
	be flagged late with no check-in behind it to measure against — so the flag
	is said in words rather than left as an empty cell on a row that the Late
	Only filter just returned.
	"""
	marks = []
	if row.late_entry:
		marks.append(_("late"))
	if row.early_exit:
		marks.append(_("left early"))
	return f"{_(row.status)} · {', '.join(marks)}" if marks else _(row.status)


def _window(start, end) -> str:
	"""The shift's two times as one cell, because four columns said it twice."""
	start, end = upstream.convert_datetime_to_time_for_same_date(start, end)
	return f"{start} – {end}" if start and end else ""


def _columns() -> list[dict]:
	return [
		{
			"label": _("Employee"),
			"fieldname": "employee_name",
			"fieldtype": "Data",
			"width": 200,
		},
		{"label": _("Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 110},
		{
			"label": _("Shift"),
			"fieldname": "shift",
			"fieldtype": "Link",
			"options": "Shift Type",
			"width": 110,
		},
		{"label": _("Shift Hours"), "fieldname": "shift_hours", "fieldtype": "Data", "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 90},
		{"label": _("In"), "fieldname": "in_time", "fieldtype": "Data", "width": 90},
		{"label": _("Out"), "fieldname": "out_time", "fieldtype": "Data", "width": 90},
		{"label": _("Hours"), "fieldname": "working_hours", "fieldtype": "Data", "width": 80},
		{"label": _("Late By"), "fieldname": "late_entry_hrs", "fieldtype": "Data", "width": 100},
		{"label": _("Left Early By"), "fieldname": "early_exit_hrs", "fieldtype": "Data", "width": 120},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{
			"label": _("Attendance"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Attendance",
			"width": 150,
		},
	]


def _totals(rows: list) -> list[dict] | None:
	"""Days, not "records" — the same number, and one of them is a word people say.

	The four status tiles add up to the rows, which is the whole point: a count
	that has silently dropped its own denominator is what was wrong here. Working
	from home counts as present, the way HRMS's own summary counts it. Half days
	and leave only appear when there are some, because five tiles fit on one line
	and two permanent zeroes are not worth the second.

	`No Shift` is the one that would have explained the old screen: nineteen of
	these twenty-seven days carry no shift, which is exactly what its inner join
	threw away without saying so.
	"""
	if not rows:
		return None

	counted = {}
	late = early = no_shift = 0
	for row in rows:
		counted[row.status] = counted.get(row.status, 0) + 1
		late += bool(row.late_entry)
		early += bool(row.early_exit)
		no_shift += not row.shift

	present = counted.get("Present", 0) + counted.get("Work From Home", 0)
	tiles = [
		{"label": _("Present"), "value": present, "indicator": "Green", "datatype": "Int"},
		{"label": _("Absent"), "value": counted.get("Absent", 0), "indicator": "Red", "datatype": "Int"},
	]
	for status, colour in (("Half Day", "Blue"), ("On Leave", "Blue")):
		if counted.get(status):
			tiles.append(
				{"label": _(status), "value": counted[status], "indicator": colour, "datatype": "Int"}
			)
	tiles.extend(
		[
			{"label": _("Late"), "value": late, "indicator": "Orange", "datatype": "Int"},
			{"label": _("Left Early"), "value": early, "indicator": "Orange", "datatype": "Int"},
			{"label": _("No Shift"), "value": no_shift, "indicator": "Grey", "datatype": "Int"},
		]
	)
	return tiles
