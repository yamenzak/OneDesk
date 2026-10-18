"""A timer on a task, written into the person's timesheet as it runs.

One runs at a time. Pausing it, or starting another, ends its line on the
timesheet and keeps the task among the person's timers, paused, so it can be
resumed on a new line. Stopping it takes it off. The paused tasks are a user
default (PAUSED), the person's own list.
"""

import json

import erpnext
import frappe
from frappe.utils import flt, get_datetime, get_first_day_of_week, getdate, now_datetime, time_diff_in_hours

from onedesk.one_task.capture import DONE

PAUSED = "one_timers_paused"

SLIP = 1 / 60


def _employee(user: str) -> str | None:
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def _drafts(user: str) -> list[str]:
	"""The person's timesheets not yet submitted, newest first."""
	employee = _employee(user)
	whose = {"employee": employee} if employee else {"owner": user, "employee": ["is", "not set"]}
	return frappe.get_all(
		"Timesheet",
		filters={"docstatus": 0, "company": erpnext.get_default_company(), **whose},
		pluck="name",
		order_by="creation desc",
	)


def _running_row(user: str):
	drafts = _drafts(user)
	if not drafts:
		return None
	rows = frappe.get_all(
		"Timesheet Detail",
		filters={
			"parenttype": "Timesheet",
			"parent": ["in", drafts],
			"from_time": ["is", "set"],
			"to_time": ["is", "not set"],
		},
		fields=["name", "parent", "task", "from_time"],
		order_by="from_time desc",
		limit=1,
	)
	return rows[0] if rows else None


@frappe.whitelist()
@frappe.read_only()
def running() -> dict | None:
	"""The reader's running timer: which task, since when, on which timesheet."""
	row = _running_row(frappe.session.user)
	if not row:
		return None
	return {
		"task": row.task,
		"subject": frappe.db.get_value("Task", row.task, "subject") if row.task else None,
		"since": str(row.from_time),
		"timesheet": row.parent,
	}


@frappe.whitelist(methods=["POST"])
def start(task: str) -> dict | None:
	"""Start timing a task, or resume it, pausing whatever was running."""
	from onedesk.one_project.hours import bills_hours

	doc = frappe.get_doc("Task", task)
	doc.check_permission("read")
	pause()
	_paused_set([one for one in _paused() if one != doc.name])
	user = frappe.session.user
	sheet = _this_week(user)
	sheet.append(
		"time_logs",
		{
			"task": doc.name,
			"project": doc.project,
			"activity_type": _last_activity(user),
			"from_time": now_datetime(),
			"completed": 0,
			"is_billable": 1 if bills_hours(doc.project) else 0,
		},
	)
	sheet.save()
	_told()
	return running()


@frappe.whitelist(methods=["POST"])
def pause() -> float:
	"""End the running timer's line and keep its task among the reader's
	timers, to resume. The hours it added."""
	row = _running_row(frappe.session.user)
	if not row:
		return 0
	hours = _end(row)
	if row.task:
		_paused_set([row.task, *[one for one in _paused() if one != row.task]])
	_told()
	return hours


@frappe.whitelist(methods=["POST"])
def stop(task: str | None = None) -> float:
	"""Stop the reader's running timer, if one is, or take a paused one off
	their timers. The hours it added, which are none when it was a slip or
	it was paused."""
	row = _running_row(frappe.session.user)
	if task and (not row or row.task != task):
		_paused_set([one for one in _paused() if one != task])
		_told()
		return 0
	if not row:
		return 0
	_paused_set([one for one in _paused() if one != row.task])
	hours = _end(row)
	_told()
	return hours


@frappe.whitelist()
@frappe.read_only()
def timers() -> dict:
	"""The reader's timers: the one running and the ones paused, each with
	its task, where it is and the hours on it today, for the rail's Timers."""
	from onedesk.one_task.mine import place

	now = running()
	names = [one for one in ([now["task"]] if now and now.get("task") else []) + _paused()]
	company = erpnext.get_default_company()
	readable = {
		one.name: one
		for one in frappe.get_list(
			"Task",
			filters={"name": ["in", names or [""]], "company": company},
			fields=["name", "subject", "project", "status"],
		)
	}
	today = _today(names)
	titles = dict(
		frappe.get_all(
			"Project",
			filters={
				"name": ["in", [one.project for one in readable.values() if one.project] or [""]],
				"company": company,
			},
			fields=["name", "project_name"],
			as_list=True,
		)
	)

	def said(name):
		one = readable[name]
		return {
			"task": name,
			"subject": one.subject,
			"place": place(one.project, titles.get(one.project)),
			"today": flt(today.get(name), 2),
		}

	paused = [
		said(one)
		for one in _paused()
		if one in readable and readable[one].status not in DONE and one != (now or {}).get("task")
	]
	if now and now.get("task") in readable:
		now = {**now, **said(now["task"])}
	return {"running": now, "paused": paused}


def _end(row) -> float:
	"""End a running line now. The hours it added, none for a slip."""
	sheet = frappe.get_doc("Timesheet", row.parent)
	one = next(line for line in sheet.time_logs if line.name == row.name)
	ends = now_datetime()
	if slip(get_datetime(one.from_time), ends):
		sheet.remove(one)
		if not sheet.time_logs:
			sheet.delete()
			return 0
		sheet.save()
		return 0
	one.to_time = ends
	one.hours = time_diff_in_hours(ends, one.from_time)
	sheet.save()
	return one.hours


def _paused() -> list[str]:
	return json.loads(frappe.defaults.get_user_default(PAUSED) or "[]")


def _paused_set(names: list[str]) -> None:
	frappe.defaults.set_user_default(PAUSED, json.dumps(names))


def _today(tasks: list[str]) -> dict:
	"""The hours the reader logged on each task today, closed lines only."""
	sheets = _sheets(frappe.session.user)
	if not tasks or not sheets:
		return {}
	rows = frappe.get_all(
		"Timesheet Detail",
		filters={
			"parenttype": "Timesheet",
			"parent": ["in", sheets],
			"task": ["in", tasks],
			"from_time": [">=", getdate()],
			"to_time": ["is", "set"],
		},
		fields=["task", "hours"],
	)
	total = {}
	for one in rows:
		total[one.task] = total.get(one.task, 0) + flt(one.hours)
	return total


def _sheets(user: str) -> list[str]:
	"""The person's timesheets, drafts and submitted."""
	employee = _employee(user)
	whose = {"employee": employee} if employee else {"owner": user, "employee": ["is", "not set"]}
	return frappe.get_all(
		"Timesheet",
		filters={"docstatus": ["<", 2], "company": erpnext.get_default_company(), **whose},
		pluck="name",
	)


def _told() -> None:
	"""Every screen of the reader's that shows a timer: the rail's Timers, My
	Tasks and a task's page."""
	frappe.publish_realtime("one_timers", {}, user=frappe.session.user, after_commit=True)


def slip(starts, ends) -> bool:
	"""Whether a timer ran too short to be anything but a mis-click. Pure."""
	return (ends - starts).total_seconds() / 3600 < SLIP


def _this_week(user: str):
	"""The person's draft timesheet for this week, or a new one."""
	monday = get_first_day_of_week(now_datetime().date())
	for name in _drafts(user):
		sheet = frappe.get_doc("Timesheet", name)
		if sheet.start_date and sheet.start_date >= monday:
			return sheet
	sheet = frappe.new_doc("Timesheet")
	sheet.employee = _employee(user)
	return sheet


def _last_activity(user: str) -> str | None:
	employee = _employee(user)
	whose = {"employee": employee} if employee else {"owner": user}
	sheets = frappe.get_all("Timesheet", filters=whose, pluck="name", order_by="creation desc", limit=5)
	if not sheets:
		return None
	found = frappe.get_all(
		"Timesheet Detail",
		filters={"parent": ["in", sheets], "activity_type": ["is", "set"]},
		pluck="activity_type",
		order_by="creation desc",
		limit=1,
	)
	return found[0] if found else None
