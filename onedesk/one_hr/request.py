"""Asking for a day to count as worked, and the person who answers.

HRMS ships the asking and not the answering. `Attendance Request` is a
submittable document whose submit writes the Attendance rows, and the whole of
its approval is that an Employee has no `submit` grant and HR does — so the
decision happens, but nothing anywhere records that it was a decision, who made
it, or that anybody ever said no. A request turned down is a draft nobody
reopened.

So three things are added and nothing is replaced. Submitting is still what
writes the attendance, and it now also writes down who approved it and when.
Rejecting is a verb: the request stays a draft, carries a `Rejected` decision
that only somebody with the submit grant can set, and cannot be submitted while
it stands. And the reason stops being two hardcoded words.

**The reason is a record now, but HRMS's field is still the one that decides the
status.** `AttendanceRequest.get_attendance_status` reads `self.reason` and
compares it to the literal string "Work From Home"; everything else becomes
Present. Rather than override that method, `before_validate` writes HRMS's own
field from the chosen `Attendance Reason` — so a workspace can offer fifteen
reasons and HRMS keeps marking the days exactly as it always did.
"""

import frappe
from frappe import _

from onedesk.one_hr import decision

#: The two strings HRMS's own Select holds, and the only two its status mapping
#: can tell apart. Every Attendance Reason lands on one of them.
WORK_FROM_HOME = "Work From Home"
ON_DUTY = "On Duty"

APPROVED = "Approved"
REJECTED = "Rejected"


def before_validate(doc, method=None) -> None:
	"""Fill in what the form no longer asks for, before HRMS reads it.

	Before rather than after: HRMS's own `validate` already calls
	`get_attendance_status` to work out which days it would have nothing to
	write, so `reason` has to be right by then or the warnings are about a
	different request.
	"""
	_company(doc)
	_reason(doc)


def before_submit(doc, method=None) -> None:
	"""Submitting is the approval, so it is signed.

	Whoever presses Submit is the approver whether they came through the button
	below or through the form's own toolbar, and a request somebody has already
	turned down does not get submitted by being opened again.
	"""
	if doc.one_decision == REJECTED:
		frappe.throw(
			_("This request was turned down on {0}. Approve it first if that has changed.").format(
				frappe.format(doc.one_decided_on, "Datetime")
			)
		)
	doc.one_decision = APPROVED
	decision.sign(doc)


@frappe.whitelist(methods=["POST"])
def approve(name: str, note: str | None = None) -> None:
	"""Say yes, which submits, which writes the days."""
	doc = frappe.get_doc("Attendance Request", name)
	decision.may_decide(doc)
	doc.one_decision = ""
	doc.one_note = note or ""
	doc.submit()


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str | None = None) -> None:
	"""Say no, which leaves a draft that says who said it.

	Not a cancellation, because there is nothing submitted to cancel, and not a
	deletion, because the request and its answer are the record of the
	conversation. The document stays editable — a person who was turned down for
	the wrong week can fix the week and ask again — and `before_submit` refuses
	to submit it until somebody with the same grant approves instead.
	"""
	doc = frappe.get_doc("Attendance Request", name)
	decision.may_decide(doc)
	if doc.docstatus != 0:
		frappe.throw(_("Only a request still waiting can be turned down."))

	doc.db_set({"one_decision": REJECTED, **decision.signed(note)})
	doc.add_comment("Workflow", _("Turned down.") + (f" {note}" if note else ""))
	doc.notify_update()


def _company(doc) -> None:
	"""The employee's company, never a question on the form.

	It was a mandatory Link showing the one company there is, which is a field
	that can only be got wrong.
	"""
	company = frappe.db.get_value("Employee", doc.employee, "company") if doc.employee else None
	if company:
		doc.company = company


def _reason(doc) -> None:
	"""HRMS's Select, written from the chosen reason."""
	marks_as = (
		frappe.db.get_value("Attendance Reason", doc.one_reason, "marks_as")
		if doc.one_reason
		else None
	)
	if marks_as:
		doc.reason = WORK_FROM_HOME if marks_as == WORK_FROM_HOME else ON_DUTY
	elif not doc.reason:
		doc.reason = ON_DUTY
