"""OneProject on the calendar: a project's own, with every task in it still to
do, whoever is on them, beside the events about the project (one_calendar/
events.py). Dragging one moves it as it does on anybody's calendar.

A parent's calendar has its sub-projects' tasks too, each titled with where it
is — Handrails · Fit the rails — so the villa's month is the whole villa."""

import frappe
from frappe import _lt

from onedesk.one_project import members, tree
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
	"""Every task in one project and the projects under it, not yet done."""
	top = record[1]
	user = frappe.session.user
	projects = [one for one in tree.below({top}, tree.parents()) if one == top or members.sees(one, user)]
	rows = due([["project", "in", projects], ["status", "not in", DONE]], start, end)
	where = dict(frappe.get_all("Task", filters={"name": ["in", [row["name"] for row in rows]]}, fields=["name", "project"], as_list=True)) if rows else {}
	titles = dict(frappe.get_all("Project", filters={"name": ["in", projects]}, fields=["name", "project_name"], as_list=True))
	for row in rows:
		project = where.get(row["name"])
		if project and project != top:
			row["title"] = f"{titles.get(project) or project} · {row['title']}"
	return rows
