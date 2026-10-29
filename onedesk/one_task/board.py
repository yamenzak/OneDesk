"""OneTask's two boards: the reader's tasks and their Inbox, on frappe's own Kanban."""

import json

import frappe

# Each board is filtered to its reader in public/js/one_task/task_kanban.js, which
# adds the assignment (and, for the Inbox, no project) to its filters.
BOARDS = ("My Tasks", "Inbox")

FILTERS = [["Task", "is_template", "=", 0]]


def settle(*_args) -> None:
	"""Make the two boards where they are missing; a board kept has been the
	workspace's to change since."""
	for name in BOARDS:
		if frappe.db.exists("Kanban Board", name):
			continue
		board = frappe.new_doc("Kanban Board")
		board.update(
			{
				"kanban_board_name": name,
				"reference_doctype": "Task",
				"field_name": "status",
				"filters": json.dumps(FILTERS),
				"private": 0,
			}
		)
		for column in ("Open", "Working", "Pending Review", "Completed", "Cancelled"):
			board.append("columns", {"column_name": column})
		board.insert(ignore_permissions=True)
