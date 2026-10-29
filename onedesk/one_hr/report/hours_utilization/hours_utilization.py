"""How much of everybody's week ended up on a timesheet."""

import frappe
from frappe import _
from frappe.query_builder.functions import Coalesce
from frappe.utils import add_days, flt, get_link_to_form, getdate

from hrms.utils.holiday_list import (
	get_holiday_list_ranges_for_employees,
	get_holidays_in_ranges_map,
)

WATCH = 70.0


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	_check(filters)

	people = _people(filters)
	if not people:
		return _columns(), [], None, None, None

	rows = _rows(
		people,
		_every_day(filters),
		_logged(filters, 1),
		_days_off(people, filters),
		_standard(),
	)
	return _columns(), rows, None, None, _totals(rows, _logged(filters, 0))


def _check(filters) -> None:
	if not (filters.from_date and filters.to_date):
		frappe.throw(_("Set the date range."))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("The start date is after the end date."))


def _standard() -> float:
	hours = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours"))
	if not hours:
		frappe.throw(
			_("Set Standard Working Hours in {0} first. Everything here is measured against it.").format(
				get_link_to_form("HR Settings", "HR Settings", _("Attendance Settings"))
			)
		)
	return hours


def _people(filters) -> dict[str, frappe._dict]:
	"""Everybody who keeps timesheets, whether or not they wrote anything down
	this period. Somebody who has never kept one, an accountant say, is not
	somebody whose hours went untracked."""
	where = {"status": "Active"}
	if filters.employee:
		where["name"] = filters.employee
	else:
		where["name"] = ["in", frappe.get_all("Timesheet", filters={"docstatus": ["<", 2]}, pluck="employee", distinct=True) or [""]]
	if filters.department:
		where["department"] = filters.department

	found = frappe.get_all(
		"Employee",
		filters=where,
		fields=["name", "employee_name", "department", "company"],
		order_by="employee_name asc",
	)
	return {row.name: row for row in found}


def _logged(filters, submitted: int) -> dict[str, frappe._dict]:
	"""Hours on timesheets, split billed from not, by the log's own time.

	HRMS required the whole timesheet to fall inside the period, so one that
	straddled the first of the month contributed nothing at all. A log knows
	when it happened; that is what the period is about.
	"""
	sheet = frappe.qb.DocType("Timesheet")
	log = frappe.qb.DocType("Timesheet Detail")
	when = Coalesce(log.from_time, sheet.start_date)

	query = (
		frappe.qb.from_(log)
		.join(sheet)
		.on(log.parent == sheet.name)
		.select(sheet.employee, log.hours, log.is_billable)
		.where(sheet.docstatus == submitted)
		.where(sheet.employee.isnotnull())
		.where(when >= f"{filters.from_date} 00:00:00")
		.where(when <= f"{filters.to_date} 23:59:59")
	)
	if filters.employee:
		query = query.where(sheet.employee == filters.employee)
	if filters.project:
		query = query.where(log.project == filters.project)

	totals: dict[str, frappe._dict] = {}
	for employee, hours, billable in query.run():
		row = totals.setdefault(employee, frappe._dict(billed=0.0, not_billed=0.0))
		if billable:
			row.billed += flt(hours)
		else:
			row.not_billed += flt(hours)
	return totals


def _days_off(people: dict, filters) -> dict[str, set]:
	"""Each person's holidays and weekly offs in the period, in two queries.

	Their own list where they have one, their company's otherwise — which is
	what `get_holiday_list_for_employee` resolves and what Attendance is marked
	against, so the denominator here and the days on the month sheet agree.
	"""
	ranges = get_holiday_list_ranges_for_employees(
		{name: row.company for name, row in people.items()},
		filters.from_date,
		filters.to_date,
	)
	found = get_holidays_in_ranges_map(ranges)
	return {name: {holiday.holiday_date for holiday in days} for name, days in found.items()}


def _every_day(filters) -> set:
	"""Every date in the period. Each person's holidays come off it below."""
	days, day = set(), getdate(filters.from_date)
	last = getdate(filters.to_date)
	while day <= last:
		days.add(day)
		day = add_days(day, 1)
	return days


def _rows(
	people: dict, days: set, logged: dict, days_off: dict, standard: float
) -> list[frappe._dict]:
	"""One row each, lowest first: the people who wrote nothing down are the ones
	this is opened to find, so they are not at the bottom of a long list."""
	rows = []

	for name, who in people.items():
		working_days = len(days - days_off.get(name, set()))
		available = flt(working_days * standard, 2)
		hours = logged.get(name) or frappe._dict(billed=0.0, not_billed=0.0)
		tracked = hours.billed + hours.not_billed

		rows.append(
			frappe._dict(
				employee=name,
				employee_name=who.employee_name,
				department=who.department,
				working_days=working_days,
				available=available,
				billed=flt(hours.billed, 2),
				not_billed=flt(hours.not_billed, 2),
				untracked=flt(max(available - tracked, 0), 2),
				per_util=_percent(tracked, available),
				per_billed=_percent(hours.billed, available),
			)
		)

	rows.sort(key=lambda row: row.per_util)
	return rows


def _totals(rows: list, drafted: dict) -> list[dict] | None:
	if not rows:
		return None

	available = sum(row.available for row in rows)
	billed = sum(row.billed for row in rows)
	not_billed = sum(row.not_billed for row in rows)
	draft = sum(row.billed + row.not_billed for row in drafted.values())
	used = _percent(billed + not_billed, available)

	tiles = [
		{
			"label": _("Utilization"),
			"value": f"{used}%",
			"indicator": "Red" if used < WATCH else "Green",
			"datatype": "Data",
		},
		{"label": _("Billed"), "value": _hours(billed), "indicator": "Green", "datatype": "Data"},
		{"label": _("Not Billed"), "value": _hours(not_billed), "indicator": "Blue", "datatype": "Data"},
		{
			"label": _("Untracked"),
			"value": _hours(sum(row.untracked for row in rows)),
			"indicator": "Grey",
			"datatype": "Data",
		},
	]
	if draft:
		tiles.append(
			{"label": _("Still in Draft"), "value": _hours(draft), "indicator": "Orange", "datatype": "Data"}
		)
	return tiles


def _hours(value: float) -> str:
	"""38 h, 163.3 h: hours as a person writes them."""
	return _("{0} h").format(f"{flt(value, 1):g}")


def _percent(part: float, whole: float) -> float:
	return flt((part / whole) * 100, 2) if whole else 0.0


def _columns() -> list[dict]:
	return [
		{"label": _("Employee"), "fieldname": "employee_name", "fieldtype": "Data", "width": 200},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{"label": _("Working Days"), "fieldname": "working_days", "fieldtype": "Int", "width": 120},
		{"label": _("Available Hours"), "fieldname": "available", "fieldtype": "Float", "precision": 1, "width": 130},
		{"label": _("Billed Hours"), "fieldname": "billed", "fieldtype": "Float", "precision": 1, "width": 120},
		{"label": _("Not Billed Hours"), "fieldname": "not_billed", "fieldtype": "Float", "precision": 1, "width": 140},
		{"label": _("Untracked Hours"), "fieldname": "untracked", "fieldtype": "Float", "precision": 1, "width": 140},
		{"label": _("Utilization"), "fieldname": "per_util", "fieldtype": "Percent", "precision": 1, "width": 110},
		{"label": _("Billed %"), "fieldname": "per_billed", "fieldtype": "Percent", "precision": 1, "width": 100},
	]
