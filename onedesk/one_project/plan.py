"""A project's plan: what depends on what, and what moves when a date slips.

**A dependency says which project it is in.** ERPNext moves a task's dependants
later when its date slips (`reschedule_dependent_tasks`), and finds them by the
project on each Task Depends On row — a read-only field nothing in ERPNext ever
writes, so the slip never found anything. The row takes the task's project.

**A slip crosses sub-projects** (`reschedule`). ERPNext moves only dependants in
the same project as the task that slipped. "Install the handrails" in Handrails
waits on "Fit the frames" in Windows, both under one villa, and should move
when the frames do. So after ERPNext's own pass this moves the dependants in the
rest of the same tree, the way theirs moves the others: a task still Open that
would start before the new end starts the day after it, keeping its length.
It saves the dependant whether or not the person who moved the date may edit
it: the date moved because of theirs, and a plan that holds only where the
mover is a member is not a plan.

**The plan is frappe's Gantt** over the tree's tasks (public/js/project.js,
Schedule): bars, milestones, the dependency arrows, and dragging a bar moves the
task. A task with a due date and no start is drawn as a day on its due date
(public/js/task_list.js).
"""

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
