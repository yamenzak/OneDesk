"""OneTask on the calendar: tasks, and the other things somebody was given.

A task is drawn on the day it is due, from its own table, and done where it
lives. Assignments are drawn too, but only the ones on other records — a deal,
a leave application — since an assignment on a task is that task, already on
the calendar once.

**Dragging a task moves its dates** (`move`): the due date goes to the day it
was dropped on, and the start goes with it by as many days, so a task keeps
its length. A time of day already set stays. A task is a day on the calendar,
so it is dragged, never stretched.

**A project's calendar** (Calendar on a project) has every task in it, whoever
is on them, beside the events about the project.
"""

from datetime import datetime, timedelta

import frappe
from frappe import _lt
from frappe.utils import get_datetime, getdate

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
		"move": "onedesk.one_task.calendar.move",
	},
	{
		"key": "project-tasks",
		"label": _lt("Tasks"),
		"color": "purple",
		"group": "Workspace",
		"doctype": "Task",
		"rows": "onedesk.one_task.calendar.project_tasks",
		"move": "onedesk.one_task.calendar.move",
		"about": ["Project"],
		"only_about": True,
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
	return _due([["_assign", "like", f'%"{frappe.session.user}"%'], ["status", "not in", DONE]], start, end)


def project_tasks(start, end, record: tuple) -> list[dict]:
	"""Every task in one project not yet done, whoever is on it."""
	return _due([["project", "=", record[1]], ["status", "not in", DONE]], start, end)


def _due(which: list, start, end) -> list[dict]:
	due = _tasks([*which, *layers.within("exp_end_date", start, end)], "exp_end_date")
	starting = _tasks([*which, ["exp_end_date", "is", "not set"], *layers.within("exp_start_date", start, end)], "exp_start_date")
	return due + starting


def _tasks(filters: list, day: str) -> list[dict]:
	# Editable: the page offers the drag, and `move` checks the reader may
	# write the task before anything changes.
	return [
		{"name": one.name, "title": one.subject, "start": getdate(one[day]), "all_day": 1, "editable": 1, "resizable": 0}
		for one in frappe.get_list("Task", filters=filters, fields=["name", "subject", day], limit=layers.MOST)
	]


def move(name: str, start: str, end: str | None = None, all_day: int | None = None) -> None:
	"""A task dragged to another day, through its own save."""
	doc = frappe.get_doc("Task", name)
	doc.check_permission("write")
	was = doc.exp_end_date or doc.exp_start_date
	if not was:
		return
	doc.exp_start_date, doc.exp_end_date = shifted(
		get_datetime(doc.exp_start_date) if doc.exp_start_date else None,
		get_datetime(doc.exp_end_date) if doc.exp_end_date else None,
		getdate(start),
	)
	doc.save()


def shifted(starts: datetime | None, ends: datetime | None, day) -> tuple:
	"""A task's start and end with the day it is drawn on moved to `day`: both
	by the same number of days, each keeping its time. Pure."""
	drawn = (ends or starts).date()
	by = timedelta(days=(day - drawn).days)
	return (starts + by if starts else None, ends + by if ends else None)


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
