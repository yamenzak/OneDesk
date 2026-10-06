"""A project's plan: what depends on what, and what moves when a date slips."""

import frappe
from frappe.utils import add_days, date_diff

from onedesk.one_project import tree


def before_validate(doc, method=None) -> None:
	"""Task before_validate: each dependency row names the task's project."""
	for row in doc.get("depends_on") or []:
		if not row.project:
			row.project = doc.project


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
		filters={"parenttype": "Task", "task": doc.name, "project": ["in", list(family)]},
		pluck="parent",
	)
	for name in waiting:
		task = frappe.get_doc("Task", name)
		moved = moved_after(task.exp_start_date, task.exp_end_date, ends, task.status)
		if not moved:
			continue
		task.exp_start_date, task.exp_end_date = moved
		task.flags.ignore_recursion_check = True
		task.flags.ignore_permissions = True
		task.save()


def moved_after(starts, ends, before, status: str):
	"""Where a dependant goes when what it waits on now ends at `before`: the
	day after, keeping its length — or None when it need not move. ERPNext's
	own rule, for one task. Pure."""
	if not (starts and ends and status == "Open" and starts < before):
		return None
	length = date_diff(ends, starts)
	starts = add_days(before, 1)
	return starts, add_days(starts, length)
