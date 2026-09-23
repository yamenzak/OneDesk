"""Every to-do is a task.

frappe has two things called a to-do. A **ToDo** is an assignment — somebody
was given something to do about a record — and assigning a task, a deal or a
leave application makes one. A ToDo with nothing it is about is the other kind:
a note to self, made from the ToDo form or `frappe.desk.doctype.todo.todo.new_todo`,
and it lives outside everything else — no project, no sub-tasks, no board.

So One keeps one kind of work, the Task:

- **A to-do with nothing it is about becomes a task** (`todo_made`). The task is
  made from what was typed, and the ToDo is kept as what it always was, the
  assignment on it. Whoever it was for is still who it is for.
- **A task made with no project and nobody on it is its maker's**
  (`task_made`), so "assigned to me" is the one question that finds all of a
  person's work, on the calendar and in every list.
- **Ticking off the last assignment on a task with no project completes it**
  (`todo_changed`). ERPNext already does the other direction: completing a
  task closes its assignments. A task in a project is not completed by one
  person being done with it.
"""

import frappe
from frappe.desk.form.assign_to import add as assign

from onedesk.one_calendar.layers import plain

#: What a task that is still to do cannot be.
DONE = ("Completed", "Cancelled", "Template")


def todo_made(doc, method=None) -> None:
	"""ToDo before_insert: a to-do about nothing is made a task first."""
	if doc.reference_type or doc.reference_name or not plain(doc.description):
		return
	task = frappe.new_doc("Task")
	task.update(
		{
			"subject": plain(doc.description, 140),
			"description": doc.description,
			"priority": doc.priority or "Medium",
			"exp_end_date": doc.date,
		}
	)
	task.flags.one_assigned = True
	task.insert()
	doc.reference_type, doc.reference_name = "Task", task.name


def task_made(doc, method=None) -> None:
	"""Task after_insert: a task of nobody's, with no project, is its maker's;
	a repeat is given to whoever had the task it repeats (task.recurring)."""
	if doc.flags.one_assign_to:
		assign({"doctype": "Task", "name": doc.name, "assign_to": doc.flags.one_assign_to})
		return
	if doc.project or doc.flags.one_assigned or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if frappe.parse_json(doc.get("_assign")) or doc.owner in ("Administrator", "Guest"):
		return
	assign({"doctype": "Task", "name": doc.name, "assign_to": [doc.owner]})


def todo_changed(doc, method=None) -> None:
	"""ToDo on_update: the last assignment ticked off completes a task of one's own."""
	if doc.reference_type != "Task" or doc.status != "Closed" or not doc.has_value_changed("status"):
		return
	task = frappe.db.get_value("Task", doc.reference_name, ["project", "status"], as_dict=True)
	if not task or task.project or task.status in DONE:
		return
	if frappe.db.exists("ToDo", {"reference_type": "Task", "reference_name": doc.reference_name, "status": "Open"}):
		return
	one = frappe.get_doc("Task", doc.reference_name)
	one.status = "Completed"
	one.flags.ignore_permissions = True
	one.save()
