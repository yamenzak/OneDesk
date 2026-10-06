"""Rent, retainers and subscriptions: an invoice or bill made again on a
schedule.
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
