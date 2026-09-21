"""Asking to work a different shift, and the person who answers.

Three things were wrong with HRMS's screen and all three are the same kind of
thing: the form knows something the person reading it does not.

**The approver picker comes back empty and does not say why.** `Approver` is
mandatory and HRMS filters it to exactly two sources — the employee's own
`shift_request_approver`, and the `shift_request_approver` rows on their
department. An employee with neither gets an empty list, a required field, and
no way to find out what is missing. So the form fills the field itself where
there is one obvious answer, and says what to do where there is none.

**Nothing on the screen said what the shift is.** The whole document is about
moving somebody onto "Evening", and "Evening" is a name. The hours are written
onto the record so the form and the list both read as a sentence.

**Submitting was the approval and refused to say so.** HRMS's `on_submit`
throws unless `status` is already Approved or Rejected, which is a rule the
toolbar button does not know about, and either way nothing recorded who
decided. Approve and Reject set the status, sign the document and submit it —
rejecting closes the request and writes no Shift Assignment, which is HRMS's
own behaviour and the right one.
"""

import frappe
from frappe import _
from frappe.utils import format_timedelta

from onedesk.one_hr import decision

DRAFT = "Draft"
APPROVED = "Approved"
REJECTED = "Rejected"


def before_validate(doc, method=None) -> None:
	_company(doc)
	doc.one_when = hours(doc.shift_type)


def before_submit(doc, method=None) -> None:
	"""Submitting is the approval, so it is signed — and it says which one.

	HRMS refuses a submit while the status is still Draft, without ever putting
	that rule on the screen. Pressing Submit plainly means yes, so that is what
	it does.
	"""
	if doc.status == DRAFT:
		doc.status = APPROVED
	decision.sign(doc)


@frappe.whitelist(methods=["POST"])
def approve(name: str, note: str | None = None) -> None:
	"""Say yes, which submits, which writes the Shift Assignment."""
	_answer(name, APPROVED, note)


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str | None = None) -> None:
	"""Say no, which submits a closed request and assigns nobody anything."""
	_answer(name, REJECTED, note)


@frappe.whitelist()
def approvers(employee: str) -> list[str]:
	"""Everybody HRMS would accept in the Approver field, in its own order.

	Read from the two places `ShiftRequest.validate_approver` reads, rather than
	from HRMS's search query: the search is what the picker offers and this is
	what the save will accept, and where those two disagree it is the second one
	that throws.
	"""
	if not employee:
		return []

	department, own = frappe.db.get_value(
		"Employee", employee, ["department", "shift_request_approver"]
	) or (None, None)

	found = []
	if department:
		found = frappe.get_all(
			"Department Approver",
			filters={"parent": department, "parentfield": "shift_request_approver"},
			pluck="approver",
			ignore_permissions=True,
		)
	if own:
		found.append(own)
	return list(dict.fromkeys(one for one in found if one))


@frappe.whitelist()
def hours(shift_type: str) -> str:
	"""A shift as its two times, or nothing where it has none.

	Written in 24 hours rather than through `format_time`, because this is
	stored on the document and the saver's own time format is not the reader's.
	"""
	if not shift_type:
		return ""
	starts, ends = frappe.db.get_value("Shift Type", shift_type, ["start_time", "end_time"]) or (
		None,
		None,
	)
	if starts is None or ends is None:
		return ""
	return f"{format_timedelta(starts)[:5]} – {format_timedelta(ends)[:5]}"


def _answer(name: str, verdict: str, note) -> None:
	doc = frappe.get_doc("Shift Request", name)
	decision.may_decide(doc)
	if doc.docstatus != 0:
		frappe.throw(_("Only a request still waiting can be answered."))

	doc.status = verdict
	doc.one_note = note or ""
	doc.submit()


def _company(doc) -> None:
	"""One workspace is one company, so this is never a question on a form."""
	company = frappe.db.get_value("Employee", doc.employee, "company") if doc.employee else None
	if company:
		doc.company = company
