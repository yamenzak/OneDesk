"""OneTask's page: the reader's tasks still to do, by when they are due."""

from datetime import date, timedelta

import erpnext
import frappe
from frappe import _lt
from frappe.utils import getdate, nowdate

from onedesk.one_task.capture import DONE

MOST = 500

GROUPS = {
	"overdue": _lt("Overdue"),
	"today": _lt("Today"),
	"tomorrow": _lt("Tomorrow"),
	"week": _lt("Next 7 Days"),
	"later": _lt("Later"),
	"none": _lt("No Due Date"),
}

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


VIEWS = ("mine", "inbox")


def _filters(view: str, user: str) -> tuple[list, list | None]:
	"""What a view lists, as `filters` and `or_filters`. The Inbox is what is
	given to the reader outside any project, as its board shows it
	(one_task/task_kanban.js): a task they made is theirs (capture.py)."""
	if view == "inbox":
		return (
			[["_assign", "like", f'%"{user}"%'], ["project", "is", "not set"], ["is_template", "=", 0], ["status", "not in", DONE]],
			None,
		)
	return [["_assign", "like", f'%"{user}"%'], ["status", "not in", DONE]], None


def due(task) -> date | None:
	"""When a task is due: its end, or its start when it has no end."""
	day = task.exp_end_date or task.exp_start_date
	return getdate(day) if day else None


@frappe.whitelist()
@frappe.read_only()
def tasks(view: str = "mine") -> list[dict]:
	"""The reader's tasks in a view, in their groups, each group only if it has any."""
	filters, or_filters = _filters(view if view in VIEWS else "mine", frappe.session.user)
	rows = frappe.get_list(
		"Task",
		filters=[*filters, ["company", "=", erpnext.get_default_company()]],
		or_filters=or_filters,
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
	waiting = _waiting([one.name for one in rows])
	from onedesk.one_project.tree import path

	titles = {project: path(project) for project in {one.project for one in rows if one.project}}
	places = {project: place(project, title) for project, title in titles.items()}
	today = getdate(nowdate())
	grouped = {}
	for one in rows:
		one.due = due(one)
		one.project_title = titles.get(one.project) or one.project
		one.place = places.get(one.project)
		one.waiting = waiting.get(one.name, 0)
		if not one.project and one.one_about_doctype and one.one_about:
			one.about_title = about(one.one_about_doctype, one.one_about)
		one.subject = unnamed(one.subject, (one.place or {}).get("label") or one.get("about_title"))
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


def _waiting(names: list[str]) -> dict[str, int]:
	"""How many tasks each of these waits on that are still to do. A parent's
	own sub-tasks are in its Depends On too (ERPNext lists them there), and
	are its work, not work it waits on."""
	if not names:
		return {}
	rows = frappe.get_all(
		"Task Depends On", filters={"parenttype": "Task", "parent": ["in", names]}, fields=["parent", "task"]
	)
	if not rows:
		return {}
	open_ = {
		one.name: one.parent_task
		for one in frappe.get_all(
			"Task",
			filters={
				"name": ["in", list({one.task for one in rows})],
				"status": ["not in", DONE],
				"company": erpnext.get_default_company(),
			},
			fields=["name", "parent_task"],
		)
	}
	waiting = {}
	for one in rows:
		if one.task in open_ and open_[one.task] != one.parent:
			waiting[one.parent] = waiting.get(one.parent, 0) + 1
	return waiting


def place(project: str | None, title: str | None = None) -> dict | None:
	"""Where a task in a project opens: the project's page, or, for an
	onboarding's or an exit's checklist, that onboarding or exit, with no route
	for a reader who may not open it. Its project is HRMS's, and not a project
	of OneProject's (one_hr/lifecycle.py)."""
	if not project:
		return None
	from onedesk.one_hr.lifecycle import BOARDINGS

	for doctype in BOARDINGS:
		found = frappe.db.get_value(doctype, {"project": project}, ["name", "employee_name"], as_dict=True)
		if found:
			return {
				"label": found.employee_name or found.name,
				"route": f"/desk/{frappe.scrub(doctype).replace('_', '-')}/{found.name}"
				if frappe.has_permission(doctype, "read", doc=found.name)
				else None,
				"kind": doctype,
			}
	return {"label": title or project, "route": f"/desk/project/{project}", "kind": "Project"}


def unnamed(subject: str | None, where: str | None) -> str | None:
	"""A task's subject without the name the row already says beside it: HRMS
	names an onboarding's step "Plan the first week : Feras Odeh". Pure."""
	if subject and where and subject.endswith(f" : {where}") and len(subject) > len(where) + 3:
		return subject[: -len(where) - 3]
	return subject


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
	company = ["company", "=", erpnext.get_default_company()]
	filters, or_filters = _filters("inbox", user)
	inbox = frappe.get_list(
		"Task", filters=[*filters, company], or_filters=or_filters, pluck="name", limit=MOST
	)
	mine = frappe.get_list(
		"Task",
		filters=[*_filters("mine", user)[0], company],
		fields=["exp_start_date", "exp_end_date"],
		limit=MOST,
	)
	today = getdate(nowdate())
	late = sum(1 for one in mine if when(due(one), today) == "overdue")
	return {"mine": len(mine), "inbox": len(inbox), "late": late}
