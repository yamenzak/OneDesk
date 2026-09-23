"""A task's parts: the sub-tasks under it and the checklist on it.

**A sub-task is a task** with `parent_task` set, which is ERPNext's own tree.
ERPNext refuses a parent that is not marked Is Group, a box nobody ticks before
wanting a sub-task, so the parent is marked when the first one is made. A
sub-task made from its parent's page is in the parent's project; without that
it would be nobody's but its maker's, in their inbox.

**A step is not a task.** It has no owner, no date and nobody assigned — it is
a line to tick on the way to finishing the task (Task Step). When a task has
steps, its Progress is the share of them done, which ERPNext's Project already
reads when a project measures completion by task progress.

The sub-tasks are on the task's page as a connection (`dashboard`), so its +
makes one with the parent filled in, which is frappe's own way of doing it.

**A repeating task is frappe's Auto Repeat** (Repeat on a task's page). Each
repeat is a copy of the task, which would keep its old dates, its Completed and
its ticked steps; `recurring` makes it due on the day it repeats and gives it to
the same people.
"""

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate


def before_validate(doc, method=None) -> None:
	if doc.parent_task:
		parent = frappe.db.get_value("Task", doc.parent_task, ["is_group", "project"], as_dict=True)
		if parent and not parent.is_group:
			frappe.db.set_value("Task", doc.parent_task, "is_group", 1)
		if parent and not doc.project:
			doc.project = parent.project
	steps = doc.get("one_steps") or []
	if steps and doc.status != "Completed":
		doc.progress = share([step.done for step in steps])


def share(ticks: list) -> float:
	"""How much of a checklist is done, out of 100. Pure."""
	return flt(100 * sum(1 for one in ticks if one) / len(ticks), 1) if ticks else 0


def dashboard(data: dict) -> dict:
	"""Sub-tasks on a task's page, beside ERPNext's timesheets."""
	data.setdefault("non_standard_fieldnames", {})["Task"] = "parent_task"
	data.setdefault("transactions", []).insert(0, {"label": _("Sub-tasks"), "items": ["Task"]})
	return data


def recurring(doc, method=None, reference_doc=None, auto_repeat_doc=None, **kwargs) -> None:
	"""Task on_recurring: a repeat, due the day it repeats and still to do."""
	from onedesk.one_task.calendar import shifted

	day = getdate(auto_repeat_doc.next_schedule_date) if auto_repeat_doc else getdate()
	starts = get_datetime(doc.exp_start_date) if doc.exp_start_date else None
	ends = get_datetime(doc.exp_end_date) if doc.exp_end_date else None
	if starts or ends:
		doc.exp_start_date, doc.exp_end_date = shifted(starts, ends, day)
	else:
		doc.exp_end_date = get_datetime(day)
	doc.update({"status": "Open", "progress": 0, "completed_by": None, "completed_on": None})
	doc.update({"act_start_date": None, "act_end_date": None, "actual_time": 0})
	for step in doc.get("one_steps") or []:
		step.done = 0
	# The copy carries the list of people but not their assignments, which are
	# ToDos; capture.task_made gives it to them properly once it is saved.
	people = frappe.db.get_value("Task", reference_doc.name, "_assign") if reference_doc else None
	doc.flags.one_assign_to = frappe.parse_json(people) if people else None
	doc._assign = None
