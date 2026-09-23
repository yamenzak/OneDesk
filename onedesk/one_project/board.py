"""A project's board: its tasks by status, on the desk's own Kanban.

ERPNext already makes one. **View › Kanban Board** on a project creates a board
named after it, filtered to its tasks, with a column per Task status. This
shapes that board as it is made (`shape`, on the Kanban Board's before_insert):
Template and Cancelled are archived, the columns get colours, and a card shows
the priority and the due date beside the people on it.

**Overdue is not a status here.** ERPNext's daily job sets every open task past
its due date to Overdue, whatever it was — a task somebody was Working on moves
columns overnight, and moving it back lasts until the next night. How late a
task is follows from its date, and every list in One already shows it from
there (My Tasks has an Overdue group; the calendar draws it on its day). So the
job is stopped, and Overdue is taken off the status list (custom/task.json).
ERPNext's Project Summary report counted Overdue tasks, and now counts none.
"""

import json

import frappe

#: ERPNext's nightly job that turns open tasks past their date to Overdue.
OVERDUE_JOB = "erpnext.projects.doctype.task.task.set_tasks_as_overdue"

#: Each column, its colour, and whether it is shown.
COLUMNS = {
	"Open": ("Blue", "Active"),
	"Working": ("Orange", "Active"),
	"Pending Review": ("Purple", "Active"),
	"Completed": ("Green", "Active"),
	"Cancelled": ("Gray", "Archived"),
	"Template": ("Gray", "Archived"),
}

#: What a card shows under the task's subject.
CARD = ["priority", "exp_end_date"]


def settle(*_args) -> None:
	"""Stop the Overdue job, give back the status it took, and shape the
	boards already made."""
	job = frappe.db.exists("Scheduled Job Type", {"method": OVERDUE_JOB})
	if job and not frappe.db.get_value("Scheduled Job Type", job, "stopped"):
		frappe.db.set_value("Scheduled Job Type", job, "stopped", 1)
	frappe.db.sql("update `tabTask` set status = 'Open' where status = 'Overdue'")
	for name in frappe.get_all("Kanban Board", filters={"reference_doctype": "Task", "field_name": "status"}, pluck="name"):
		board = frappe.get_doc("Kanban Board", name)
		if shape(board):
			board.flags.ignore_permissions = True
			board.save()


def shape(doc, method=None) -> bool:
	"""A board of tasks by status, shaped. Whether anything changed."""
	if doc.reference_doctype != "Task" or doc.field_name != "status":
		return False
	before = [(one.column_name, one.indicator, one.status) for one in doc.columns] + [doc.fields, doc.show_labels]
	doc.set("columns", [one for one in doc.columns if one.column_name in COLUMNS])
	for one in doc.columns:
		one.indicator, one.status = COLUMNS[one.column_name]
	doc.fields = json.dumps(CARD)
	doc.show_labels = 0
	return before != [(one.column_name, one.indicator, one.status) for one in doc.columns] + [doc.fields, doc.show_labels]
