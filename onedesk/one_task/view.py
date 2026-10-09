"""A task's page (page/task_view, frontend/src/task): the task as its reader
may see it, what it waits on and what waits on it, its checklist, its
sub-tasks and the time logged on it. The page only reads here; it changes the
task as desk does (set_value, insert, assign) and through task.py."""

from datetime import date
from typing import Annotated

import frappe
from frappe.utils import cint, date_diff, flt, format_date, getdate, nowdate

from onedesk.one_project.hours import bills_hours
from onedesk.one_task.capture import DONE
from onedesk.one_task.mine import about

#: What the page reads of the task itself.
FIELDS = (
	"name",
	"subject",
	"status",
	"priority",
	"project",
	"parent_task",
	"is_group",
	"is_milestone",
	"is_template",
	"exp_start_date",
	"exp_end_date",
	"expected_time",
	"actual_time",
	"progress",
	"description",
	"type",
	"completed_on",
	"completed_by",
	"review_date",
	"auto_repeat",
	"one_bill_share",
	"one_about_doctype",
	"one_about",
	"owner",
	"modified",
	"_assign",
)

#: The most time entries the Time view lists; the rest open in the Timesheet list.
MOST = 200


def headline(status: str, due: date | None, waiting: list[str], today: date) -> dict | None:
	"""The one thing worth saying above the task, if anything: waiting on
	other work, late, or due today. Pure."""
	if status in ("Completed", "Cancelled"):
		return None
	if waiting:
		return {"key": "waiting", "names": waiting, "tone": "orange"}
	if status == "Pending Review":
		return {"key": "review", "tone": "blue"}
	if due and due < today:
		return {"key": "late", "days": date_diff(today, due), "tone": "red"}
	if due and due == today:
		return {"key": "today", "tone": "orange"}
	return None


@frappe.whitelist()
@frappe.read_only()
def read(task: Annotated[str, "The task."]) -> dict:
	"""The task as its page shows it, read as the reader."""
	frappe.has_permission("Task", "read", doc=task, throw=True)
	doc = frappe.get_doc("Task", task)
	said = {field: doc.get(field) for field in FIELDS if field != "_assign"}
	assigned = frappe.parse_json(doc.get("_assign") or "[]")
	meta = frappe.get_meta("Task")
	today = getdate(nowdate())
	due = getdate(doc.exp_end_date or doc.exp_start_date) if (doc.exp_end_date or doc.exp_start_date) else None

	# A parent's own sub-tasks are in its Depends On too, and listed as its
	# sub-tasks instead.
	under = set(frappe.get_all("Task", filters={"parent_task": task}, pluck="name"))
	waits = _readable([row.task for row in doc.depends_on if row.task not in under], ["name", "subject", "status"])
	waiting = [one.subject for one in waits if one.status not in DONE]
	# ERPNext lists a sub-task in its parent's Depends On, so the parent is
	# what the task is part of, not work waiting on it.
	blocking = _readable(
		[
			one
			for one in frappe.get_all("Task Depends On", filters={"task": task, "parenttype": "Task"}, pluck="parent")
			if one != doc.parent_task
		],
		["name", "subject", "status"],
	)
	sub_tasks = frappe.get_list(
		"Task",
		filters={"parent_task": task},
		fields=["name", "subject", "status", "exp_end_date", "_assign"],
		order_by="exp_start_date asc, creation asc",
	)
	people = set(assigned) | {doc.owner, doc.completed_by}
	for one in sub_tasks:
		one.assigned = frappe.parse_json(one.pop("_assign") or "[]")
		people.update(one.assigned)
	time = _time(task)
	people.update(one["user"] for one in time["entries"] if one.get("user"))

	said.update(
		{
			"assigned": assigned,
			"due": str(due) if due else None,
			"late_by": date_diff(today, due) if due and due < today and doc.status not in DONE else 0,
			"headline": headline(doc.status, due, waiting, today),
			"project_title": frappe.db.get_value("Project", doc.project, "project_name") if doc.project else None,
			"above": _above(doc),
			"about_title": about(doc.one_about_doctype, doc.one_about) if doc.one_about_doctype and doc.one_about else None,
			"steps": [{"name": row.name, "step": row.step, "done": cint(row.done)} for row in doc.get("one_steps") or []],
			"waits": [{"name": one.name, "subject": one.subject, "done": one.status in DONE} for one in waits],
			"blocking": [{"name": one.name, "subject": one.subject, "status": one.status} for one in blocking],
			"sub_tasks": sub_tasks,
			"time": time,
			"repeat": _repeat(doc.auto_repeat),
			"bills_hours": bills_hours(doc.project),
			"files": files(task),
			"people": _people_of(people),
			"statuses": [one for one in meta.get_field("status").options.split("\n") if one and one != "Template"],
			"priorities": [one for one in meta.get_field("priority").options.split("\n") if one],
			"can_write": bool(frappe.has_permission("Task", "write", doc=doc)),
			"can_create": bool(frappe.has_permission("Task", "create")),
			"can_time": bool(frappe.has_permission("Timesheet", "create")) and doc.status not in DONE,
			"can_delete": bool(frappe.has_permission("Task", "delete", doc=doc)),
		}
	)
	return said


@frappe.whitelist()
@frappe.read_only()
def files(task: Annotated[str, "The task."]) -> int:
	"""How many files are attached to the task, as the reader may see them."""
	frappe.has_permission("Task", "read", doc=task, throw=True)
	return len(
		frappe.get_list("File", filters={"attached_to_doctype": "Task", "attached_to_name": task, "is_folder": 0}, pluck="name")
	)


def _readable(names: list[str], fields: list[str]) -> list:
	"""Those of the tasks the reader may see, in the order given."""
	if not names:
		return []
	found = {one.name: one for one in frappe.get_list("Task", filters={"name": ["in", names]}, fields=fields)}
	return [found[name] for name in names if name in found]


def _above(doc) -> list[dict]:
	"""The tasks this one sits under, outermost first, as far as the reader may see."""
	chain, seen, parent = [], {doc.name}, doc.parent_task
	while parent and parent not in seen and len(chain) < 10:
		seen.add(parent)
		if not frappe.has_permission("Task", "read", doc=parent):
			break
		row = frappe.db.get_value("Task", parent, ["name", "subject", "parent_task"], as_dict=True)
		if not row:
			break
		chain.insert(0, {"name": row.name, "subject": row.subject})
		parent = row.parent_task
	return chain


def _time(task: str) -> dict:
	"""The hours logged on the task, as the reader may read timesheets: who,
	the day, the activity and the hours, newest first, with drafts apart."""
	if not frappe.has_permission("Timesheet", "read"):
		return {"entries": [], "logged": 0, "drafts": 0, "more": 0}
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters={"task": task, "docstatus": ["<", 2]},
		fields=["parent", "from_time", "hours", "activity_type", "docstatus", "is_billable", "description"],
		order_by="from_time desc",
		limit=MOST + 1,
	)
	sheets = {one.parent for one in rows}
	who = {
		one.name: one
		for one in frappe.get_list(
			"Timesheet", filters={"name": ["in", list(sheets)]}, fields=["name", "employee", "employee_name", "user"]
		)
	} if sheets else {}
	entries = [
		{
			"sheet": one.parent,
			"day": str(getdate(one.from_time)) if one.from_time else None,
			"hours": flt(one.hours),
			"activity": one.activity_type,
			"draft": one.docstatus == 0,
			"billable": cint(one.is_billable),
			"description": one.description,
			"who": (who.get(one.parent) or {}).get("employee_name"),
			"user": (who.get(one.parent) or {}).get("user"),
		}
		for one in rows[:MOST]
	]
	return {
		"entries": entries,
		"logged": flt(sum(one["hours"] for one in entries if not one["draft"]), 2),
		"drafts": flt(sum(one["hours"] for one in entries if one["draft"]), 2),
		"more": max(0, len(rows) - MOST),
	}


def _repeat(name: str | None) -> dict | None:
	"""How the task repeats, where it does."""
	if not name or not frappe.has_permission("Auto Repeat", "read", doc=name):
		return None
	row = frappe.db.get_value("Auto Repeat", name, ["name", "frequency", "disabled", "next_schedule_date"], as_dict=True)
	if not row:
		return None
	return {
		"name": row.name,
		"frequency": row.frequency,
		"disabled": cint(row.disabled),
		"next": format_date(row.next_schedule_date) if row.next_schedule_date else None,
	}


def _people_of(users) -> dict:
	"""Each user's name and picture, for avatars."""
	users = [one for one in users if one]
	if not users:
		return {}
	return {
		one.name: {"name": one.full_name or one.name, "image": one.user_image}
		for one in frappe.get_all("User", filters={"name": ["in", users]}, fields=["name", "full_name", "user_image"])
	}

