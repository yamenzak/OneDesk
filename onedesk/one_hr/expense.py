"""Answering an expense claim, the same way the other three are answered.

Fourth request doctype in OneHR, fourth approval shape. HRMS gives this one an
`approval_status` Select — Draft, Approved, Rejected — that the approver edits
by hand, and then `on_submit` throws

    Approval Status must be 'Approved' or 'Rejected'

if they forgot, which is a rule the toolbar's own Submit button does not carry.
Attendance Request had no way to say no at all, Shift Request had a dropdown,
Leave Application had a dropdown and a throw; all three now have the same two
buttons, a note, and the three fields that say who decided. This is the last of
them.

`approval_status` stays HRMS's verdict and becomes read-only, because the
buttons set it, and a plain Submit reads as a yes rather than throwing. Their
own `validate_for_self_approval` still runs and still refuses: nobody approves
their own claim, whatever they press.
"""

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one_hr import decision

DRAFT = "Draft"
APPROVED = "Approved"
REJECTED = "Rejected"


def before_validate(doc, method=None) -> None:
	"""Every row gets the cost centre the company only has one of.

	`cost_center` is required on each expense row to book the claim, and it is
	filled by their form script — from the claim, which is filled from the
	company. A claim made any other way fails on submit with *"Row 1: Cost
	Center is required in the expenses table"*, which is a better message than
	most of the ones in this audit and still a field nobody typed because there
	is only one answer.
	"""
	if not doc.company:
		return
	if not doc.cost_center:
		doc.cost_center = frappe.get_cached_value("Company", doc.company, "cost_center")
	for row in doc.expenses or []:
		if not row.cost_center:
			row.cost_center = doc.cost_center


def before_submit(doc, method=None) -> None:
	"""Submitting is the approval, so it is signed — and it says which one."""
	if doc.approval_status == DRAFT:
		doc.approval_status = APPROVED
	decision.sign(doc)


@frappe.whitelist(methods=["POST"])
def approve(name: str, note: str | None = None) -> None:
	"""Say yes, which submits, which books the expense and owes the money."""
	_answer(name, APPROVED, note)


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str | None = None) -> None:
	"""Say no, which submits a closed claim and books nothing."""
	_answer(name, REJECTED, note)


@frappe.whitelist()
def about(name: str) -> dict:
	"""What approving this will pay, for the sentence above the form."""
	doc = frappe.get_doc("Expense Claim", name)
	doc.check_permission("read")

	advance = flt(doc.total_advance_amount)
	sanctioned = flt(doc.total_sanctioned_amount)
	return {
		"employee_name": doc.employee_name or doc.employee,
		"claimed": flt(doc.total_claimed_amount),
		"sanctioned": sanctioned,
		# What is actually paid back: an advance already handed over comes off.
		"payable": max(flt(doc.grand_total) - advance, 0),
		"advance": advance,
		"currency": doc.currency,
		"rows": len(doc.expenses or []),
	}


def _answer(name: str, verdict: str, note: str | None) -> None:
	doc = frappe.get_doc("Expense Claim", name)
	decision.may_decide(doc)

	if doc.docstatus != 0:
		frappe.throw(_("Only a claim still waiting can be answered."))

	doc.approval_status = verdict
	decision.sign(doc, note)
	doc.submit()
