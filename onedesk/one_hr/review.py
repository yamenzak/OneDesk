"""What happens to a check-in nobody could be sure about."""

import frappe
from frappe import _
from frappe.utils import now_datetime

REVIEWERS = ("HR User", "HR Manager")


@frappe.whitelist(methods=["POST"])
def accept(attempt: str, note: str | None = None) -> dict:
	"""The check-in stands. Nothing about the day changes."""
	return _settle(attempt, "Accepted", note)


@frappe.whitelist(methods=["POST"])
def reject(attempt: str, note: str | None = None) -> dict:
	"""The check-in stops counting, and says so on the log itself."""
	settled = _settle(attempt, "Rejected", note)
	checkin = frappe.db.get_value("Clock Attempt", attempt, "checkin")
	if checkin:
		frappe.db.set_value("Employee Checkin", checkin, "skip_auto_attendance", 1)
	settled["checkin"] = checkin
	from onedesk.one_hr import tell

	tell.checkin_rejected(frappe.db.get_value("Clock Attempt", attempt, "employee"), checkin, note)
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
