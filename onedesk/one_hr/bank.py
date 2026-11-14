"""An employee's changed bank details wait for a second person
(one/second.py, one_book/details.py).

An Employee's Bank Name, Bank A/C No. or IBAN changing from what it was
asks an HR Manager other than whoever changed it; until one approves,
payroll's bank entry and every payment to the employee are refused
(one_book/unusual.py). The employee is told on their bell, so a change they
did not ask for is noticed. Filling them in the first time asks nothing."""

import frappe

WATCHED = ("bank_name", "bank_ac_no", "iban")

ROLE = "HR Manager"


def changed(doc, method=None) -> None:
	"""Employee on_update."""
	from onedesk.one_book import details

	before = doc.get_doc_before_save()
	if not before or details.skipped():
		return
	said = details.changes(before.as_dict(), doc.as_dict(), WATCHED, details.labels(doc.doctype, WATCHED))
	if said:
		details.asked("Employee", doc.name, said, reference=(doc.doctype, doc.name), role=ROLE)


def tell(employee: str) -> None:
	"""The employee, on their bell, while they can sign in."""
	user = frappe.db.get_value("Employee", employee, "user_id")
	if not user or not frappe.db.get_value("User", user, "enabled") or user == frappe.session.user:
		return
	from onedesk.one_hr import tell as told

	told.bank_details_changed(user, employee)
