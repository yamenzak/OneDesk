"""A task's parts: the sub-tasks under it and the checklist on it."""

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


@frappe.whitelist(methods=["POST"])
def tick(task: str, step: str, done: int | str = 1) -> float:
	"""Tick or untick a step of a task's checklist, saved as the task, so its
	progress and its project's follow. Returns the task's progress."""
	doc = frappe.get_doc("Task", task)
	doc.check_permission("write")
	row = next((one for one in doc.get("one_steps") or [] if one.name == step), None)
	if not row:
		frappe.throw(_("That step isn't on this task any more."))
	row.done = 1 if str(done) in ("1", "true", "True") else 0
	doc.save()
	return flt(doc.progress)


@frappe.whitelist(methods=["POST"])
def add_step(task: str, step: str) -> str:
	"""A step added at the end of a task's checklist. Returns its row name."""
	step = (step or "").strip()
	if not step:
		frappe.throw(_("Write the step first."))
	doc = frappe.get_doc("Task", task)
	doc.check_permission("write")
	row = doc.append("one_steps", {"step": step})
	doc.save()
	return row.name
