"""Answering a leave application, the same way the other two are answered.

Three doctypes in OneHR are asked for and then answered by a person, and until
now each had its own shape. Attendance Request had no way to say no at all;
Shift Request had a Status dropdown; this one has a Status dropdown too, and
`on_submit` throws "Only Leave Applications with status 'Approved' and
'Rejected' can be submitted" — a rule the toolbar's own Submit button does not
carry. Three shapes for one question is two too many.

So it gets what the other two got: Approve and Reject, a note, and the three
fields that say who decided and when. HRMS's `status` stays the verdict and
becomes read-only, because the buttons set it, and a plain Submit reads as a yes
rather than throwing.

The headline is the other half. HRMS stacks two — frappe's "Submit this document
to confirm" and its own "Submit this Leave Application to confirm." — and
neither says what approving does. The one here says how many days of what, for
whom, and what it leaves them with, because the table above it does not: it
shows Available Leaves 21 beside Leaves Pending Approval 3, and the 3 is the
application you are looking at.
"""

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one_hr import decision

OPEN = "Open"
APPROVED = "Approved"
REJECTED = "Rejected"


def before_submit(doc, method=None) -> None:
	"""Submitting is the approval, so it is signed — and it says which one."""
	if doc.status == OPEN:
		doc.status = APPROVED
	decision.sign(doc)


@frappe.whitelist(methods=["POST"])
def approve(name: str, note: str | None = None) -> None:
	"""Say yes, which submits, which spends the days and marks the attendance."""
	_answer(name, APPROVED, note)


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str | None = None) -> None:
	"""Say no, which submits a closed application and spends nothing."""
	_answer(name, REJECTED, note)


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


def _answer(name: str, verdict: str, note) -> None:
	doc = frappe.get_doc("Leave Application", name)
	decision.may_decide(doc)
	if doc.docstatus != 0:
		frappe.throw(_("Only an application still waiting can be answered."))

	doc.status = verdict
	doc.one_note = note or ""
	doc.submit()
