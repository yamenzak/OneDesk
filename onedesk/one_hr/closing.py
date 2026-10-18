"""Closing a day nobody closed."""

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime, today

from onedesk.one_hr import policy, tell

GRACE_HOURS = 2


def hourly() -> None:
	if not policy.on("one_close_the_day"):
		return
	for log in _open_past_their_shift():
		_close(log)


def _open_past_their_shift() -> list[frappe._dict]:
	"""Today's last log per employee, where it was an IN and the shift has ended.

	Read from `Employee Checkin` rather than from Attendance, because Attendance
	for today does not exist until the auto-attendance job has run — and it is
	the one that is about to read these pairs.
	"""
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"time": [">=", f"{today()} 00:00:00"]},
		fields=["name", "employee", "log_type", "time", "shift", "shift_end"],
		order_by="employee asc, time asc",
		ignore_permissions=True,
	)
	last: dict[str, frappe._dict] = {}
	for row in rows:
		last[row.employee] = row

	now = now_datetime()
	return [
		row
		for row in last.values()
		if (row.log_type or "IN") == "IN"
		and row.shift_end
		and get_datetime(row.shift_end) <= add_to_date(now, hours=-GRACE_HOURS)
	]


def ending_reason() -> str | None:
	"""What a closed day is filed under, chosen by the flag rather than by name.

	Whichever enabled `Clock Reason` is marked `ends_the_day`. The name used to
	be written here as a string, and that row can be renamed or deleted by any
	HR Manager, which would have left every closed day pointing at a row that
	is not there. No such reason means no reason: `one_auto_closed` is the part
	that matters and it is set either way.
	"""
	return frappe.db.get_value(
		"Clock Reason", {"enabled": 1, "ends_the_day": 1}, "name", order_by="creation asc"
	)


def _close(log) -> None:
	"""One OUT at the shift's end, marked for what it is, and one nudge.

	At the shift's end rather than now: the hours a person is paid for should
	not depend on when a scheduled job happened to run.
	"""
	out = frappe.new_doc("Employee Checkin")
	out.flags.one_gated = True
	out.employee = log.employee
	out.log_type = "OUT"
	out.time = log.shift_end
	out.one_auto_closed = 1
	out.one_reason = ending_reason()
	out.insert(ignore_permissions=True)
	tell.day_closed(log.employee, out.name)
