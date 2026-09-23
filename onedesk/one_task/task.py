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
"""

import frappe
from frappe import _
from frappe.utils import flt


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
