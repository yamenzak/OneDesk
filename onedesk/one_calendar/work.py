"""To-dos and tasks: work with a day it is due, not a time it happens.

A ToDo is frappe's assignment — somebody was given something to do about a
record — and a Task is ERPNext's. Neither is copied into an Event: each is
drawn on the day it is due from its own table, and done where it lives. Both
belong to OneTask when OneDesk has one, and move there with their layers.
"""

import frappe
from frappe import _lt

from onedesk.one_calendar import layers

#: What a task that is still to do can be.
DONE = ("Completed", "Cancelled", "Template")

LAYERS = [
	{
		"key": "my-todos",
		"label": _lt("My To-Dos"),
		"color": "orange",
		"group": "Mine",
		"doctype": "ToDo",
		"rows": "onedesk.one_calendar.work.todos",
	},
	{
		"key": "my-tasks",
		"label": _lt("My Tasks"),
		"color": "purple",
		"group": "Mine",
		"doctype": "Task",
		"rows": "onedesk.one_calendar.work.tasks",
	},
]


def todos(start, end) -> list[dict]:
	"""Open to-dos given to the reader, on the day they are due. One opens the
	record it is about, which is where it is done."""
	rows = []
	for one in frappe.get_list(
		"ToDo",
		filters=[["allocated_to", "=", frappe.session.user], ["status", "=", "Open"], *layers.within("date", start, end)],
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


def tasks(start, end) -> list[dict]:
	"""Tasks assigned to the reader and not yet done, on the day they are due,
	or the day they start when no end is set."""
	user = frappe.session.user
	rows = []
	for one in frappe.get_list(
		"Task",
		filters=[["_assign", "like", f'%"{user}"%'], ["status", "not in", DONE]],
		or_filters=[
			["exp_end_date", "between", [str(start), str(end)]],
			["exp_start_date", "between", [str(start), str(end)]],
		],
		fields=["name", "subject", "exp_start_date", "exp_end_date"],
		limit=layers.MOST,
	):
		due = one.exp_end_date or one.exp_start_date
		if due and start <= due <= end:
			rows.append({"name": one.name, "title": one.subject, "start": due, "all_day": 1})
	return rows
