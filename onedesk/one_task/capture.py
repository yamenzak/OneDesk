"""Every to-do is a task."""

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
	# A repeat's people, or the colleagues OneAI's card named (one_task/ai.py).
	given = doc.flags.one_assign_to or [one.strip() for one in (doc.get("one_for") or "").split(",") if one.strip()]
	if given:
		assign({"doctype": "Task", "name": doc.name, "assign_to": given})
		# Said once: a repeat of this task is given to whoever has it then.
		if doc.get("one_for"):
			frappe.db.set_value("Task", doc.name, "one_for", None, update_modified=False)
		return
	if doc.project or doc.is_template or doc.flags.one_assigned or frappe.flags.in_install or frappe.flags.in_migrate:
		return
	if frappe.parse_json(doc.get("_assign") or "[]") or doc.owner in ("Administrator", "Guest"):
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
