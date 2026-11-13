"""Asking to work a different shift, and the person who answers."""

import frappe
from frappe import _
from frappe.utils import format_time

from onedesk.one_hr import decision

DRAFT = "Draft"
APPROVED = "Approved"
REJECTED = "Rejected"


def before_validate(doc, method=None) -> None:
	decision.kept(doc)
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
	decision.answer("Shift Request", name, "status", APPROVED, note, _("Only a request still waiting can be answered."))


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str | None = None) -> None:
	"""Say no, which submits a closed request and assigns nobody anything."""
	decision.answer("Shift Request", name, "status", REJECTED, note, _("Only a request still waiting can be answered."))


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
	return f"{format_time(str(starts))} – {format_time(str(ends))}"


def _company(doc) -> None:
	"""One workspace is one company, so this is never a question on a form."""
	company = frappe.db.get_value("Employee", doc.employee, "company") if doc.employee else None
	if company:
		doc.company = company
