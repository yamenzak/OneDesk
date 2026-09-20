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
from frappe.utils import add_days, date_diff, getdate, nowdate

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
		"tenure": _tenure(doc),
		"today": _today(doc),
		"leave": _leave(doc),
		"awaiting": _awaiting(doc),
		"pay": _pay(doc),
	}


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


def _is_holiday(doc) -> bool:
	if not doc.holiday_list:
		return False
	return bool(
		frappe.get_all(
			"Holiday",
			filters={"parent": doc.holiday_list, "holiday_date": nowdate()},
			limit=1,
		)
	)


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
