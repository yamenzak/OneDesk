"""A benefit application and a benefit claim work out their own limits.

Both doctypes carry a read-only ceiling that their `validate` compares against —
`max_benefits` on the application, `max_amount_eligible` on the claim — and both
are filled only by a whitelisted method their *form script* calls. A document
made any other way has `None` there, and validate does not say so: it reaches

    if rounded(total_benefit_amount, 2) > self.max_benefits:

and raises `TypeError: '>' not supported between instances of 'float' and
'NoneType'`, which names neither the field nor what is missing.

It is the same fault as `leave_balance` on a Leave Application, which read
nought on anything not made through the form, and it gets the same answer: the
method upstream already wrote is called before validate when the field is empty,
so the ceiling is there however the document arrived. Nothing is recomputed for
a document that already carries one, because a submitted application's ceiling
is the one it was approved against.
"""

import frappe
from frappe.utils import flt


def application(doc, method=None) -> None:
	"""Fill the yearly benefit pot, and add the rows up.

	`total_amount` and `remaining_benefit` are computed in eleven lines of their
	form script and nowhere on the server, so a submitted application read
	**Total Amount 0.00** and **Remaining Benefits 0.00** above a table holding
	one row of 9,000 against a maximum of 12,000 — three numbers on one screen,
	two of them wrong. Adding up a table is not a decision, so it is done here
	rather than only where somebody happens to be typing.
	"""
	if not (doc.employee and doc.date):
		return
	if not doc.max_benefits:
		doc.set_benefit_components_and_currency()

	doc.total_amount = sum(flt(row.amount) for row in (doc.employee_benefits or []))
	doc.remaining_benefit = flt(doc.max_benefits) - flt(doc.total_amount)


def claim(doc, method=None) -> None:
	"""Fill what is left to claim before their validate compares against it."""
	if doc.max_amount_eligible or not (doc.employee and doc.earning_component):
		return
	doc.get_benefit_details()
