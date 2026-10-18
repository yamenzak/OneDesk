"""Recording a payment against an invoice or a bill in one step.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

SETTLED = ("Sales Invoice", "Purchase Invoice")

REMINDER = "Payment Reminder"


def allocate(amount: float, owed: list[float]) -> list[float]:
	"""An amount across what each reference still owes, first to last. Pure."""
	left, out = flt(amount), []
	for one in owed:
		take = min(left, flt(one))
		out.append(take)
		left -= take
	return out


@frappe.whitelist(methods=["POST"])
def settle(doctype: str, name: str, amount: float, account: str, reference: str | None = None, on: str | None = None) -> str:
	"""A submitted Payment Entry for `amount` of the invoice or bill, into or out
	of `account`. The bank's reference defaults to the invoice's number, since
	ERPNext will not submit a bank payment without one."""
	if doctype not in SETTLED:
		frappe.throw(_("Only an invoice or a bill is paid here."))
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	amount, on = flt(amount), getdate(on or nowdate())
	if amount <= 0:
		frappe.throw(_("Enter the amount paid."))
	entry = get_payment_entry(doctype, name, bank_account=account)
	if entry.paid_from_account_currency != entry.paid_to_account_currency:
		frappe.throw(_("This is paid in another currency. Use Create › Payment."))
	owed = [flt(row.outstanding_amount) for row in entry.references]
	if amount > sum(owed) + 0.005:
		frappe.throw(_("{0} is more than the {1} still owed.").format(amount, sum(owed)))
	for row, share in zip(entry.references, allocate(amount, owed)):
		row.allocated_amount = share
	entry.references = [row for row in entry.references if row.allocated_amount]
	entry.paid_amount = entry.received_amount = amount
	entry.posting_date = entry.reference_date = on
	entry.reference_no = (reference or "").strip() or name
	entry.insert()
	entry.submit()
	return entry.name



def titled(doc, method=None) -> None:
	"""A payment to or from somebody is titled by their name, not their ID:
	ERPNext titles it by the party, which for an employee is HR-EMP-00013."""
	if doc.payment_type in ("Receive", "Pay") and doc.party_name and doc.title == doc.party:
		doc.title = doc.party_name
