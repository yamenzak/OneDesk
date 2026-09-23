"""A project started from one that went well.

ERPNext's **Project Template** is a list of template tasks — Tasks ticked **Is
Template**, each with **Begin On (Days)** after the project starts and a
**Duration (Days)** — and a project given one gets a task for each, dated from
its own start, with the template's sub-tasks and dependencies between them
(`Project.copy_from_template`). That part is theirs and stays theirs. What this
adds is what stopped anybody using it:

- **Save as Template** (`save_as`). Building a template meant making each
  template task by hand on the Task form and then listing it on the template.
  Now a project that went well is the template: its tasks, their dates as days
  after the project's start, their lengths, sub-tasks, dependencies,
  milestones, checklists and expected time. Cancelled tasks are left out, and
  so are dependencies on tasks in other projects, since a template is one
  project.
- **What ERPNext's copy leaves behind** (`task_made`). Their copy carries the
  subject, dates, priority, type and a few more, and not whether a task is a
  milestone, its expected time or its checklist; the new task takes them from
  the template task it was made from.
- **Who may keep templates** (`settle`). ERPNext lets only a System Manager
  open one; a Projects Manager may keep them, and a Projects User read them.
- **A template task is nobody's work.** It is not assigned to its maker
  (one_task/capture.py) and everybody who works in projects sees it
  (one_task/access.py), since a template is for the whole team.

A new project's Task Prefix names the tasks a template makes, because the
naming rule is written when the project is, not after (naming.py).
"""

import frappe
from frappe import _
from frappe.permissions import add_permission, setup_custom_perms, update_permission_property
from frappe.utils import date_diff, getdate

#: The Task fields a template task keeps, beside its dates.
KEPT = ("subject", "description", "priority", "type", "is_group", "is_milestone", "expected_time", "task_weight", "color")

#: What ERPNext's copy leaves out and the new task takes from its template task.
LEFT_OUT = ("is_milestone", "expected_time")

MANAGER = "Projects Manager"
USER = "Projects User"


def settle() -> None:
	"""A Projects Manager may keep templates. Written once, like
	one_task/access.py: a Project Template with Custom DocPerm rows has been
	decided by the workspace."""
	if frappe.db.exists("Custom DocPerm", {"parent": "Project Template"}):
		return
	setup_custom_perms("Project Template")
	if not frappe.db.exists("Custom DocPerm", {"parent": "Project Template", "role": MANAGER, "permlevel": 0}):
		add_permission("Project Template", MANAGER, 0)
	for ptype in ("read", "write", "create", "delete"):
		update_permission_property("Project Template", MANAGER, 0, ptype, 1, validate=False)
	if frappe.db.exists("Custom DocPerm", {"parent": "Project Template", "role": USER, "permlevel": 0}):
		update_permission_property("Project Template", USER, 0, "read", 1, validate=False)


def task_made(doc, method=None) -> None:
	"""Task before_insert: a task made from a template task takes what
	ERPNext's copy left out."""
	if not doc.get("template_task") or doc.is_template:
		return
	source = frappe.get_doc("Task", doc.template_task)
	for field in LEFT_OUT:
		if not doc.get(field):
			doc.set(field, source.get(field))
	if not doc.get("one_steps"):
		for step in source.get("one_steps") or []:
			doc.append("one_steps", {"step": step.step})


@frappe.whitelist(methods=["POST"])
def save_as(project: str, title: str) -> str:
	"""A Project Template made from this project's tasks. Returns its name."""
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Project Template", "create", throw=True)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("Name the template."))
	if frappe.db.exists("Project Template", title):
		frappe.throw(_("There is already a template called {0}.").format(title))
	source = frappe.get_doc("Project", project)
	tasks = frappe.get_all(
		"Task",
		filters={"project": project, "status": ["not in", ("Cancelled", "Template")]},
		fields=["name", "parent_task", "exp_start_date", "exp_end_date", *KEPT],
		order_by="lft asc, creation asc",
	)
	if not tasks:
		frappe.throw(_("{0} has no tasks to make a template from.").format(source.project_name))
	begins = start_of(source.expected_start_date, tasks)
	made = {}
	for task in tasks:
		copy = frappe.new_doc("Task")
		copy.update({field: task.get(field) for field in KEPT})
		copy.update(days(begins, task.exp_start_date, task.exp_end_date))
		copy.is_template = 1
		for step in frappe.get_all("Task Step", filters={"parent": task.name, "parenttype": "Task"}, fields=["step"], order_by="idx"):
			copy.append("one_steps", {"step": step.step})
		copy.insert()
		made[task.name] = copy.name
	for task in tasks:
		waits = frappe.get_all("Task Depends On", filters={"parent": task.name, "parenttype": "Task"}, pluck="task")
		parent = made.get(task.parent_task)
		waits = [made[one] for one in waits if one in made]
		if not (parent or waits):
			continue
		copy = frappe.get_doc("Task", made[task.name])
		copy.parent_task = parent
		for one in waits:
			copy.append("depends_on", {"task": one})
		copy.save()
	template = frappe.new_doc("Project Template")
	template.update({"project_type": source.project_type})
	for task in tasks:
		template.append("tasks", {"task": made[task.name], "subject": task.subject})
	template.insert(set_name=title)
	return template.name


def start_of(project_starts, tasks: list) -> object:
	"""Day nought of a template: the project's start, or its first task's if
	that is earlier, so no task begins before the project. Pure."""
	dates = [getdate(day) for task in tasks for day in (task.get("exp_start_date"), task.get("exp_end_date")) if day]
	if project_starts:
		dates.append(getdate(project_starts))
	return min(dates) if dates else None


def days(begins, starts, ends) -> dict:
	"""A task's dates as ERPNext's template counts them: Begin On days after the
	project starts, and Duration, the days from its start to its end. A task
	with only an end is a day on it; one with no dates begins with the
	project. Pure."""
	starts = starts or ends
	if not (begins and starts):
		return {"start": 0, "duration": 0}
	ends = ends or starts
	return {"start": max(date_diff(starts, begins), 0), "duration": max(date_diff(ends, starts), 0)}
