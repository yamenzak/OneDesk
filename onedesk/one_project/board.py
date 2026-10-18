"""A project's board: its tasks by status, on the desk's own Kanban."""

import json

import frappe

from onedesk.one import boards

OVERDUE_JOB = "erpnext.projects.doctype.task.task.set_tasks_as_overdue"

COLUMNS = {
	"Open": ("Blue", "Active"),
	"Working": ("Orange", "Active"),
	"Pending Review": ("Purple", "Active"),
	"Completed": ("Green", "Active"),
	"Cancelled": ("Gray", "Archived"),
	"Template": ("Gray", "Archived"),
}

STANDARD_BOARD = "Task Status"

CARD = {"priority": "flag", "exp_end_date": "calendar"}


HEALTH_BOARD = "Projects by Health"
HEALTH = {"On Track": "Green", "At Risk": "Orange", "Off Track": "Red"}
BOARDING = ["project_type", "!=", "Employee Boarding"]
HEALTH_FILTERS = [["Project", "status", "=", "Open", False]]
HEALTH_CARD = {"customer": "building-2", "expected_end_date": "calendar"}


def settle(*_args) -> None:
	"""Stop the Overdue job, give back the status it took, shape the boards
	already made, and make the Projects board."""
	job = frappe.db.exists("Scheduled Job Type", {"method": OVERDUE_JOB})
	if job and not frappe.db.get_value("Scheduled Job Type", job, "stopped"):
		frappe.db.set_value("Scheduled Job Type", job, "stopped", 1)
	frappe.db.sql("update `tabTask` set status = 'Open' where status = 'Overdue'")
	for row in frappe.get_all(
		"Kanban Board Column",
		filters={"parent": STANDARD_BOARD, "parenttype": "Kanban Board", "column_name": "Overdue", "status": "Active"},
		pluck="name",
	):
		frappe.db.set_value("Kanban Board Column", row, "status", "Archived", update_modified=False)
	for name in frappe.get_all(
		"Kanban Board",
		filters={"reference_doctype": "Task", "field_name": "status", "is_standard": ["!=", "Yes"]},
		pluck="name",
	):
		board = frappe.get_doc("Kanban Board", name)
		if shape(board):
			board.flags.ignore_permissions = True
			board.save()
	if frappe.db.exists("Kanban Board", HEALTH_BOARD):
		board = frappe.get_doc("Kanban Board", HEALTH_BOARD)
		kept = [one for one in json.loads(board.filters or "[]") if one[1:4] != BOARDING]
		changed = len(kept) != len(json.loads(board.filters or "[]"))
		board.filters = json.dumps(kept)
		if boards.cards(board, HEALTH_CARD) or changed:
			board.flags.ignore_permissions = True
			board.save()
		return
	board = frappe.new_doc("Kanban Board")
	board.update(
		{
			"kanban_board_name": HEALTH_BOARD,
			"reference_doctype": "Project",
			"field_name": "one_health",
			"filters": json.dumps(HEALTH_FILTERS),
			"private": 0,
		}
	)
	for column, colour in HEALTH.items():
		board.append("columns", {"column_name": column, "indicator": colour, "status": "Active"})
	boards.cards(board, HEALTH_CARD)
	board.insert(ignore_permissions=True)


def shape(doc, method=None) -> bool:
	"""A board of tasks by status, shaped. Whether anything changed. An app's
	own board is the app's (saving it in developer mode writes its file)."""
	if doc.reference_doctype != "Task" or doc.field_name != "status" or doc.is_standard == "Yes":
		return False
	before = [(one.column_name, one.indicator, one.status) for one in doc.columns]
	doc.set("columns", [one for one in doc.columns if one.column_name in COLUMNS])
	for one in doc.columns:
		one.indicator, one.status = COLUMNS[one.column_name]
	carded = boards.cards(doc, CARD)
	return carded or before != [(one.column_name, one.indicator, one.status) for one in doc.columns]
