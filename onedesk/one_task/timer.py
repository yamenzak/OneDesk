"""A timer on a task, written into the person's timesheet as it runs.

Time is ERPNext's Timesheet, which payroll, costing and billing already read;
this only saves somebody opening one. **Start** adds a row to the person's
draft timesheet for the week — made if there is none — with the task, its
project and a start. **Stop** gives the row its end, and ERPNext works out the
hours. One timer runs at a time: starting another stops the first.

A row with a start and no end is the running one, which is the same rule as
the Timesheet form's own timer (public/js/timesheet.js), so either can stop
what the other started. Every stamp is `now_datetime`, the site's clock, for
the reason given there. A timer stopped within a minute of starting was a
slip, and its row is taken out rather than left at nought hours to be refused
on submit.

Time on a project with a customer is billable until somebody unticks it: an
unticked hour quietly never reaches an invoice, and a ticked one is a line
somebody is looking at anyway.

The activity is the one the person used last, since it is required when the
timesheet is submitted and is usually the same all week; they change it on the
timesheet when it is not.
"""

import frappe
from frappe.utils import get_datetime, get_first_day_of_week, now_datetime, time_diff_in_hours

#: Shorter than this, in hours, and a timer was started by mistake.
SLIP = 1 / 60


def _employee(user: str) -> str | None:
	return frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")


def _drafts(user: str) -> list[str]:
	"""The person's timesheets not yet submitted, newest first."""
	employee = _employee(user)
	whose = {"employee": employee} if employee else {"owner": user, "employee": ["is", "not set"]}
	return frappe.get_all("Timesheet", filters={"docstatus": 0, **whose}, pluck="name", order_by="creation desc")


def _running_row(user: str):
	drafts = _drafts(user)
	if not drafts:
		return None
	rows = frappe.get_all(
		"Timesheet Detail",
		filters={"parenttype": "Timesheet", "parent": ["in", drafts], "from_time": ["is", "set"], "to_time": ["is", "not set"]},
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
	"""Start timing a task, stopping whatever was running."""
	doc = frappe.get_doc("Task", task)
	doc.check_permission("read")
	stop()
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
			"is_billable": 1 if doc.project and frappe.db.get_value("Project", doc.project, "customer") else 0,
		},
	)
	sheet.save()
	return running()


@frappe.whitelist(methods=["POST"])
def stop() -> float:
	"""Stop the reader's running timer, if one is. The hours it added, which
	are none when it was a slip."""
	row = _running_row(frappe.session.user)
	if not row:
		return 0
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
	one.completed = 1
	sheet.save()
	return one.hours


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
