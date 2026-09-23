"""OneProject on the calendar: a project's own, with every task in it still to
do, whoever is on them, beside the events about the project (one_calendar/
events.py). Dragging one moves it as it does on anybody's calendar."""

from frappe import _lt

from onedesk.one_task.calendar import DONE, due

LAYERS = [
	{
		"key": "project-tasks",
		"label": _lt("Tasks"),
		"color": "purple",
		"group": "Workspace",
		"doctype": "Task",
		"rows": "onedesk.one_project.calendar.tasks",
		"move": "onedesk.one_task.calendar.move",
		"about": ["Project"],
		"only_about": True,
	},
]


def tasks(start, end, record: tuple) -> list[dict]:
	"""Every task in one project not yet done, whoever is on it."""
	return due([["project", "=", record[1]], ["status", "not in", DONE]], start, end)
