"""A project's time, for the page's Time view (docs/PROJECT-PAGE.md).

Every hour is ERPNext's Timesheet Detail on the project or a project under
it, read as the reader reads timesheets, so somebody who may see only their
own sees only their own. Each entry says where it stands: a draft not yet
submitted, not billable, still to invoice, or invoiced on a Sales Invoice.

**Log Time** (`log`) writes an entry into the reader's draft timesheet for
the week, the one the task timer (one_task/timer.py) writes into, so time
logged by hand and timed by the clock end up in the same place and are
submitted together.
"""

from datetime import datetime, time, timedelta
from typing import Annotated

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, get_first_day, get_fullname, getdate, nowdate

from onedesk.one_project import tree
from onedesk.one_task import timer

#: How many entries the view lists, newest first; the totals count them all.
SHOWN = 200

#: Where an hand-logged entry starts on its day when nothing else is logged.
DAY_STARTS = time(9, 0)


def state(docstatus: int, billable: bool, invoice: str | None) -> str:
	"""Where an entry stands. Pure."""
	if docstatus == 0:
		return "Draft"
	if invoice:
		return "Invoiced"
	return "To Invoice" if billable else "Not Billable"


@frappe.whitelist()
@frappe.read_only()
def entries(project: Annotated[str, "The project."]) -> dict:
	"""The project tree's time, newest first, with its totals."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	projects = sorted(tree.below({project}, tree.parents()))
	rows = frappe.get_list(
		"Timesheet Detail",
		parent_doctype="Timesheet",
		filters=[["Timesheet Detail", "project", "in", projects], ["Timesheet", "docstatus", "<", 2]],
		fields=[
			"name",
			"parent",
			"project",
			"task",
			"activity_type",
			"from_time",
			"hours",
			"is_billable",
			"billing_amount",
			"sales_invoice",
			"description",
			"docstatus",
		],
		order_by="from_time desc",
		limit_page_length=0,
	)
	people = whose({row.parent for row in rows})
	month = getdate(get_first_day(nowdate()))
	totals = {"month": 0.0, "hours": 0.0, "billable": 0.0, "to_invoice": 0.0, "invoiced": 0.0, "drafts": 0.0}
	for row in rows:
		hours = flt(row.hours)
		totals["hours"] += hours
		if row.from_time and getdate(row.from_time) >= month:
			totals["month"] += hours
		if row.docstatus == 0:
			totals["drafts"] += hours
		if row.is_billable:
			totals["billable"] += hours
			if row.docstatus == 1:
				totals["invoiced" if row.sales_invoice else "to_invoice"] += flt(row.billing_amount)
	tasks = dict(
		frappe.get_all(
			"Task",
			filters={"name": ["in", list({row.task for row in rows if row.task})]},
			fields=["name", "subject"],
			as_list=True,
		)
	)
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ["in", projects]}, fields=["name", "project_name"], as_list=True
		)
	)
	return {
		"totals": {key: round(value, 2) for key, value in totals.items()},
		"entries": [
			{
				"name": row.name,
				"timesheet": row.parent,
				"user": people.get(row.parent, {}).get("user"),
				"who": people.get(row.parent, {}).get("name"),
				"date": str(getdate(row.from_time)) if row.from_time else None,
				"hours": flt(row.hours),
				"activity": row.activity_type,
				"task": row.task,
				"task_subject": tasks.get(row.task),
				"project": row.project,
				"project_title": titles.get(row.project),
				"amount": flt(row.billing_amount),
				"state": state(row.docstatus, bool(row.is_billable), row.sales_invoice),
				"invoice": row.sales_invoice,
				"description": row.description,
			}
			for row in rows[:SHOWN]
		],
		"more": max(0, len(rows) - SHOWN),
		"can_log": bool(frappe.has_permission("Timesheet", "create")),
		# A retainer's hours are billed with its month (retainer.py), not here.
		"can_invoice": frappe.db.get_value("Project", project, "one_kind") != "Retainer"
		and bool(frappe.db.get_value("Project", project, "customer"))
		and bool(frappe.has_permission("Sales Invoice", "create")),
	}


@frappe.whitelist(methods=["POST"])
def log(
	project: Annotated[str, "The project."],
	date: Annotated[str, "The day the work was done."],
	hours: Annotated[float, "How long it took."],
	activity_type: Annotated[str, "The activity, which prices the hours."],
	task: Annotated[str | None, "The task, if the time was on one."] = None,
	description: Annotated[str | None, "What was done."] = None,
	billable: Annotated[int | None, "Whether the customer is billed for it."] = None,
) -> str:
	"""An entry in the reader's draft timesheet for the week. Its timesheet."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	frappe.has_permission("Timesheet", "create", throw=True)
	if flt(hours) <= 0:
		frappe.throw(_("Give the time a number of hours."))
	if task and frappe.db.get_value("Task", task, "project") not in tree.below({project}, tree.parents()):
		frappe.throw(_("{0} is not a task on this project.").format(task))
	if billable is None:
		billable = 1 if frappe.db.get_value("Project", project, "customer") else 0
	sheet = timer._this_week(frappe.session.user)
	starts = after(sheet, getdate(date))
	sheet.append(
		"time_logs",
		{
			"project": project,
			"task": task,
			"activity_type": activity_type,
			"from_time": starts,
			"to_time": starts + timedelta(hours=flt(hours)),
			"hours": flt(hours),
			"completed": 1,
			"is_billable": 1 if billable else 0,
			"description": description,
		},
	)
	sheet.save()
	return sheet.name


def after(sheet, day) -> datetime:
	"""Where a new entry on a day starts: after the last one the timesheet has
	that day, so two never overlap, or at the start of the working day."""
	ends = [
		get_datetime(row.to_time) for row in sheet.time_logs if row.to_time and getdate(row.to_time) == day
	]
	return max(ends) if ends else datetime.combine(day, DAY_STARTS)


def whose(sheets) -> dict[str, dict]:
	"""Who each timesheet is for: its user, its employee's, or, with no
	employee, whoever made it; and the name to show, the employee's when it
	has one. A timesheet made for an employee by somebody else (HR, an
	import) has no user of its own."""
	found = frappe.get_all(
		"Timesheet",
		filters={"name": ["in", list(sheets)]},
		fields=["name", "user", "employee", "employee_name", "owner"],
	)
	linked = dict(
		frappe.get_all(
			"Employee",
			filters={"name": ["in", list({one.employee for one in found if one.employee})]},
			fields=["name", "user_id"],
			as_list=True,
		)
	)
	said = {}
	for one in found:
		# A timesheet with no employee is its maker's, as the timer keeps it.
		user = one.user or linked.get(one.employee) or (None if one.employee else one.owner)
		said[one.name] = {
			"user": user,
			"key": user or one.employee or one.name,
			"name": one.employee_name or (get_fullname(user) if user else None),
		}
	return said
