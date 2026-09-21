"""One month, one row each, everybody on it.

HRMS's `Monthly Attendance Sheet` answers a narrower question than the one people
open it for, in three ways that compound.

**It keys on employee *and* shift**, so somebody who picked up a shift assignment
mid-month becomes two rows — one blank-shift, one "Day" — with half their days on
each and neither being their month.

**It only shows people who have an Attendance row.** Six active employees, three
rows: anybody with nothing marked at all is not on the sheet, which is exactly
the person the sheet exists to find. `unmarked_days` in the summarized view has
the same hole, because the query it sums returns nothing for them.

**And it asks which company**, with an Include Company Descendants checkbox
underneath. One workspace is one company; see `one/company.py`.

So the rows are built from HRMS's own pieces — its attendance map, its holiday
map, its status abbreviations — and the three questions above are answered before
they reach it. Nothing here re-implements what a day means.

The chart is gone rather than replaced. Attendance Overview is where the shape
of a month is looked at; this is the sheet somebody prints and initials, and a
three-series line of counts between nought and three, with every date label
rendered as an ellipsis, was a third of the screen in front of it.
"""

import frappe
from frappe import _
from frappe.utils import getdate

from hrms.hr.report.monthly_attendance_sheet import monthly_attendance_sheet as sheet

#: The grid is two-letter codes, so it needs a key. One line, in the order the
#: codes rank, rather than HRMS's eight-item list wrapping above the chart.
LEGEND = (
	("P", "Present", "var(--green-500)"),
	("WFH", "From home", "var(--green-500)"),
	("HD/P", "Half day, rest present", "#914EE3"),
	("HD/A", "Half day, rest absent", "var(--orange-500)"),
	("A", "Absent", "var(--red-500)"),
	("L", "On leave", "#3187D8"),
	("H", "Holiday", "var(--gray-500)"),
	("WO", "Weekly off", "var(--gray-500)"),
)

#: Longest a date range may be, which is HRMS's own limit and the reason it
#: exists: a column per day stops being a sheet somewhere around a quarter.
MOST_DAYS = 90


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	_the_company(filters)
	_check(filters)

	attendance = sheet.get_attendance_map(filters)
	if not filters.summarized_view:
		attendance = _one_row_each(attendance)

	data = sheet.get_data(filters, attendance)
	data.extend(_the_missing(filters, data))

	return _columns(filters), data, _legend(filters), None


def _the_company(filters) -> None:
	"""One workspace is one company, so the filter is not asked and not offered."""
	filters.company = frappe.defaults.get_user_default("Company") or frappe.db.get_value(
		"Company", {}, "name"
	)
	filters.companies = [filters.company] if filters.company else []


def _check(filters) -> None:
	if filters.filter_based_on == "Date Range":
		if not (filters.start_date and filters.end_date):
			frappe.throw(_("Set the date range."))
		if getdate(filters.start_date) > getdate(filters.end_date):
			frappe.throw(_("The start date is after the end date."))
		if (getdate(filters.end_date) - getdate(filters.start_date)).days > MOST_DAYS:
			frappe.throw(_("A sheet covers at most {0} days.").format(MOST_DAYS))
	elif not (filters.month and filters.year):
		frappe.throw(_("Choose a month and a year."))


def _one_row_each(attendance: dict) -> dict:
	"""Every shift an employee worked, folded into the one row that is their month.

	HRMS keeps a row per shift because a workplace can run two in a day. That is
	true and it is not what a month sheet is for: the days do not overlap, so
	folding them loses nothing, and the shift column says which they were on.
	"""
	folded = {}
	for employee, by_shift in attendance.items():
		days = {}
		for shift in by_shift.values():
			days.update(shift)
		shifts = sorted({name for name in by_shift if name})
		folded[employee] = {", ".join(shifts): days}
	return folded


def _the_missing(filters, data: list[dict]) -> list[dict]:
	"""A row for everybody the sheet would otherwise have left out.

	Blank rather than guessed: no attendance means no attendance, and a line of
	empty cells beside a name is the clearest way a sheet can say so. Holidays
	and weekly offs are still filled in, because those are known without a single
	Attendance row and leaving them out would make the blanks look worse than
	they are.
	"""
	people, _groups = sheet.get_employee_related_details(filters)
	if filters.group_by:
		flat = {}
		for group in people.values():
			flat.update(group)
		people = flat

	seen = {row.get("employee") for row in data}
	missing = {name: details for name, details in people.items() if name not in seen}
	if not missing:
		return []

	holidays = sheet.get_employee_holiday_map(missing, filters)

	if filters.summarized_view:
		return [
			_nothing_summarized(filters, holidays.get(name, []), name, details.employee_name)
			for name, details in missing.items()
		]

	# A shift of `None` with no days: HRMS's own row builder then fills the
	# holidays and leaves the rest blank, which is the row we want.
	return sheet.get_rows(missing, filters, holidays, {name: {None: {}} for name in missing})


def _nothing_summarized(filters, holidays: list, employee: str, employee_name: str) -> dict:
	"""The totals for somebody with no attendance at all: holidays, then blanks."""
	days = sheet.get_dates_in_period(filters)
	off = sum(
		1
		for day in days
		if sheet.get_holiday_status(getdate(day), holidays) in ("Weekly Off", "Holiday")
	)

	row = {"employee": employee, "employee_name": employee_name}
	sheet.set_defaults_for_summarized_view(filters, row)
	row["total_holidays"] = off
	row["unmarked_days"] = len(days) - off
	return row


def _columns(filters) -> list[dict]:
	"""HRMS's columns, with the two that say the same thing made into one.

	The grid opened with `HR-EMP-0000…` truncated beside a clipped name. The name
	is what a person reads; the id is what the link needs, and the formatter has
	it on the row.
	"""
	columns = []
	for column in sheet.get_columns(filters):
		if column.get("fieldname") == "employee":
			continue
		if column.get("fieldname") == "employee_name":
			column = {**column, "label": _("Employee"), "width": 200}
		columns.append(column)
	return columns


def _legend(filters) -> str:
	if filters.summarized_view:
		return ""
	parts = [
		f"<span style='white-space:nowrap; margin-right:14px'>"
		f"<b style='color:{colour}'>{abbr}</b> "
		f"<span class='text-muted'>{_(label)}</span></span>"
		for abbr, label, colour in LEGEND
	]
	return f"<div style='margin-bottom:8px'>{''.join(parts)}</div>"
