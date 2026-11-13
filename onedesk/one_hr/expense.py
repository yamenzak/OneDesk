"""Answering an expense claim, the same way the other three are answered."""

import frappe
from frappe import _
from frappe.utils import flt

from onedesk.one_hr import decision

DRAFT = "Draft"
APPROVED = "Approved"
REJECTED = "Rejected"


def before_validate(doc, method=None) -> None:
	"""Every row gets the cost centre the company only has one of."""
	decision.kept(doc)
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
	decision.answer("Expense Claim", name, "approval_status", APPROVED, note, _("Only a claim still waiting can be answered."))


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str | None = None) -> None:
	"""Say no, which submits a closed claim and books nothing."""
	decision.answer("Expense Claim", name, "approval_status", REJECTED, note, _("Only a claim still waiting can be answered."))


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
		"payable": max(flt(doc.grand_total) - advance, 0),
		"advance": advance,
		"currency": doc.currency,
		"rows": len(doc.expenses or []),
	}
