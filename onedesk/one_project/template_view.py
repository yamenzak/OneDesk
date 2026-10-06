"""A project template's page (page/project_template_view): its tasks as the
Tasks table shows a project's, each a day after the start and a number of
days long, changed in place. Every change saves the template, so ERPNext's own
checks on it run and whoever has it open hears it."""

import frappe
from frappe import _
from frappe.utils import cint, flt

#: What a task's row changes in place, and how a value is read.
FIELDS = {
	"subject": lambda value: (value or "").strip(),
	"start": cint,
	"duration": cint,
	"is_milestone": cint,
	"expected_time": flt,
}


@frappe.whitelist()
def read(template: str) -> dict:
	"""The template and its tasks, in its order, each with its depth and what
	it waits on."""
	frappe.has_permission("Project Template", "read", template, throw=True)
	doc = frappe.get_doc("Project Template", template)
	names = [row.task for row in doc.tasks]
	found = {
		one.name: one
		for one in frappe.get_all(
			"Task",
			filters={"name": ["in", names or [""]]},
			fields=[
				"name",
				"subject",
				"start",
				"duration",
				"parent_task",
				"is_group",
				"is_milestone",
				"expected_time",
			],
		)
	}
	waits = {}
	for one in frappe.get_all(
		"Task Depends On",
		filters={"parent": ["in", names or [""]], "parenttype": "Task"},
		fields=["parent", "task"],
		order_by="idx",
	):
		waits.setdefault(one.parent, []).append(one.task)
	tasks = []
	for name in names:
		task = found.get(name)
		if not task:
			continue
		depth, above = 0, task.parent_task
		while above in found and depth < 10:
			depth, above = depth + 1, found[above].parent_task
		# ERPNext lists a group's own tasks as what it waits on; those are the tree.
		own = {one.name for one in found.values() if one.parent_task == name}
		tasks.append({**task, "depth": depth, "waits": [one for one in waits.get(name, []) if one not in own]})
	return {
		"name": doc.name,
		"project_type": doc.project_type,
		"disabled": doc.disabled,
		"modified": doc.modified,
		"tasks": tasks,
		"days": max((one.start + one.duration for one in found.values()), default=0),
		"used": frappe.db.count("Project", {"project_template": doc.name}),
		"can_write": bool(frappe.has_permission("Project Template", "write", template)),
	}


@frappe.whitelist(methods=["POST"])
def change(template: str, task: str, field: str, value=None) -> None:
	"""One field of one of its tasks, as the task's form would save it."""
	if field not in FIELDS:
		frappe.throw(_("{0} cannot be changed here.").format(field))
	doc = _template(template, task)
	value = FIELDS[field](value)
	if field == "subject" and not value:
		frappe.throw(_("Name the task."))
	one = frappe.get_doc("Task", task)
	one.set(field, value)
	one.save()
	_saved(doc)


@frappe.whitelist(methods=["POST"])
def add(template: str, subject: str, parent: str | None = None) -> str:
	"""A new task at the end of the template, or of `parent`'s tasks. Returns
	its name."""
	doc = _template(template, parent)
	subject = (subject or "").strip()
	if not subject:
		frappe.throw(_("Name the task."))
	task = frappe.new_doc("Task")
	task.update({"subject": subject, "is_template": 1, "duration": 1})
	if parent:
		_group(parent)
		task.parent_task = parent
		task.start = frappe.db.get_value("Task", parent, "start") or 0
	task.insert()
	at = _after(doc, parent) if parent else len(doc.tasks)
	doc.append("tasks", {"task": task.name, "subject": subject})
	row = doc.tasks.pop()
	doc.tasks.insert(at, row)
	_saved(doc)
	return task.name


@frappe.whitelist(methods=["POST"])
def nest(template: str, task: str, parent: str | None = None) -> None:
	"""The task put under `parent`, or back at the top with none, its own
	tasks going with it."""
	doc = _template(template, task)
	if parent:
		_template(template, parent)
		if parent == task or task in _above(parent):
			frappe.throw(_("A task cannot go under itself."))
		_group(parent)
	one = frappe.get_doc("Task", task)
	before = one.parent_task
	one.parent_task = parent or None
	one.save()
	if before and not frappe.db.exists("Task", {"parent_task": before}):
		frappe.db.set_value("Task", before, "is_group", 0)
	moving = [task, *_below(doc, task)]
	rows = [row for row in doc.tasks if row.task in moving]
	doc.tasks = [row for row in doc.tasks if row.task not in moving]
	at = _after(doc, parent) if parent else len(doc.tasks)
	doc.tasks[at:at] = rows
	_saved(doc)


@frappe.whitelist(methods=["POST"])
def wait(template: str, task: str, on: str, waits: int = 1) -> None:
	"""The task waits on `on`, or no longer does."""
	doc = _template(template, task)
	_template(template, on)
	if on == task:
		frappe.throw(_("A task cannot wait on itself."))
	one = frappe.get_doc("Task", task)
	one.depends_on = [row for row in one.depends_on if row.task != on]
	if cint(waits):
		one.append("depends_on", {"task": on})
	one.save()
	_saved(doc)


@frappe.whitelist(methods=["POST"])
def remove(template: str, task: str) -> None:
	"""The task taken out of the template and deleted, with the tasks under
	it. Nothing else may still wait on them."""
	doc = _template(template, task)
	going = [task, *_below(doc, task)]
	waiting = frappe.get_all(
		"Task Depends On",
		filters={"task": ["in", going], "parent": ["not in", going], "parenttype": "Task"},
		pluck="parent",
	)
	for one in waiting:
		other = frappe.get_doc("Task", one)
		other.depends_on = [row for row in other.depends_on if row.task not in going]
		other.save()
	doc.tasks = [row for row in doc.tasks if row.task not in going]
	_saved(doc)
	for one in reversed(going):
		frappe.delete_doc("Task", one)
	parent = frappe.db.get_value("Task", task, "parent_task") if frappe.db.exists("Task", task) else None
	if parent and not frappe.db.exists("Task", {"parent_task": parent}):
		frappe.db.set_value("Task", parent, "is_group", 0)


def _template(template: str, task: str | None = None):
	"""The template, to be changed, and the task one of its own."""
	frappe.has_permission("Project Template", "write", template, throw=True)
	doc = frappe.get_doc("Project Template", template)
	if task and task not in {row.task for row in doc.tasks}:
		frappe.throw(_("{0} is not one of this template's tasks.").format(task))
	return doc


def _saved(doc) -> None:
	"""Each row says its task's name again, and the template is saved."""
	subjects = dict(
		frappe.get_all(
			"Task",
			filters={"name": ["in", [row.task for row in doc.tasks] or [""]]},
			fields=["name", "subject"],
			as_list=True,
		)
	)
	for at, row in enumerate(doc.tasks, 1):
		row.idx = at
		row.subject = subjects.get(row.task, row.subject)
	doc.save()


def _group(task: str) -> None:
	if not frappe.db.get_value("Task", task, "is_group"):
		frappe.db.set_value("Task", task, "is_group", 1)


def _below(doc, task: str) -> list[str]:
	"""Every task under `task`, however deep, in the template's order."""
	parents = dict(
		frappe.get_all(
			"Task",
			filters={"name": ["in", [row.task for row in doc.tasks]]},
			fields=["name", "parent_task"],
			as_list=True,
		)
	)
	under = []
	for row in doc.tasks:
		above = parents.get(row.task)
		while above:
			if above == task:
				under.append(row.task)
				break
			above = parents.get(above)
	return under


def _above(task: str) -> list[str]:
	found, above = [], frappe.db.get_value("Task", task, "parent_task")
	while above and len(found) < 20:
		found.append(above)
		above = frappe.db.get_value("Task", above, "parent_task")
	return found


def _after(doc, parent: str) -> int:
	"""Where a new task under `parent` goes: after the last of its tasks."""
	names = [row.task for row in doc.tasks]
	under = _below(doc, parent)
	return max([names.index(parent), *(names.index(one) for one in under)]) + 1
