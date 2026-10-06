"""A benefit application and a benefit claim work out their own limits."""

import frappe
from frappe.utils import flt


def application(doc, method=None) -> None:
	"""Fill the yearly benefit pot, and add the rows up."""
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
