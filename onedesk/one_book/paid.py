"""Recording a payment against an invoice or a bill in one step.

ERPNext's **Create › Payment** opens a Payment Entry form of some thirty
fields, filled from the invoice, for somebody to read, save and submit; the
common case — the customer paid all or part of this invoice into our bank —
needs four of them. **Record Payment** on a submitted invoice or bill asks for
those four (how much, on what day, into or out of which account, and the
bank's reference) and submits ERPNext's own Payment Entry, made by its own
`get_payment_entry`. Anything else — a discount, a deduction, another currency,
one payment across several invoices — is still **Create › Payment**.

An invoice left unpaid is also a reminder: **Payment Reminder**
(notification/payment_reminder) mails the customer the invoice a week after it
fell due. It is shipped off, since it writes to customers; the Books Check
turns it on.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

#: What can be settled here, and what its payment is called in a message.
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

