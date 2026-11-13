"""Task's collection views as frappe draws them, with what OneTask changes:
the Calendar (public/js/one_task/task_calendar.js) and the Tree (public/js/one_task/task_tree.js)
read here, leaving a template's tasks out, as the list and the boards do."""

from datetime import time
from typing import Annotated

import frappe
from frappe.desk.calendar import get_events
from frappe.utils import get_datetime

NOT_A_TEMPLATE = ["is_template", "=", 0]


def all_day(starts, ends) -> bool:
	"""A task planned by the day: ERPNext keeps its dates as datetimes, at
	midnight unless a time was set. Pure."""
	return all(not one or get_datetime(one).time() == time() for one in (starts, ends))


@frappe.whitelist()
@frappe.read_only()
def events(
	doctype: Annotated[str, "Task."],
	start: Annotated[str, "The first day shown."],
	end: Annotated[str, "The last day shown."],
	field_map: Annotated[str, "The calendar's field map."],
	filters: Annotated[str | None, "The view's filters."] = None,
	fields: Annotated[str | None, "The fields to read."] = None,
) -> list:
	"""frappe's own events for the Task calendar, as the reader may read them,
	without a template's tasks, and a task planned by the day drawn as a day
	rather than at midnight."""
	if doctype != "Task":
		frappe.throw(frappe._("Only tasks are read here."))
	rows = get_events(doctype, start, end, field_map, [*(frappe.parse_json(filters) or []), NOT_A_TEMPLATE], fields)
	for one in rows:
		one["allDay"] = 1 if all_day(one.get("exp_start_date"), one.get("exp_end_date")) else 0
	return rows


@frappe.whitelist()
@frappe.read_only()
def children(
	doctype: Annotated[str, "Task."],
	parent: Annotated[str | None, "The task opened."] = None,
	task: Annotated[str | None, "The group task chosen in the filter."] = None,
	project: Annotated[str | None, "The project chosen in the filter."] = None,
	is_root: Annotated[bool, "Whether the tree's root is opened."] = False,
) -> list:
	"""The tasks under one, as ERPNext's tree reads them (task.get_children),
	as the reader may read them, without a template's tasks, each with where
	it stands."""
	filters = [["docstatus", "<", 2], NOT_A_TEMPLATE]
	if task:
		filters.append(["parent_task", "=", task])
	elif parent and not frappe.utils.cint(is_root):
		filters.append(["parent_task", "=", parent])
	else:
		filters.append(["parent_task", "is", "not set"])
	if project:
		filters.append(["project", "=", project])
	return frappe.get_list(
		"Task",
		fields=["name as value", "subject as title", "is_group as expandable", "status", "exp_end_date"],
		filters=filters,
		order_by="exp_start_date asc, name asc",
	)
