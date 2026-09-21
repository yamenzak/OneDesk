"""The last day, and what stops on it.

Setting a Relieving Date is what HR does when somebody leaves, and on its own
it does almost nothing: attendance stops counting past it, `Exit Interview`
refuses without it, and the shift assignment tool filters on it. It does not
set the status, so the login keeps working, the passkey keeps clocking in, and
the roster keeps listing them — and the first thing that objects is payroll,
weeks later, with "Employee {0} relieved on {1} must be set as 'Left'".

So the date does the obvious things here. The status is the lever the framework
already wired: erpnext's `update_user_status` disables the User the moment an
employee stops being Active, so setting the status is also what takes the login
away. The passkey and the shift assignments are ours.

It runs twice — when the record is saved, and nightly for a date set in
advance that has since arrived — because a last day is usually typed before it
happens.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from onedesk.one_hr import passkey

#: Why the status was not set, when erpnext refuses. It refuses for one reason:
#: somebody still reports to them, and marking them Left would leave those
#: people reporting to a record nobody looks at.
STILL_REPORTS = "reports"


def nightly() -> None:
	"""Everybody whose last day has passed and who is still marked Active."""
	for employee in frappe.get_all(
		"Employee",
		# A list rather than a dict: two conditions on one fieldname, and the
		# second key would quietly replace the first.
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
		_tell(employee, str(refused))
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


def _tell(employee: str, why: str) -> None:
	name = frappe.db.get_value("Employee", employee, "employee_name") or employee
	for user in frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["HR User", "HR Manager"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	):
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Employee",
				"document_name": employee,
				"subject": _("{0} could not be marked Left").format(name),
				"email_content": _(
					"Their passkey and shift assignments have been ended, but the status "
					"is still Active:\n\n{0}"
				).format(frappe.utils.strip_html(why)),
			}
		).insert(ignore_permissions=True)
