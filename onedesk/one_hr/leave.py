"""Answering a leave application, the same way the other two are answered."""

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one_hr import decision

OPEN = "Open"
APPROVED = "Approved"
REJECTED = "Rejected"

PAID_AS = "Leave Encashment"


def encashable() -> None:
	"""Give every encashable leave type something to pay an encashed day with.

	Only a leave type that has none is touched: a workspace that chose its own component keeps it. If HRMS's standard
	component is not on the site, nothing happens and the throw stands — which is
	the honest answer, because there is nothing to point at.
	"""
	if not frappe.db.exists("Salary Component", PAID_AS):
		return
	for leave_type in frappe.get_all(
		"Leave Type",
		filters={"allow_encashment": 1, "earning_component": ("in", (None, ""))},
		pluck="name",
	):
		frappe.db.set_value("Leave Type", leave_type, "earning_component", PAID_AS)


def before_submit(doc, method=None) -> None:
	"""Submitting is the approval, so it is signed — and it says which one."""
	if doc.status == OPEN:
		doc.status = APPROVED
	decision.sign(doc)


@frappe.whitelist(methods=["POST"])
def approve(name: str, note: str | None = None) -> None:
	"""Say yes, which submits, which spends the days and marks the attendance."""
	decision.answer("Leave Application", name, "status", APPROVED, note, _("Only an application still waiting can be answered."))


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str | None = None) -> None:
	"""Say no, which submits a closed application and spends nothing."""
	decision.answer("Leave Application", name, "status", REJECTED, note, _("Only an application still waiting can be answered."))


@frappe.whitelist()
def about(name: str) -> dict:
	"""What approving this will do, for the sentence above the form."""
	doc = frappe.get_doc("Leave Application", name)
	doc.check_permission("read")

	days = flt(doc.total_leave_days)
	before = _balance(doc)
	return {
		"employee_name": doc.employee_name or doc.employee,
		"leave_type": doc.leave_type,
		"days": days,
		"from_date": str(doc.from_date or ""),
		"to_date": str(doc.to_date or ""),
		"before": before,
		"after": max(before - days, 0),
	}


def _balance(doc) -> float:
	"""What they have left, worked out rather than read off the record.

	`leave_balance` is filled by HRMS's own form script when the type or the
	dates change, so an application created any other way carries nought while
	the allocation above it says twenty-one. `get_leave_balance_on` is the
	function that script calls, so the sentence and the table agree.
	"""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	if not (doc.employee and doc.leave_type and doc.from_date):
		return 0.0
	try:
		return flt(get_leave_balance_on(doc.employee, doc.leave_type, doc.from_date))
	except Exception:
		frappe.clear_last_message()
		return flt(doc.leave_balance)
