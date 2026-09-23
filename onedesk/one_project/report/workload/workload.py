"""Who has how many hours of open work in a week, against the hours they have.

**Planned** is the hours still to do on each person's open tasks in the week:
a task's Expected Time less the time already logged on it (ERPNext's Actual
Time), spread evenly over the days from its start to its due date and counted
for the days that fall in the week, and shared equally when a task is given to
more than one person. Work already late counts in full this week, since that is
when it has to be done now. A task with only a due date is a day on it.

**Capacity** is the person's working days in the week — not a holiday on their
holiday list, not a day of approved leave — times HR Settings' **Standard
Working Hours**, 8 when it is not set. Somebody with no employee record works
the company's working days, or Monday to Friday where there is no holiday list.

Hours are only as good as the Expected Time on tasks, so **Not Estimated**
says how many of a person's tasks in the week have none: a light load with
five unestimated tasks is not a light load.

Only tasks the reader may see are counted. A project filter counts the tasks
of that project and everything under it.
"""

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
		assigned = frappe.parse_json(task._assign) or []
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
	per_day = flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")) or DAY
	rows = []
	for user, one in people.items():
		capacity = working_days(user, starts, ends) * per_day
		rows.append(
			{
				"user": user,
				"full_name": frappe.db.get_value("User", user, "full_name"),
				"capacity": capacity,
				"planned": round(one["hours"], 1),
				"free": round(capacity - one["hours"], 1),
				"load": load(one["hours"], capacity),
				"tasks": one["tasks"],
				"late": one["late"],
				"unestimated": one["unestimated"],
			}
		)
	rows.sort(key=lambda row: -(row["load"] or 0))
	return columns(), rows


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
		{"fieldname": "capacity", "label": _("Capacity (Hours)"), "fieldtype": "Float", "precision": 1, "width": 150},
		{"fieldname": "planned", "label": _("Planned (Hours)"), "fieldtype": "Float", "precision": 1, "width": 150},
		{"fieldname": "free", "label": _("Free (Hours)"), "fieldtype": "Float", "precision": 1, "width": 130},
		{"fieldname": "load", "label": _("Load (%)"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "tasks", "label": _("Tasks"), "fieldtype": "Int", "width": 80},
		{"fieldname": "late", "label": _("Late"), "fieldtype": "Int", "width": 80},
		{"fieldname": "unestimated", "label": _("Not Estimated"), "fieldtype": "Int", "width": 120},
	]
