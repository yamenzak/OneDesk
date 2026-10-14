"""Who has how many hours of open work in a week, against the hours they have."""

import frappe
from frappe import _
from frappe.utils import add_days, cint, date_diff, flt, get_first_day_of_week, getdate, nowdate

from onedesk.one_project import tree

#: What a working day is when HR Settings does not say.
DAY = 8.0

OPEN = ("Open", "Working", "Pending Review")


def execute(filters=None):
	filters = filters or {}
	starts = get_first_day_of_week(getdate(filters.get("week") or nowdate()))
	ends = add_days(starts, 6)
	where = [["status", "in", OPEN], ["is_template", "=", 0]]
	if filters.get("project"):
		where.append(["project", "in", list(tree.below({filters["project"]}, tree.parents()))])
	tasks = frappe.get_list(
		"Task",
		filters=where,
		fields=["name", "_assign", "exp_start_date", "exp_end_date", "expected_time", "actual_time"],
		limit=0,
	)
	people: dict[str, dict] = {}
	for task in tasks:
		assigned = frappe.parse_json(task._assign or "[]") or []
		if not assigned:
			continue
		due = task.exp_end_date or task.exp_start_date
		if not due:
			continue
		left = max(flt(task.expected_time) - flt(task.actual_time), 0)
		hours = in_week(task.exp_start_date, due, starts, ends, left)
		if hours is None:
			continue
		for user in assigned:
			one = people.setdefault(user, {"hours": 0.0, "tasks": 0, "late": 0, "unestimated": 0})
			one["hours"] += hours / len(assigned)
			one["tasks"] += 1
			one["late"] += getdate(due) < getdate(nowdate())
			one["unestimated"] += not flt(task.expected_time)
	# Everyone on an open project's team, so whoever has room shows with it.
	for user in team(filters.get("project")):
		people.setdefault(user, {"hours": 0.0, "tasks": 0, "late": 0, "unestimated": 0})
	per_day = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")) or DAY
	rows = []
	for user, one in people.items():
		capacity = working_days(user, starts, ends) * per_day
		named = frappe.db.get_value("User", user, ["full_name", "user_image"], as_dict=True) or {}
		rows.append(
			{
				"user": user,
				"full_name": named.get("full_name"),
				"image": named.get("user_image"),
				"capacity": capacity,
				"planned": round(one["hours"], 1),
				"free": round(capacity - one["hours"], 1),
				"load": load(one["hours"], capacity),
				"tasks": one["tasks"],
				"late": one["late"],
				"unestimated": one["unestimated"],
			}
		)
	rows.sort(key=lambda row: (-(row["load"] or 0), -row["late"], row["full_name"] or row["user"]))
	week = _("Week of {0} to {1}").format(frappe.format(starts, "Date"), frappe.format(ends, "Date"))
	return columns(), rows, week, None, summary(rows)


def team(project: str | None = None) -> list[str]:
	"""The people on the team of each open project, or of `project` and the
	projects under it, who can still sign in."""
	where = {"status": "Open"}
	if project:
		where = {"name": ["in", list(tree.below({project}, tree.parents()))]}
	# Only the projects the reader may open: a team is who is on a project.
	projects = frappe.get_list("Project", filters=where, pluck="name", limit_page_length=0)
	if not projects:
		return []
	users = frappe.get_all(
		"Project User", filters={"parenttype": "Project", "parent": ["in", projects]}, pluck="user", distinct=True
	)
	return frappe.get_all("User", filters={"name": ["in", users or [""]], "enabled": 1}, pluck="name")


def summary(rows: list[dict]) -> list[dict]:
	"""The team's week at a glance: its hours, what's planned, what's free,
	and who is over. Hours are written as the table writes them, to a tenth
	(a summary's Float has no precision, so frappe would write three places)."""
	capacity = sum(row["capacity"] for row in rows)
	planned = sum(row["planned"] for row in rows)
	over = sum(1 for row in rows if (row["load"] or 0) > 100)
	return [
		{"label": _("Capacity (Hours)"), "value": hours(capacity), "datatype": "Data", "indicator": "Blue"},
		{"label": _("Planned (Hours)"), "value": hours(planned), "datatype": "Data", "indicator": "Blue"},
		{
			"label": _("Free (Hours)"),
			"value": hours(capacity - planned),
			"datatype": "Data",
			"indicator": "Green" if capacity >= planned else "Red",
		},
		{"label": _("Over Capacity"), "value": over, "datatype": "Int", "indicator": "Red" if over else "Green"},
	]


def hours(value: float) -> str:
	"""Hours as the table writes them, through frappe's own format."""
	return frappe.format(round(value, 1), {"fieldtype": "Float", "precision": 1})


def in_week(starts, due, week_starts, week_ends, hours: float) -> float | None:
	"""The share of a task's hours that falls in a week, or None when none of
	it does. Late work falls in full in the week it is late in. Pure."""
	due = getdate(due)
	starts = getdate(starts) if starts else due
	if starts > due:
		starts = due
	week_starts, week_ends = getdate(week_starts), getdate(week_ends)
	if due < week_starts:
		return hours if week_starts <= getdate(nowdate()) <= week_ends else None
	if starts > week_ends:
		return None
	days = date_diff(due, starts) + 1
	inside = date_diff(min(due, week_ends), max(starts, week_starts)) + 1
	return hours * inside / days


def load(planned: float, capacity: float) -> int | None:
	"""Planned against capacity, out of 100. Pure."""
	return round(100 * planned / capacity) if capacity else None


def working_days(user: str, starts, ends) -> float:
	"""The person's working days in the week: not a holiday, less approved leave."""
	employee = frappe.db.get_value("Employee", {"user_id": user, "status": "Active"}, "name")
	holidays = set()
	listed = None
	if employee:
		from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

		listed = get_holiday_list_for_employee(employee, raise_exception=False)
	if not listed:
		company = frappe.defaults.get_global_default("company")
		listed = frappe.get_cached_value("Company", company, "default_holiday_list") if company else None
	if listed:
		holidays = {
			getdate(day)
			for day in frappe.get_all(
				"Holiday", filters={"parent": listed, "holiday_date": ["between", [starts, ends]]}, pluck="holiday_date"
			)
		}
	days = [add_days(starts, n) for n in range(7)]
	working = [day for day in days if getdate(day) not in holidays] if listed else days[:5]
	away = 0.0
	if employee:
		for leave in frappe.get_all(
			"Leave Application",
			filters={"employee": employee, "status": "Approved", "docstatus": 1, "from_date": ["<=", ends], "to_date": [">=", starts]},
			fields=["from_date", "to_date", "half_day", "half_day_date"],
		):
			for day in working:
				if getdate(leave.from_date) <= getdate(day) <= getdate(leave.to_date):
					away += 0.5 if cint(leave.half_day) and getdate(leave.half_day_date or leave.from_date) == getdate(day) else 1
	return max(len(working) - away, 0)


def columns() -> list[dict]:
	return [
		{"fieldname": "user", "label": _("Person"), "fieldtype": "Link", "options": "User", "width": 220},
		{"fieldname": "full_name", "label": _("Name"), "fieldtype": "Data", "hidden": 1},
		{"fieldname": "image", "label": _("Image"), "fieldtype": "Data", "hidden": 1},
		{"fieldname": "capacity", "label": _("Capacity (Hours)"), "fieldtype": "Float", "precision": 1, "width": 150},
		{"fieldname": "planned", "label": _("Planned (Hours)"), "fieldtype": "Float", "precision": 1, "width": 150},
		{"fieldname": "free", "label": _("Free (Hours)"), "fieldtype": "Float", "precision": 1, "width": 130},
		{"fieldname": "load", "label": _("Load (%)"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "tasks", "label": _("Tasks"), "fieldtype": "Int", "width": 80},
		{"fieldname": "late", "label": _("Late"), "fieldtype": "Int", "width": 80},
		{"fieldname": "unestimated", "label": _("Not Estimated"), "fieldtype": "Int", "width": 120},
	]
