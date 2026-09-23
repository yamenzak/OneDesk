"""Rent, retainers and subscriptions: an invoice or bill made again on a
schedule.

Frappe's **Auto Repeat** copies a document on a schedule, and ERPNext's
invoices were written for it — each has an `auto_repeat` field and an
`on_recurring` method — but neither is switched on for it
(`allow_auto_repeat`), so **⋯ › Repeat** is not offered. OneBook switches it
on (custom/sales_invoice.json, custom/purchase_invoice.json) rather than
using ERPNext's **Subscription**, which needs a plan per item and a price
per plan to say what the invoice already says.

The copy is not right as Auto Repeat makes it, and `repeated` (both
invoices' `on_recurring`, run after ERPNext's own) corrects it:

- **The due date.** Auto Repeat dates every required date field the day it
  runs, and ERPNext's `on_recurring` empties the due date, so a copy with no
  payment terms falls due the day it is made and is late the next. The copy
  keeps the original's days to pay instead.
- **The payment schedule.** Its rows are copied with last time's dates; the
  copy's is made again from its own due date or payment terms.
- **The supplier's bill number.** It is copied, and is the supplier's number
  for last month's bill; with duplicate bill numbers refused (the Books Check
  suggests it) the copy cannot even be saved. The copy has none until this
  month's bill comes, and is dated the day it is made.
"""

from frappe.utils import add_days, date_diff, getdate


def terms(reference, posting_date) -> str | None:
	"""The copy's due date: as many days after its posting as the original's
	was after its own. None when the original had payment terms, which set it
	themselves. Pure over the original's dates."""
	if reference.get("payment_terms_template") or not reference.get("due_date"):
		return None
	days = max(date_diff(reference.get("due_date"), reference.get("posting_date")), 0)
	return add_days(getdate(posting_date), days)


def repeated(doc, method=None, reference_doc=None, auto_repeat_doc=None) -> None:
	"""on_recurring for Sales Invoice and Purchase Invoice."""
	if reference_doc is None:
		return
	doc.set("payment_schedule", [])
	due = terms(reference_doc, doc.posting_date)
	if due:
		doc.due_date = due
	if doc.doctype == "Purchase Invoice":
		doc.bill_no = None
		doc.bill_date = doc.posting_date
