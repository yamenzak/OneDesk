"""A project started from one that went well, on ERPNext's own Project Template."""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

#: The Task fields a template task keeps, beside its dates.
KEPT = ("subject", "description", "priority", "type", "is_group", "is_milestone", "expected_time", "task_weight", "color")

#: What ERPNext's copy leaves out and the new task takes from its template task.
LEFT_OUT = ("is_milestone", "expected_time")

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


@frappe.whitelist(methods=["POST"])
def add(project: str, template: str, starts: str | None = None) -> int:
	"""A template's tasks added to a running project, dated from `starts`
	(today when not given). Returns how many were made."""
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Project Template", "read", template, throw=True)
	frappe.has_permission("Task", "create", throw=True)
	doc = frappe.get_doc("Project", project)
	# ERPNext's copy counts each task's Begin On from the project's start; here
	# that's the day chosen, and the project itself isn't saved.
	doc.expected_start_date = getdate(starts or nowdate())
	sources = [frappe.get_doc("Task", row.task) for row in frappe.get_doc("Project Template", template).tasks]
	if not sources:
		frappe.throw(_("{0} has no tasks.").format(template))
	made = [doc.create_task_from_template(one) for one in sources]
	doc.dependency_mapping(sources, made)
	return len(made)


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
