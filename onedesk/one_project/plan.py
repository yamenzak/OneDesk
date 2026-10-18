"""A project's plan: what moves when a date slips."""

import frappe
from frappe.utils import add_days, date_diff

from onedesk.one_project import tree

MOVES = ("Open", "Working", "Overdue")


def reschedule(doc, method=None) -> None:
	"""Task on_update: dependants in other projects of the same tree move too."""
	ends = doc.exp_end_date or doc.act_end_date
	if not ends or not doc.project or not doc.has_value_changed("exp_end_date"):
		return
	of = tree.parents()
	family = tree.below({tree.above(doc.project, of)[-1]}, of) - {doc.project}
	if not family:
		return
	waiting = frappe.get_all(
		"Task Depends On",
		filters={"parenttype": "Task", "task": doc.name, "parent": ["!=", doc.parent_task or ""]},
		pluck="parent",
	)
	if not waiting:
		return
	for name in frappe.get_all("Task", filters={"name": ["in", waiting], "project": ["in", list(family)]}, pluck="name"):
		task = frappe.get_doc("Task", name)
		moved = moved_after(task.exp_start_date, task.exp_end_date, ends, task.status)
		if not moved:
			continue
		task.exp_start_date, task.exp_end_date = moved
		task.flags.ignore_recursion_check = True
		task.flags.rescheduled = True
		task.flags.ignore_permissions = True
		task.save()


def moved_after(starts, ends, before, status: str):
	"""Where a dependant goes when what it waits on now ends at `before`: the
	day after, keeping its length — or None when it need not move. ERPNext's
	own rule, for one task. Pure."""
	if not (starts and ends and status in MOVES and starts < before):
		return None
	length = date_diff(ends, starts)
	starts = add_days(before, 1)
	return starts, add_days(starts, length)
