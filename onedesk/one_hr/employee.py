"""What a person's record should answer before anyone clicks anything.

The desk already links thirty doctypes off an Employee, which tells you where
to look and nothing else. This reads the five things somebody opens the record
to find out — where they are today, what leave is left, what is waiting on an
approver, what they are paid under, how long they have been here — and each
answer carries the doctype it came from so the links stay.

Everything here is read through `frappe.get_all` and `frappe.get_doc`, which
apply the reader's own permissions, so the same call answers differently for an
HR manager and for the person themselves. Leave is HRMS's own
`get_leave_details`, because a balance is theirs to calculate and ours to show.
"""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, get_first_day_of_week, getdate, nowdate, strip_html

#: Thirteen weeks of squares: one quarter, which is as far back as anybody looks
#: and as much as sits beside the numbers without wrapping.
WEEKS = 13

#: Attendance's own five statuses, in our words. `late`, `holiday` and `none`
#: are ours — a flag, a list and an absence of any row.
MARKS = {
	"Present": "present",
	"Work From Home": "wfh",
	"Half Day": "half",
	"On Leave": "leave",
	"Absent": "absent",
}

#: What a person is waiting on somebody to approve, and the field that says so.
AWAITING = (
	("Leave Application", "status", "Open"),
	("Expense Claim", "approval_status", "Draft"),
	("Attendance Request", "docstatus", 0),
	("Shift Request", "status", "Draft"),
)


@frappe.whitelist()
def overview(employee: str) -> dict:
	frappe.has_permission("Employee", doc=employee, throw=True)
	doc = frappe.get_doc("Employee", employee)
	return {
		"state": _state(doc),
		"days": _days(doc),
		"tenure": _tenure(doc),
		"today": _today(doc),
		"leave": _leave(doc),
		"awaiting": _awaiting(doc),
		"pay": _pay(doc),
	}


def _state(doc) -> dict:
	"""Where this person is right now, as one word and a colour.

	Read in the order a person would: somebody who has left is not absent, a
	holiday is not a no-show, approved leave outranks an unmarked day, and a
	check-in with no matching out means they are here whatever the day's
	attendance says, because attendance is usually marked after the fact.
	"""
	if doc.status != "Active":
		return {"label": doc.status, "colour": "red" if doc.status == "Left" else "orange"}

	if _is_holiday(doc):
		return {"label": _("Holiday"), "colour": "gray"}

	on_leave = frappe.get_all(
		"Leave Application",
		filters={
			"employee": doc.name,
			"status": "Approved",
			"docstatus": 1,
			"from_date": ["<=", nowdate()],
			"to_date": [">=", nowdate()],
		},
		fields=["name", "leave_type"],
		limit=1,
	)
	if on_leave:
		return {"label": _("On leave"), "colour": "orange", "doc": on_leave[0]["name"]}

	last = frappe.get_all(
		"Employee Checkin",
		filters={"employee": doc.name, "time": [">=", nowdate() + " 00:00:00"]},
		fields=["log_type"],
		order_by="time desc",
		limit=1,
	)
	if last and last[0]["log_type"] != "OUT":
		return {"label": _("On duty"), "colour": "green"}

	marked = frappe.get_all(
		"Attendance",
		filters={"employee": doc.name, "attendance_date": nowdate(), "docstatus": 1},
		fields=["status"],
		limit=1,
	)
	if marked:
		status = marked[0]["status"]
		return {
			"label": _(status),
			"colour": {"Present": "green", "Absent": "red", "On Leave": "orange"}.get(status, "blue"),
		}

	if last:
		return {"label": _("Left for the day"), "colour": "blue"}
	return {"label": _("Not in yet"), "colour": "gray"}


def _tenure(doc) -> dict:
	joined = getdate(doc.date_of_joining) if doc.date_of_joining else None
	return {
		"joined": doc.date_of_joining,
		"days": date_diff(nowdate(), joined) if joined else None,
		"designation": doc.designation,
		"department": doc.department,
		"grade": doc.grade,
		"reports_to": doc.reports_to,
		"status": doc.status,
	}


def _today(doc) -> dict:
	checkin = frappe.get_all(
		"Employee Checkin",
		filters={"employee": doc.name},
		fields=["name", "time", "log_type"],
		order_by="time desc",
		limit=1,
	)
	attendance = frappe.get_all(
		"Attendance",
		filters={"employee": doc.name, "attendance_date": nowdate(), "docstatus": 1},
		fields=["name", "status", "shift"],
		limit=1,
	)
	return {
		"checkin": checkin[0] if checkin else None,
		"attendance": attendance[0] if attendance else None,
		"holiday": _is_holiday(doc),
	}


def _days(doc) -> list[dict]:
	"""A quarter of attendance, one square a day, starting on a week boundary.

	Nothing marked and no holiday list is a site that does not keep attendance,
	and a grid of ninety-odd blank squares says that worse than no grid does.

	A day nobody marked is not absent: attendance is written after the fact, and
	calling every unwritten day a no-show would be a lie about the person rather
	than about the data. Everything Attendance knows about a day rides along —
	the shift, the leave type, the hours, whether they were late — because the
	square is the only place somebody will ever read it.
	"""
	start = get_first_day_of_week(add_days(getdate(), -(WEEKS * 7 - 1)), as_str=False)
	today = getdate()
	marked = {
		row["attendance_date"]: row
		for row in frappe.get_all(
			"Attendance",
			filters={"employee": doc.name, "docstatus": 1, "attendance_date": [">=", start]},
			fields=[
				"name",
				"attendance_date",
				"status",
				"leave_type",
				"shift",
				"working_hours",
				"late_entry",
				"early_exit",
			],
		)
	}
	closed = _holidays(doc, start)
	if not marked and not closed:
		return []

	days, day = [], start
	while day <= today:
		days.append(_day(day, marked.get(day), closed.get(day)))
		day = add_days(day, 1)
	return days


def _day(day, row, closed: str | None) -> dict:
	"""One square. `late` is not one of Attendance's five statuses — it is two
	flags on a day that is otherwise present, and it is the thing a manager
	scans a quarter looking for."""
	if row:
		mark = MARKS.get(row["status"], "none")
		if mark == "present" and (row["late_entry"] or row["early_exit"]):
			mark = "late"
		return {
			"date": str(day),
			"mark": mark,
			"doc": row["name"],
			"status": row["status"],
			"leave_type": row["leave_type"],
			"shift": row["shift"],
			"hours": row["working_hours"],
			"late": bool(row["late_entry"]),
			"early": bool(row["early_exit"]),
		}
	if closed is not None:
		return {"date": str(day), "mark": "holiday", "holiday": closed}
	return {"date": str(day), "mark": "none"}


def _holidays(doc, start) -> dict:
	"""Whose list this is is ERPNext's question — the employee's, or the
	company's — and a weekly off is a row on it like any other holiday."""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	name = get_holiday_list_for_employee(doc.name, raise_exception=False)
	if not name:
		return {}
	return {
		row["holiday_date"]: (
			_("Weekly off")
			if row["weekly_off"]
			else (strip_html(row["description"] or "").strip() or _("Holiday"))
		)
		for row in frappe.get_all(
			"Holiday",
			filters={"parent": name, "holiday_date": [">=", start]},
			fields=["holiday_date", "description", "weekly_off"],
		)
	}


def _is_holiday(doc) -> bool:
	return getdate() in _holidays(doc, getdate())


def _leave(doc) -> list[dict]:
	"""Every type this person holds an allocation for, as HRMS counts it."""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	try:
		details = get_leave_details(doc.name, nowdate())
	except frappe.PermissionError:
		return []

	rows = []
	for leave_type, counts in (details.get("leave_allocation") or {}).items():
		rows.append(
			{
				"type": leave_type,
				"allocated": counts.get("total_leaves"),
				"taken": counts.get("leaves_taken"),
				"left": counts.get("remaining_leaves"),
				"expiring": counts.get("expired_leaves"),
			}
		)
	return sorted(rows, key=lambda row: row["type"])


def _awaiting(doc) -> list[dict]:
	found = []
	for doctype, field, value in AWAITING:
		if not frappe.has_permission(doctype):
			continue
		count = frappe.db.count(doctype, {"employee": doc.name, field: value})
		if count:
			found.append({"doctype": doctype, "count": count})
	return found


def _pay(doc) -> dict | None:
	if not frappe.has_permission("Salary Structure Assignment"):
		return None
	rows = frappe.get_all(
		"Salary Structure Assignment",
		filters={"employee": doc.name, "docstatus": 1},
		fields=["name", "salary_structure", "base", "variable", "from_date"],
		order_by="from_date desc",
		limit=1,
	)
	if not rows:
		return None
	row = rows[0]
	row["currency"] = frappe.db.get_value("Salary Structure", row["salary_structure"], "currency")
	row["next_payday"] = _next_payday(doc)
	return row


def _next_payday(doc) -> str | None:
	"""The end of the period the last submitted slip covers, plus one."""
	last = frappe.get_all(
		"Salary Slip",
		filters={"employee": doc.name, "docstatus": 1},
		fields=["end_date"],
		order_by="end_date desc",
		limit=1,
	)
	return add_days(last[0]["end_date"], 1) if last else None
