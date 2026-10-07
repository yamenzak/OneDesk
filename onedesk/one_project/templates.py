"""A project started from one that went well, on ERPNext's own Project Template."""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

from onedesk.one_project.library import copy

#: The Task fields a template task keeps, beside its dates.
KEPT = (
	"subject",
	"description",
	"priority",
	"type",
	"is_group",
	"is_milestone",
	"expected_time",
	"task_weight",
	"color",
)

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


def days_kept(doc, method=None) -> None:
	"""Task before_validate: a template task begins on a day after the
	project starts, never before it, and lasts no fewer than none."""
	if not doc.is_template:
		return
	if (doc.start or 0) < 0 or (doc.duration or 0) < 0:
		frappe.throw(_("A template task cannot begin before the project or last fewer than no days."))


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
		for step in frappe.get_all(
			"Task Step", filters={"parent": task.name, "parenttype": "Task"}, fields=["step"], order_by="idx"
		):
			copy.append("one_steps", {"step": step.step})
		copy.insert()
		made[task.name] = copy.name
	for task in tasks:
		waits = frappe.get_all(
			"Task Depends On", filters={"parent": task.name, "parenttype": "Task"}, pluck="task"
		)
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
def add(
	project: str, template: str | None = None, starts: str | None = None, library: str | None = None
) -> int:
	"""A template's tasks added to a running project, dated from `starts`
	(today when not given). A preset from the library is copied in first.
	Returns how many were made."""
	frappe.has_permission("Project", "read", project, throw=True)
	template = template or (library and copy(library))
	if not template:
		frappe.throw(_("Pick a template."))
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
	dates = [
		getdate(day)
		for task in tasks
		for day in (task.get("exp_start_date"), task.get("exp_end_date"))
		if day
	]
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


def measured(doc, method=None) -> None:
	"""Project Template validate: how many tasks it holds, beside the phases
	they sit in, and how many days it runs, for its list."""
	names = [row.task for row in doc.tasks if row.task]
	found = frappe.get_all(
		"Task", filters={"name": ["in", names or [""]]}, fields=["is_group", "start", "duration"]
	)
	doc.one_tasks = sum(1 for one in found if not one.is_group)
	doc.one_days = max(((one.start or 0) + (one.duration or 0) for one in found), default=0)


def task_measured(doc, method=None) -> None:
	"""Task on_update: a template task changed on its own form, or in a bulk
	edit, counts again in the templates that hold it."""
	if not doc.is_template:
		return
	for name in frappe.get_all("Project Template Task", filters={"task": doc.name}, pluck="parent", distinct=True):
		template = frappe.get_doc("Project Template", name)
		measured(template)
		template.db_set({"one_tasks": template.one_tasks, "one_days": template.one_days}, update_modified=False)


def used(doc, method=None) -> None:
	"""Project on_update and on_trash: how many projects each template it was
	or is started from now has."""
	before = doc.get_doc_before_save()
	for name in {doc.project_template, before.project_template if before else None} - {None, ""}:
		counted(name, leaving=doc.name if method == "on_trash" else None)


def counted(template: str, leaving: str | None = None) -> None:
	if not frappe.db.exists("Project Template", template):
		return
	filters = {"project_template": template}
	if leaving:
		filters["name"] = ["!=", leaving]
	frappe.db.set_value(
		"Project Template", template, "one_projects", frappe.db.count("Project", filters), update_modified=False
	)
