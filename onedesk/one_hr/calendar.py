"""OneHR on the calendar: your own leave and interviews, the workspace's
holidays, and who is off.

**Who's Off follows the leave permissions**, as everything on the calendar
follows its record's: an HR user sees everybody's approved leave, and an
employee whose User Permission limits them to their own sees their own.
"""

import frappe
from frappe import _lt

from onedesk.one_calendar import layers
from onedesk.one_hr import own

#: Leave that is not going to happen.
DROPPED = ("Rejected", "Cancelled")

LAYERS = [
	{
		"key": "my-leave",
		"label": _lt("My Leave"),
		"color": "pink",
		"group": "Mine",
		"doctype": "Leave Application",
		"rows": "onedesk.one_hr.calendar.my_leave",
	},
	{
		"key": "my-interviews",
		"label": _lt("My Interviews"),
		"color": "violet",
		"group": "Mine",
		"doctype": "Interview",
		"rows": "onedesk.one_hr.calendar.interviews",
	},
	{
		"key": "holidays",
		"label": _lt("Holidays"),
		"color": "red",
		"group": "Workspace",
		"doctype": "Holiday List",
		"rows": "onedesk.one_hr.calendar.holidays",
	},
	{
		"key": "whos-off",
		"label": _lt("Who's Off"),
		"color": "gray",
		"group": "Workspace",
		"doctype": "Leave Application",
		"on": False,
		"rows": "onedesk.one_hr.calendar.whos_off",
	},
	# On an employee's own calendar: their leave, for whoever may read it.
	{
		"key": "employee-leave",
		"label": _lt("Leave"),
		"color": "pink",
		"group": "Workspace",
		"doctype": "Leave Application",
		"rows": "onedesk.one_hr.calendar.employee_leave",
		"about": ["Employee"],
		"only_about": True,
	},
]


def _leave(start, end, filters) -> list:
	return frappe.get_list(
		"Leave Application",
		filters=[*filters, ["from_date", "<=", str(end)], ["to_date", ">=", str(start)]],
		fields=["name", "employee_name", "leave_type", "from_date", "to_date", "status", "half_day"],
		limit=layers.MOST,
	)


def my_leave(start, end) -> list[dict]:
	employee = own.employee_of()
	if not employee:
		return []
	return [
		{
			"name": one.name,
			"title": f"{frappe._(one.leave_type)}" + ("" if one.status == "Approved" else f" · {frappe._(one.status)}"),
			"start": one.from_date,
			"end": one.to_date,
			"all_day": 1,
		}
		for one in _leave(start, end, [["employee", "=", employee], ["status", "not in", DROPPED]])
	]


def employee_leave(start, end, record: tuple) -> list[dict]:
	return [
		{
			"name": one.name,
			"title": f"{frappe._(one.leave_type)}" + ("" if one.status == "Approved" else f" · {frappe._(one.status)}"),
			"start": one.from_date,
			"end": one.to_date,
			"all_day": 1,
		}
		for one in _leave(start, end, [["employee", "=", record[1]], ["status", "not in", DROPPED]])
	]


def whos_off(start, end) -> list[dict]:
	return [
		{
			"name": one.name,
			"title": one.employee_name + (f" · {frappe._('Half Day')}" if one.half_day else ""),
			"start": one.from_date,
			"end": one.to_date,
			"all_day": 1,
		}
		for one in _leave(start, end, [["status", "=", "Approved"]])
	]


def holidays(start, end) -> list[dict]:
	"""The company's holidays, not its weekly days off: a calendar with every
	Friday marked is a calendar nobody reads."""
	company = frappe.defaults.get_global_default("company")
	listed = company and frappe.db.get_value("Company", company, "default_holiday_list")
	if not listed:
		return []
	return [
		{"name": listed, "id": f"Holiday:{one.name}", "title": layers.plain(one.description, 80), "start": one.holiday_date, "all_day": 1}
		for one in frappe.get_all(
			"Holiday",
			filters=[["parent", "=", listed], ["weekly_off", "=", 0], *layers.within("holiday_date", start, end)],
			fields=["name", "holiday_date", "description"],
		)
	]


def interviews(start, end) -> list[dict]:
	"""Interviews the reader is on the panel for."""
	rows = []
	for one in frappe.get_list(
		"Interview",
		filters=[
			["Interview Detail", "interviewer", "=", frappe.session.user],
			["status", "not in", ("Cancelled",)],
			*layers.within("scheduled_on", start, end),
		],
		fields=["name", "job_applicant", "interview_round", "scheduled_on", "from_time", "to_time"],
		limit=layers.MOST,
	):
		applicant = frappe.db.get_value("Job Applicant", one.job_applicant, "applicant_name") or one.job_applicant
		rows.append(
			{
				"name": one.name,
				"title": " · ".join(filter(None, [applicant, one.interview_round])),
				"start": f"{one.scheduled_on} {one.from_time or '00:00:00'}",
				"end": f"{one.scheduled_on} {one.to_time}" if one.to_time else None,
				"all_day": 0 if one.from_time else 1,
			}
		)
	return rows
