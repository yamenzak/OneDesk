"""Where somebody is, right now."""

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, nowdate, time_diff_in_seconds

STATES = ("leave", "holiday", "in", "out", "absent", "unknown")

GRACE = 10 * 60


#: Taken from the retired OneApp's `oneapp/onehr/presence.py`, ours and under
#: the same licence. The reasoning has not changed; only the app it sits
NEEDED = ("Employee Checkin", "Attendance", "Leave Application")


def installed() -> bool:
	return all(frappe.db.exists("DocType", one) for one in NEEDED)


@frappe.whitelist()
def of(employee: str) -> dict:
	"""One person's state, now.

	Permission is Frappe's: reading an Employee is what entitles you to know
	whether they are in, and every query below goes through `get_all` as the
	caller. Somebody who cannot see the record gets `unknown` rather than a
	refusal — the page has already refused them the record itself, and this is
	drawn beside a name they can see or not at all.
	"""
	if not employee or not installed():
		return _unknown()

	if not frappe.has_permission("Employee", "read", doc=employee):
		return _unknown()

	today = getdate()

	leave = _on_leave(employee, today)
	if leave:
		return leave

	holiday = _on_holiday(employee, today)
	if holiday:
		return holiday

	checked = _checked_in(employee, today)
	if checked:
		return checked

	marked = _marked(employee, today)
	if marked:
		return marked

	return _unknown()


@frappe.whitelist()
def in_now() -> int:
	"""How many people are checked in this minute. The dashboard's one live number.

	`of()` answers for one person by ranking four doctypes; this only needs the
	last log of the day per employee, so it reads that and counts the INs. A
	person on leave who badged in is counted here and shows as on leave there,
	which is the disagreement `of()` exists to rank rather than an error.
	"""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"time": [">=", f"{nowdate()} 00:00:00"]},
		fields=["employee", "log_type"],
		order_by="employee asc, time asc",
		ignore_permissions=True,
	)
	last: dict[str, str] = {}
	for row in rows:
		last[row.employee] = row.log_type or "IN"
	return sum(1 for log_type in last.values() if log_type == "IN")


def _unknown() -> dict:
	return {"state": "unknown", "label": _("Unknown"), "detail": "", "since": None,
	        "late": False}


def _on_leave(employee: str, today) -> dict | None:
	"""An approved application covering today, by leave type.

	Submitted *and* Approved: HRMS keeps `status` on a submitted document, and a
	rejected one is still `docstatus == 1`. Reading only the docstatus marks
	somebody on leave for a request their manager turned down.
	"""
	found = frappe.get_all(
		"Leave Application",
		filters={
			"employee": employee,
			"status": "Approved",
			"docstatus": 1,
			"from_date": ["<=", today],
			"to_date": [">=", today],
		},
		fields=["leave_type", "to_date", "half_day", "half_day_date"],
		limit=1,
	)
	if not found:
		return None

	one = found[0]
	half = one.get("half_day") and getdate(one.get("half_day_date")) == today
	return {
		"state": "leave",
		"label": _("Half day") if half else _("On leave"),
		"detail": one.get("leave_type") or "",
		"since": None,
		"until": str(one.get("to_date") or ""),
		"late": False,
	}


def _on_holiday(employee: str, today) -> dict | None:
	"""Today in the list this person's own shift or company keeps.

	Their own first: a company that runs two shifts across two countries has two
	holiday lists, and answering from the company's is answering for the wrong
	half of the workforce.
	"""
	found = frappe.db.get_value("Employee", employee, ["holiday_list", "company"],
	                            as_dict=True) or {}
	holidays = found.get("holiday_list")
	if not holidays:
		holidays = frappe.db.get_value("Company", found.get("company"),
		                               "default_holiday_list")
	if not holidays:
		return None

	on = frappe.db.get_value("Holiday", {"parent": holidays, "holiday_date": today},
	                         "description")
	if on is None:
		return None
	return {"state": "holiday", "label": _("Holiday"), "detail": on or "",
	        "since": None, "late": False}


def _checked_in(employee: str, today) -> dict | None:
	"""The last log today, and which way it pointed.

	`time` descending rather than `creation`: a device that uploads a batch at
	noon writes the morning's IN after the morning's OUT, and reading the newest
	*row* would have somebody leaving before they arrived.
	"""
	found = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": ["between", [f"{today} 00:00:00",
		                                                    f"{today} 23:59:59"]]},
		fields=["log_type", "time", "shift", "shift_start"],
		order_by="time desc",
		limit=1,
	)
	if not found:
		return None

	one = found[0]
	at = get_datetime(one["time"])
	if (one.get("log_type") or "IN") == "OUT":
		return {"state": "out", "label": _("Checked out"), "detail": "",
		        "since": str(at), "late": False}

	return {
		"state": "in",
		"label": _("Checked in"),
		"detail": one.get("shift") or "",
		"since": str(at),
		"late": _late(at, one.get("shift_start")),
	}


def _late(at, shift_start) -> bool:
	"""Whether an arrival was after the shift began, by more than the grace.

	`shift_start` is stamped on the check-in by HRMS itself where auto-attendance
	is on, which is the only place the *date* of a shift start exists — Shift
	Type carries a time of day and nothing to anchor it to.
	"""
	if not shift_start:
		return False
	try:
		return time_diff_in_seconds(at, get_datetime(shift_start)) > GRACE
	except Exception:
		return False


def _marked(employee: str, today) -> dict | None:
	"""What the attendance job decided, where nothing above had an answer.

	Last, because it is a verdict written after the day rather than a fact about
	now — and `Present` here with no check-in is somebody whose attendance was
	entered by hand, which is worth saying as "marked present" rather than as
	"in".
	"""
	status = frappe.db.get_value(
		"Attendance",
		{"employee": employee, "attendance_date": today, "docstatus": 1},
		"status",
	)
	if not status:
		return None
	if status == "Absent":
		return {"state": "absent", "label": _("Absent"), "detail": "",
		        "since": None, "late": False}
	if status == "On Leave":
		return {"state": "leave", "label": _("On leave"), "detail": "",
		        "since": None, "late": False}
	return {
		"state": "in",
		"label": _("Marked present") if status == "Present" else _(status),
		"detail": "",
		"since": None,
		"late": False,
	}
