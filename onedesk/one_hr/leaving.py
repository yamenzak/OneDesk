"""The last day, and what stops on it."""

import frappe
from frappe.utils import add_days, getdate, today

from onedesk.one_hr import passkey, tell

STILL_REPORTS = "reports"


def nightly() -> None:
	"""Everybody whose last day has passed and who is still marked Active."""
	for employee in frappe.get_all(
		"Employee",
		filters=[
			["status", "=", "Active"],
			["relieving_date", "is", "set"],
			["relieving_date", "<=", today()],
		],
		pluck="name",
		ignore_permissions=True,
	):
		close(employee)


def on_employee_update(doc, method=None) -> None:
	"""A last day typed today, or typed earlier and only now saved."""
	if doc.status != "Active" or not doc.relieving_date:
		return
	if getdate(doc.relieving_date) > getdate(today()):
		return
	close(doc.name)


def notice_ends_on(doc, method=None) -> None:
	"""When the contract says the notice runs out: resignation plus the days.

	Worked out rather than typed, and kept apart from the relieving date on
	purpose. This one is what the contract says; the relieving date is the day
	they actually stop. The two differing is the useful part — notice waived,
	paid in lieu, or extended — and a single field cannot show it.
	"""
	if not doc.meta.has_field("one_notice_ends_on"):
		return
	if not doc.resignation_letter_date or not doc.notice_number_of_days:
		doc.one_notice_ends_on = None
		return
	doc.one_notice_ends_on = add_days(
		getdate(doc.resignation_letter_date), int(doc.notice_number_of_days)
	)


def close(employee: str) -> dict:
	"""Mark them Left, and take away what somebody who has left should not have.

	The passkey and the assignments go first: if the status cannot be set —
	because people still report to them — the door should still be shut while
	HR sorts the reporting line out.
	"""
	blocked = passkey.block(employee)
	ended = end_shifts(employee)
	left = set_left(employee)
	return {"passkeys": blocked, "shifts": ended, "status": left}


def set_left(employee: str) -> bool:
	"""Through a real save, so erpnext's own checks run.

	`db_set` would be one line and would skip `validate_status`, which is the
	check that stops a manager being marked Left while their team still points
	at them. When it refuses, HR is told rather than the job failing quietly.
	"""
	doc = frappe.get_doc("Employee", employee)
	if doc.status != "Active":
		return False

	doc.status = "Left"
	try:
		doc.save(ignore_permissions=True)
	except frappe.ValidationError as refused:
		frappe.db.rollback()
		tell.could_not_mark_left(employee, str(refused))
		return False
	return True


def end_shifts(employee: str) -> int:
	"""No roster past the last day.

	`end_date` and `status` are both `allow_on_submit` on Shift Assignment, so
	a submitted assignment is amended rather than cancelled — cancelling would
	take the history of who was rostered where with it.
	"""
	last = frappe.db.get_value("Employee", employee, "relieving_date")
	if not last:
		return 0

	touched = 0
	for row in frappe.get_all(
		"Shift Assignment",
		filters={"employee": employee, "docstatus": 1, "status": "Active"},
		fields=["name", "start_date", "end_date"],
		ignore_permissions=True,
	):
		if row.start_date and getdate(row.start_date) > getdate(last):
			frappe.db.set_value("Shift Assignment", row.name, "status", "Inactive")
			touched += 1
		elif not row.end_date or getdate(row.end_date) > getdate(last):
			frappe.db.set_value("Shift Assignment", row.name, "end_date", last)
			touched += 1
	return touched
