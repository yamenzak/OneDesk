"""OneTask's tours (one/tours.py, docs/READY.md mechanism 10), one for each
area of its screens, found by the mark at `at`; each step points at a
`data-tour` mark, the window's own (window-*) or OneTask's. My Tasks has one
area, the list of what is yours, with OneTask's rail beside it."""

from frappe import _lt

MY_TASKS = [
	{
		"target": "window-nav",
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
		"title": _lt("Due First"),
		"text": _lt("Tasks come by when they are due; tick one when it is done, or time it with the play button."),
	},
	{
		"target": "window-tour",
		"side": "top",
		"title": _lt("Settings and Tours"),
		"text": _lt("Settings is the cog, and the tour runs again from the button beside it."),
	},
]

TOURS = [{"key": "my_tasks", "at": "onetask-list", "steps": MY_TASKS}]
