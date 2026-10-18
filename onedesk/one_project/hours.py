"""A project's time, for the page's Time view (docs/PROJECT-PAGE.md)."""

from datetime import datetime, time, timedelta
from typing import Annotated

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, get_first_day, get_fullname, getdate, nowdate

from onedesk.one_project import kinds, tree
from onedesk.one_project.money import _route as money_route
from onedesk.one_project.money import currency as money_currency
from onedesk.one_task import timer

TIMESHEETS = "Timesheets"
ATTENDANCE = "Attendance on Site"
NOT_TRACKED = "Not Tracked"
METHODS = (TIMESHEETS, ATTENDANCE, NOT_TRACKED)

SHOWN = 200

DAY_STARTS = time(9, 0)


def default() -> str:
	"""How the workspace counts time on a new project."""
	found = frappe.db.get_single_value("Projects Settings", "one_time_default")
	return found if found in METHODS else TIMESHEETS


def settle() -> None:
	"""`after_sync` and `after_migrate`: the default stored, since a Single
	shows a default only before it is first saved."""
	if frappe.db.get_single_value("Projects Settings", "one_time_default") not in METHODS:
		frappe.db.set_single_value("Projects Settings", "one_time_default", TIMESHEETS)


def method(project: str | None) -> str:
	"""How a project counts its time."""
	found = frappe.db.get_value("Project", project, "one_time") if project else None
	return found if found in METHODS else TIMESHEETS


def billed_by_the_hour(kind: str | None) -> bool:
	"""Whether a kind's hours are billable: Time and Materials and Retainer
	bill hours, Fixed Price and Internal count them as cost. Pure."""
	return kind in (kinds.TIME, kinds.RETAINER)


def bills_hours(project: str | None) -> bool:
	"""Whether an hour on a project is billable unless somebody says not."""
	if not project:
		return False
	found = frappe.db.get_value("Project", project, ["one_kind", "customer"], as_dict=True)
	return bool(found and found.customer and billed_by_the_hour(found.one_kind))


@frappe.whitelist()
@frappe.read_only()
def billed_hourly(project: Annotated[str, "The project."]) -> bool:
	"""Whether an hour on the project is billable unless somebody says not,
	for desk's timesheet form."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	return bills_hours(project)


def billable(doc, method=None) -> None:
	"""Timesheet before_insert: a row on a project billed by the hour is
	billable, as Log Time and the timer make it, however the timesheet is
	made: OneHR, the API or Data Import. Desk's form ticks it as the project
	is picked (timesheet.js), so a row somebody unticked there stays so."""
	if (frappe.form_dict or {}).get("cmd") == "frappe.desk.form.save.savedocs":
		return
	for row in doc.get("time_logs") or []:
		if row.project and not row.is_billable and bills_hours(row.project):
			row.is_billable = 1


def on_its_project(doc, method=None) -> None:
	"""Timesheet validate: a row's task is on the row's project or one under
	it, however the row is written."""
	for row in doc.get("time_logs") or []:
		if not (row.task and row.project):
			continue
		on = frappe.db.get_value("Task", row.task, "project")
		if on and on not in tree.below({row.project}, tree.parents()):
			frappe.throw(_("Row {0}: {1} is not a task on {2}.").format(row.idx, row.task, row.project))


def fill(doc, method=None) -> None:
	"""Project before_validate: how it counts time, the workspace's default
	when nobody said; a site only on a project counted by attendance, and
	only one open project at a site."""
	if doc.get("one_time") not in METHODS:
		doc.one_time = default()
	if doc.one_time != ATTENDANCE:
		doc.one_site = None
		return
	if not doc.get("one_site"):
		frappe.throw(_("Pick the site."))
	if doc.status != "Open":
		return
	taken = frappe.db.get_value(
		"Project",
		{"one_site": doc.one_site, "one_time": ATTENDANCE, "status": "Open", "name": ["!=", doc.name or ""]},
		"project_name",
	)
	if taken:
		frappe.throw(_("{0} is already the site of {1}.").format(doc.one_site, taken))


def state(docstatus: int, billable: bool, invoice: str | None) -> str:
	"""Where an entry stands. Pure."""
	if docstatus == 0:
		return "Draft"
	if invoice:
		return "Invoiced"
	return "To Invoice" if billable else "Not Billable"


def sees_rates() -> bool:
	"""Whether the reader may see what time costs and bills: ERPNext keeps a
	timesheet's rates and amounts to those it lets read them (Accounts User,
	by default)."""
	return 1 in frappe.get_meta("Timesheet").get_permlevel_access("read")


def count(rows: list, month, money: bool) -> dict:
	"""The figures over the entries: hours this month and in all, what's on
	drafts, and, for whoever sees money, what's to invoice, invoiced and what
	it cost, all in the company's currency. A draft is no cost yet. Pure."""
	totals = {"month": 0.0, "hours": 0.0, "drafts": 0.0}
	if money:
		totals.update({"to_invoice": 0.0, "invoiced": 0.0, "cost": 0.0})
	for row in rows:
		hours = flt(row.get("hours"))
		totals["hours"] += hours
		if row.get("from_time") and getdate(row["from_time"]) >= month:
			totals["month"] += hours
		if row.get("docstatus") == 0:
			totals["drafts"] += hours
			continue
		if not money:
			continue
		totals["cost"] += flt(row.get("base_costing_amount"))
		if row.get("is_billable"):
			totals["invoiced" if row.get("sales_invoice") else "to_invoice"] += flt(
				row.get("base_billing_amount")
			)
	return {key: round(value, 2) for key, value in totals.items()}


def planned(projects: list[str]) -> float:
	"""The hours the tree's open and finished tasks plan, a cancelled one's
	left out (ERPNext's Expected Time)."""
	found = frappe.get_all(
		"Task",
		filters={"project": ["in", projects], "status": ["not in", ("Cancelled", "Template")]},
		pluck="expected_time",
	)
	return round(sum(flt(one) for one in found), 2)


def sums(rows: list, people: dict, tasks: dict, where) -> list[dict]:
	"""The entries counted, with their hours, amount and cost, by person,
	activity, task, place under the project and where each stands."""
	found: dict[tuple, dict] = {}
	for row in rows:
		who = people.get(row.parent, {})
		key = (
			who.get("user"),
			who.get("name"),
			row.activity_type,
			tasks.get(row.task),
			where(row),
			state(row.docstatus, bool(row.is_billable), row.sales_invoice),
		)
		one = found.setdefault(
			key,
			dict(zip(("user", "who", "activity", "task_subject", "where", "state"), key, strict=True))
			| {"entries": 0, "hours": 0.0, "amount": 0.0, "cost": 0.0},
		)
		one["entries"] += 1
		one["hours"] += flt(row.hours)
		if row.docstatus == 0:
			continue
		one["amount"] += flt(row.get("base_billing_amount")) if row.is_billable else 0.0
		one["cost"] += flt(row.get("base_costing_amount"))
	return list(found.values())


@frappe.whitelist()
@frappe.read_only()
def entries(
	project: Annotated[str, "The project."],
	only: Annotated[bool | None, "Only the project's own work, not what is under it."] = None,
) -> dict:
	"""The project tree's time, newest first, with its figures: hours for
	everybody, money for whoever may see rates."""
	from onedesk.one_project import milestones

	frappe.has_permission("Project", "read", doc=project, throw=True)
	tree.narrow(project, only)
	of = tree.parents()
	projects = sorted(tree.scope(project))
	money = sees_rates()
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
			"sales_invoice",
			"description",
			"docstatus",
			*(("base_billing_amount", "base_costing_amount") if money else ()),
		],
		order_by="from_time desc",
		limit_page_length=0,
	)
	people = whose({row.parent for row in rows})
	faces = _faces(people.values())
	head = frappe.db.get_value(
		"Project", project, ["one_kind", "customer", "one_monthly_hours", "company"], as_dict=True
	)
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
	totals = count(rows, getdate(get_first_day(nowdate())), money)
	whole = frappe.get_all(
		"Project", filters={"name": ["in", projects]}, fields=["one_hours_planned", "one_time_budget"]
	)
	totals["planned"] = planned(projects) or round(sum(flt(one.one_hours_planned) for one in whole), 2)
	totals["time_budget"] = round(sum(flt(one.one_time_budget) for one in whole), 2) if money else None
	billing_on = sorted(
		{
			titles.get(row.project) or row.project
			for row in rows
			if row.is_billable and row.docstatus == 1 and not row.sales_invoice and row.project != project
		}
	)
	return {
		"kind": head.one_kind,
		"time": method(project),
		"bills_hours": billed_by_the_hour(head.one_kind),
		"money": money,
		"currency": money_currency(project),
		"totals": totals,
		"billing_on": billing_on,
		"entries": [
			{
				"name": row.name,
				"timesheet": row.parent,
				"user": people.get(row.parent, {}).get("user"),
				"who": people.get(row.parent, {}).get("name"),
				"image": faces.get(
					people.get(row.parent, {}).get("user") or people.get(row.parent, {}).get("employee")
				),
				"date": str(getdate(row.from_time)) if row.from_time else None,
				"hours": flt(row.hours),
				"activity": row.activity_type,
				"task": row.task,
				"task_subject": tasks.get(row.task),
				"project": row.project,
				"where": milestones.where(row.project, project, of, titles),
				"amount": flt(row.get("base_billing_amount")) if row.is_billable else None,
				"cost": flt(row.get("base_costing_amount")) if money else None,
				"state": state(row.docstatus, bool(row.is_billable), row.sales_invoice),
				"invoice": row.sales_invoice,
				"description": row.description,
			}
			for row in rows[:SHOWN]
		],
		"more": max(0, len(rows) - SHOWN),
		"sums": sums(rows, people, tasks, lambda row: milestones.where(row.project, project, of, titles)),
		"all_route": money_route("Timesheet", {"Timesheet Detail.project": ["in", projects], "docstatus": ["<", 2]}),
		"has_sub_projects": len(projects) > 1,
		"allowance": flt(head.one_monthly_hours) if head.one_kind == kinds.RETAINER else None,
		"can_log": method(project) != ATTENDANCE and bool(frappe.has_permission("Timesheet", "create")),
		"can_budget": bool(frappe.has_permission("Project", "write", doc=project)),
		"can_invoice": head.one_kind != kinds.RETAINER
		and bool(head.customer)
		and bool(frappe.has_permission("Sales Invoice", "create")),
	}


def late_drafts(projects: list[str], user: str) -> list[dict]:
	"""Needs You: the reader's own timesheets still in draft with time on the
	projects from before this week, to submit."""
	from frappe.utils import get_first_day_of_week

	monday = get_first_day_of_week(getdate(nowdate()))
	found = frappe.get_all(
		"Timesheet Detail",
		filters={
			"project": ["in", projects],
			"parenttype": "Timesheet",
			"docstatus": 0,
			"from_time": ["<", str(monday)],
		},
		fields=["parent", "hours"],
	)
	if not found:
		return []
	mine = {
		name: info for name, info in whose({row.parent for row in found}).items() if info.get("user") == user
	}
	said = []
	for sheet in sorted(mine):
		hours = sum(flt(row.hours) for row in found if row.parent == sheet)
		said.append(
			{
				"tone": "orange",
				"text": _("Submit your timesheet"),
				"dim": _("{0} h not submitted").format(f"{hours:g}"),
				"route": f"/desk/timesheet/{sheet}",
				"mine": True,
			}
		)
	return said


@frappe.whitelist(methods=["POST"])
def log(
	project: Annotated[str, "The project."],
	date: Annotated[str, "The day the work was done."],
	hours: Annotated[float, "How long it took."],
	activity_type: Annotated[str, "The activity, which prices the hours."],
	task: Annotated[str | None, "The task, if the time was on one."] = None,
	description: Annotated[str | None, "What was done."] = None,
	billable: Annotated[int | None, "Whether the customer is billed for it."] = None,
	on: Annotated[str | None, "The project or sub-project the time was on, when not the page's."] = None,
) -> str:
	"""An entry in the reader's draft timesheet for the week, on the task's
	project, or the one chosen under the page's. Its timesheet."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	frappe.has_permission("Timesheet", "create", throw=True)
	if flt(hours) <= 0:
		frappe.throw(_("Give the time a number of hours."))
	below = tree.below({project}, tree.parents())
	if task:
		on = frappe.db.get_value("Task", task, "project")
		if on not in below:
			frappe.throw(_("{0} is not a task on this project.").format(task))
	if on and on not in below:
		frappe.throw(_("{0} is not under this project.").format(on))
	project = on or project
	if billable is None:
		billable = 1 if bills_hours(project) else 0
	sheet = timer._this_week(frappe.session.user)
	starts = after(sheet, getdate(date), _elsewhere(sheet, getdate(date)))
	sheet.append(
		"time_logs",
		{
			"project": project,
			"task": task,
			"activity_type": activity_type,
			"from_time": starts,
			"to_time": starts + timedelta(hours=flt(hours)),
			"hours": flt(hours),
			"completed": 0,
			"is_billable": 1 if billable else 0,
			"description": description,
		},
	)
	sheet.save()
	return sheet.name


def after(sheet, day, elsewhere=()) -> datetime:
	"""Where a new entry on a day starts: after the last one the person has
	that day, on this timesheet or `elsewhere` (when another ended), so two
	never overlap, or at the start of the working day. Pure."""
	ends = [
		get_datetime(row.to_time) for row in sheet.time_logs if row.to_time and getdate(row.to_time) == day
	]
	ends += [get_datetime(one) for one in elsewhere]
	return max(ends) if ends else datetime.combine(day, DAY_STARTS)


def _elsewhere(sheet, day) -> list:
	"""When the person's entries that day on their other timesheets end:
	ERPNext refuses an entry that overlaps any of them, submitted ones too."""
	if not sheet.employee:
		return []
	others = frappe.get_all(
		"Timesheet",
		filters={"employee": sheet.employee, "docstatus": ["<", 2], "name": ["!=", sheet.name or ""]},
		pluck="name",
	)
	if not others:
		return []
	return frappe.get_all(
		"Timesheet Detail",
		filters={
			"parenttype": "Timesheet",
			"parent": ["in", others],
			"from_time": ["<=", datetime.combine(day, datetime.max.time())],
			"to_time": [">=", datetime.combine(day, datetime.min.time())],
		},
		pluck="to_time",
	)


def _faces(people) -> dict:
	"""The picture of each person `whose` found: their user's, or their
	employee's when they have no user."""
	people = list(people)
	users = [one["user"] for one in people if one["user"]]
	employees = [one["employee"] for one in people if one["employee"] and not one["user"]]
	faces = dict(
		frappe.get_all(
			"User", filters={"name": ["in", users or [""]]}, fields=["name", "user_image"], as_list=True
		)
	)
	faces.update(
		frappe.get_all(
			"Employee", filters={"name": ["in", employees or [""]]}, fields=["name", "image"], as_list=True
		)
	)
	return faces


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
		user = one.user or linked.get(one.employee) or (None if one.employee else one.owner)
		said[one.name] = {
			"user": user,
			"key": user or one.employee or one.name,
			"name": one.employee_name or (get_fullname(user) if user else None),
			"employee": one.employee,
		}
	return said
