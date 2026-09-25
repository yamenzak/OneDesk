"""What happens to a check-in nobody could be sure about.

`HR Settings` says a check-in scoring between the two thresholds is "written,
and marked Flagged for review". Written it was; reviewed it was not — there
was no queue, no verdict, and nobody was told. The band in the middle is the
whole reason for having two thresholds rather than one, so it needs an end.

Rejecting does not delete anything. The log stays, the attempt stays, and the
check-in gets `skip_auto_attendance`, which is HRMS's own lever for a log that
should not count towards a day's attendance. What was attempted and what was
decided both remain readable, which is the point of keeping a ledger at all.
"""

import frappe
from frappe import _
from frappe.utils import now_datetime

#: Roles that may settle one. Deliberately not the employee's own: the person
#: a flag is about is not the person who clears it.
REVIEWERS = ("HR User", "HR Manager")


@frappe.whitelist()
def accept(attempt: str, note: str | None = None) -> dict:
	"""The check-in stands. Nothing about the day changes."""
	return _settle(attempt, "Accepted", note)


@frappe.whitelist()
def reject(attempt: str, note: str | None = None) -> dict:
	"""The check-in stops counting, and says so on the log itself."""
	settled = _settle(attempt, "Rejected", note)
	checkin = frappe.db.get_value("Clock Attempt", attempt, "checkin")
	if checkin:
		frappe.db.set_value("Employee Checkin", checkin, "skip_auto_attendance", 1)
	settled["checkin"] = checkin
	return settled


def _settle(attempt: str, verdict: str, note: str | None) -> dict:
	if not frappe.has_permission("Clock Attempt", "write"):
		frappe.throw(_("Only HR can review a check-in."), frappe.PermissionError)

	row = frappe.db.get_value(
		"Clock Attempt", attempt, ["outcome", "verdict", "employee"], as_dict=True
	)
	if not row:
		frappe.throw(_("No such check-in attempt."))
	if row.verdict:
		frappe.throw(_("This attempt was already reviewed."))
	if row.outcome != "Flagged":
		frappe.throw(_("Only a flagged attempt needs reviewing."))

	frappe.db.set_value(
		"Clock Attempt",
		attempt,
		{
			"verdict": verdict,
			"reviewed_by": frappe.session.user,
			"reviewed_on": now_datetime(),
			"note": note,
		},
	)
	return {"attempt": attempt, "verdict": verdict}


def tell(attempt: str, employee: str, signals: list[str]) -> None:
	"""One alert per flag, to everybody who can settle it.

	The reasons go in the notification rather than only on the record, because
	a flag worth raising at all is worth being able to judge from the phone
	that buzzed.
	"""
	from onedesk.one import notify
	from onedesk.one_hr import rules

	name = frappe.db.get_value("Employee", employee, "employee_name") or employee
	told = "\n".join(f"• {_(rules.says(signal))}" for signal in dict.fromkeys(signals))
	notify.notify(
		"Check-in Flagged", _reviewers(), record=("Clock Attempt", attempt), employee=name, reasons=told
	)


def _reviewers() -> list[str]:
	return frappe.get_all(
		"Has Role",
		filters={"role": ["in", list(REVIEWERS)], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
