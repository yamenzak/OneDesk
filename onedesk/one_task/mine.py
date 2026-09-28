"""OneTask's page: the reader's tasks still to do, by when they are due.

Two views: **My Tasks**, everything assigned to the reader, and the **Inbox**,
the reader's own tasks in no project. Read as the reader, so it is exactly the
tasks they may see.
Ticking one off is the page writing the task's status through frappe's own
save (my_tasks.js), which ERPNext answers by closing its assignments — so this
file only reads.
"""

from datetime import date, timedelta

import frappe
from frappe import _lt
from frappe.utils import getdate, nowdate

from onedesk.one_task.capture import DONE

#: The most tasks one person's list shows.
MOST = 500

#: The groups, in the order they are shown.
GROUPS = {
	"overdue": _lt("Overdue"),
	"today": _lt("Today"),
	"tomorrow": _lt("Tomorrow"),
	"week": _lt("Next 7 Days"),
	"later": _lt("Later"),
	"none": _lt("No Due Date"),
}

#: Most pressing first, within a day.
PRIORITY = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}


def when(due: date | None, today: date) -> str:
	"""Which group a task due on this day is in. Pure."""
	if due is None:
		return "none"
	if due < today:
		return "overdue"
	if due == today:
		return "today"
	if due == today + timedelta(days=1):
		return "tomorrow"
	if due <= today + timedelta(days=7):
		return "week"
	return "later"


#: The page's views: what each lists, besides being still to do.
VIEWS = ("mine", "inbox")


def _filters(view: str, user: str) -> list:
	if view == "inbox":
		return [
			["owner", "=", user],
			["project", "is", "not set"],
			["is_template", "=", 0],
			["status", "not in", DONE],
		]
	return [["_assign", "like", f'%"{user}"%'], ["status", "not in", DONE]]


def due(task) -> date | None:
	"""When a task is due: its end, or its start when it has no end."""
	day = task.exp_end_date or task.exp_start_date
	return getdate(day) if day else None


@frappe.whitelist()
@frappe.read_only()
def tasks(view: str = "mine") -> list[dict]:
	"""The reader's tasks in a view, in their groups, each group only if it has any."""
	user = frappe.session.user
	rows = frappe.get_list(
		"Task",
		filters=_filters(view if view in VIEWS else "mine", user),
		fields=[
			"name",
			"subject",
			"status",
			"priority",
			"project",
			"exp_start_date",
			"exp_end_date",
			"is_milestone",
			"one_about_doctype",
			"one_about",
		],
		limit=MOST,
	)
	# Where each task is, as a path through sub-projects, Villa and then Handrails.
	# The reader may be on a task in a project they cannot open; its name is
	# already on the task, so its path is no more than that.
	from onedesk.one_project.tree import path

	titles = {project: path(project) for project in {one.project for one in rows if one.project}}
	today = getdate(nowdate())
	grouped = {}
	for one in rows:
		one.due = due(one)
		one.project_title = titles.get(one.project) or one.project
		# What a task OneIntake made is about, where it is in no project.
		if not one.project and one.one_about_doctype and one.one_about:
			one.about_title = about(one.one_about_doctype, one.one_about)
		grouped.setdefault(when(one.due, today), []).append(one)
	return [
		{
			"key": key,
			"label": str(label),
			"tasks": sorted(
				grouped[key],
				key=lambda one: (
					one.due or date.max,
					PRIORITY.get(one.priority, 2),
					(one.subject or "").lower(),
				),
			),
		}
		for key, label in GROUPS.items()
		if key in grouped
	]


def about(doctype: str, name: str) -> str:
	"""A record a task is about, by its title where the reader may read it."""
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read", doc=name):
		return name
	field = frappe.get_meta(doctype).get_title_field()
	return (field != "name" and frappe.db.get_value(doctype, name, field)) or name


@frappe.whitelist()
@frappe.read_only()
def counts() -> dict:
	"""How many tasks each view holds, and how many of the reader's are late,
	which is the Overdue group's own rule (`when`). Counted as the reader,
	through `get_list`: `frappe.db.count` is not."""
	user = frappe.session.user
	inbox = frappe.get_list("Task", filters=_filters("inbox", user), pluck="name", limit=MOST)
	mine = frappe.get_list(
		"Task", filters=_filters("mine", user), fields=["exp_start_date", "exp_end_date"], limit=MOST
	)
	today = getdate(nowdate())
	late = sum(1 for one in mine if when(due(one), today) == "overdue")
	return {"mine": len(mine), "inbox": len(inbox), "late": late}
