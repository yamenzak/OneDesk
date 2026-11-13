"""OneTask's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneTask's. My Tasks is a
board (task_kanban.js marks it), with OneTask's rail beside it."""

from frappe import _lt

MY_TASKS = [
	{
		"target": "interface-nav",
		"side": "right",
		"title": _lt("Your Tasks and Inbox"),
		"text": _lt("My Tasks is everything given to you, and Inbox is what has no project yet."),
	},
	{
		"target": "onetask-add",
		"side": "bottom",
		"title": _lt("Add a Task"),
		"text": _lt("Type it and press Enter, with a due date if it has one, and it is yours."),
	},
	{
		"target": "onetask-list",
		"side": "top",
		"title": _lt("A Column for Each Status"),
		"text": _lt("Drag a task to Completed when it is done, or time it with the play button on its card."),
	},
	{
		"target": "interface-tour",
		"side": "top",
		"title": _lt("Help and Tours"),
		"text": _lt("Help is the question mark and the tour is the button beside it, with Settings under the arrow at the end of the top bar."),
	},
]

TASK = [
	{
		"target": "record-cards",
		"side": "bottom",
		"title": _lt("When and How Long"),
		"text": _lt("When it is due or how late, its checklist, what it waits on and the hours logged against the plan."),
	},
	{
		"target": "record-panel",
		"side": "left",
		"title": _lt("Who Is On It"),
		"text": _lt("Assign gives it to somebody, and Activity holds the comments and every change."),
	},
]

TOURS = [
	{"key": "my_tasks", "at": "onetask-list", "steps": MY_TASKS},
	{"key": "task", "at": "record-task", "steps": TASK},
]
