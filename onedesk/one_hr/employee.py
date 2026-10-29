"""What a person's record should answer before anyone clicks anything."""

import frappe
from frappe import _
from frappe.utils import add_days, date_diff, get_first_day_of_week, getdate, nowdate, strip_html

from onedesk.one_hr import policy, rules

WEEKS = 13

MARKS = {
	"Present": "present",
	"Work From Home": "wfh",
	"Half Day": "half",
	"On Leave": "leave",
	"Absent": "absent",
}

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
		"standing": _standing(doc),
		"tenure": _tenure(doc),
		"today": _today(doc),
		"leave": _leave(doc),
		"awaiting": _awaiting(doc),
		"pay": _pay(doc),
		"passkey": _passkey(doc),
		"equipment": _equipment(doc),
	}


@frappe.whitelist()
def passkey_of(employee: str) -> dict | None:
	"""The person's credential for the Reset Passkey button, and nothing
	else about them."""
	frappe.has_permission("Employee", doc=employee, throw=True)
	return _passkey(frappe.get_doc("Employee", employee))


def _equipment(doc) -> int:
	"""How many of the company's assets the person holds. See
	one_inventory/custody.py."""
	if not frappe.has_permission("Asset", "read"):
		return 0
	from onedesk.one_inventory.custody import held

	return len(held(doc.name))


def _standing(doc) -> dict | None:
	"""The number `healing.standings()` worked out last night, and its band."""
	if not frappe.get_meta("Employee").has_field("one_standing"):
		return None
	score = doc.get("one_standing")
	if score in (None, ""):
		return None

	score = int(score)
	refuse = policy.band("refuse_below", rules.REFUSE_BELOW)
	flag = policy.band("flag_below", rules.FLAG_BELOW)
	return {
		"score": score,
		"on": doc.get("one_standing_on"),
		"band": "low" if score < refuse else "watch" if score < flag else "good",
	}


def _passkey(doc) -> dict | None:
	"""Their credential, for the reset button and for nothing else.

	No public key and no credential id: this answers a screen, and a screen has
	no use for either.
	"""
	from onedesk.one_hr import passkey

	held = passkey.held_by(doc.name)
	return {"label": held.label} if held else None


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
		return {"label": _("Checked in"), "colour": "green"}

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
		return {"label": _("Checked out"), "colour": "blue"}
	return {"label": _("Not checked in"), "colour": "gray"}


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
	"""A quarter of attendance, one square a day, starting on a week boundary."""
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

	said = len(frappe.local.message_log)
	try:
		details = get_leave_details(doc.name, nowdate())
	except frappe.PermissionError:
		del frappe.local.message_log[said:]
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


MASTERS = {
	"Leave Policy": {"docstatus": 1},
	"Salary Structure": {"docstatus": 1, "is_active": "Yes"},
	"Shift Schedule": {"docstatus": 1},
}


@frappe.whitelist()
def get_assignable_masters(company: str) -> dict[str, bool]:
	"""HRMS's question, asked only of what the reader may read: a master they
	may not read answers no, where HRMS's own refuses the whole question and
	the record opens on a permission error."""
	return {
		doctype: bool(
			frappe.has_permission(doctype, "read")
			and frappe.get_list(
				doctype,
				filters={**filters, **({"company": company} if doctype == "Salary Structure" else {})},
				limit=1,
				pluck="name",
			)
		)
		for doctype, filters in MASTERS.items()
	}


def dashboard(data):
	"""override_doctype_dashboards, after HRMS's: the record's own quarter
	(heads.quarter) is the attendance, so frappe's second heat map, a year
	of the same days drawn again, is left off."""
	data["heatmap"] = False
	data.pop("heatmap_message", None)
	return data
