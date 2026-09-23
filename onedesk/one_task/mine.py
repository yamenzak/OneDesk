"""My Tasks: everything assigned to the reader and still to do, by when it is due.

Read as the reader, so it is exactly the tasks they may see and were given.
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


@frappe.whitelist()
@frappe.read_only()
def tasks() -> list[dict]:
	"""The reader's tasks in their groups, each group only if it has any."""
	user = frappe.session.user
	rows = frappe.get_list(
		"Task",
		filters=[["_assign", "like", f'%"{user}"%'], ["status", "not in", DONE]],
		fields=["name", "subject", "status", "priority", "project", "exp_start_date", "exp_end_date", "is_milestone"],
		limit=MOST,
	)
	# Where each task is, as a path through sub-projects: Villa › Handrails.
	# The reader may be on a task in a project they cannot open; its name is
	# already on the task, so its path is no more than that.
	from onedesk.one_project.tree import path

	titles = {project: path(project) for project in {one.project for one in rows if one.project}}
	today = getdate(nowdate())
	grouped = {}
	for one in rows:
		due = one.exp_end_date or one.exp_start_date
		one.due = getdate(due) if due else None
		one.project_title = titles.get(one.project) or one.project
		grouped.setdefault(when(one.due, today), []).append(one)
	return [
		{
			"key": key,
			"label": str(label),
			"tasks": sorted(
				grouped[key],
				key=lambda one: (one.due or date.max, PRIORITY.get(one.priority, 2), (one.subject or "").lower()),
			),
		}
		for key, label in GROUPS.items()
		if key in grouped
	]
