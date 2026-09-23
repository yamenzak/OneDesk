"""OneTask on the calendar: tasks, and the other things somebody was given.

A task is drawn on the day it is due, from its own table, and done where it
lives. Assignments are drawn too, but only the ones on other records — a deal,
a leave application — since an assignment on a task is that task, already on
the calendar once.
"""

import frappe
from frappe import _lt
from frappe.utils import getdate

from onedesk.one_calendar import layers
from onedesk.one_task.capture import DONE

LAYERS = [
	{
		"key": "my-tasks",
		"label": _lt("My Tasks"),
		"color": "purple",
		"group": "Mine",
		"doctype": "Task",
		"rows": "onedesk.one_task.calendar.tasks",
	},
	{
		"key": "my-todos",
		"label": _lt("Assigned to Me"),
		"color": "orange",
		"group": "Mine",
		"doctype": "ToDo",
		"rows": "onedesk.one_task.calendar.todos",
	},
]


def tasks(start, end) -> list[dict]:
	"""Tasks assigned to the reader and not yet done, on the day they are due,
	or on the day they start when no due date is set."""
	mine = [["_assign", "like", f'%"{frappe.session.user}"%'], ["status", "not in", DONE]]
	due = _tasks([*mine, *layers.within("exp_end_date", start, end)], "exp_end_date")
	starting = _tasks([*mine, ["exp_end_date", "is", "not set"], *layers.within("exp_start_date", start, end)], "exp_start_date")
	return due + starting


def _tasks(filters: list, day: str) -> list[dict]:
	return [
		{"name": one.name, "title": one.subject, "start": getdate(one[day]), "all_day": 1}
		for one in frappe.get_list("Task", filters=filters, fields=["name", "subject", day], limit=layers.MOST)
	]


def todos(start, end) -> list[dict]:
	"""Open assignments given to the reader on anything but a task, on the day
	they are due. One opens the record it is about, which is where it is done."""
	rows = []
	for one in frappe.get_list(
		"ToDo",
		filters=[
			["allocated_to", "=", frappe.session.user],
			["status", "=", "Open"],
			["reference_type", "!=", "Task"],
			*layers.within("date", start, end),
		],
		fields=["name", "description", "date", "reference_type", "reference_name"],
		limit=layers.MOST,
	):
		about = one.reference_type and one.reference_name
		rows.append(
			{
				"name": one.reference_name if about else one.name,
				"doctype": one.reference_type if about else "ToDo",
				"id": f"ToDo:{one.name}",
				"title": layers.plain(one.description, 80),
				"start": one.date,
				"all_day": 1,
			}
		)
	return rows
