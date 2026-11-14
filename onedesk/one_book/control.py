"""OneBook's Payment Approval settings (public/js/one_book/book_control.js):
when a payment waits for a second person (unusual.py), each the reader's
default company's own field on Company (custom/company.json), in its
currency."""

import frappe
from frappe import _
from frappe.utils import cint, flt

from onedesk.one.company import company_currency, reader_company
from onedesk.one_book.unusual import FIELDS


def _company() -> str:
	company = reader_company()
	if not company:
		frappe.throw(_("Add a company first."))
	return company


@frappe.whitelist()
def approval() -> dict:
	"""The company's three, and whether the reader may change them."""
	company = _company()
	frappe.has_permission("Company", "read", doc=company, throw=True)
	return {
		"company": company,
		"currency": company_currency(company),
		"may": bool(frappe.has_permission("Company", "write", doc=company)),
		**frappe.db.get_value("Company", company, FIELDS, as_dict=True),
	}


@frappe.whitelist(methods=["POST"])
def save_approval(
	one_approve_above: float | None = None,
	one_approve_first_payment: int | None = None,
	one_approve_bank_days: int | None = None,
) -> dict:
	"""The three saved on the company, as its own form would save them."""
	company = frappe.get_doc("Company", _company())
	company.check_permission("write")
	company.update(
		{
			"one_approve_above": flt(one_approve_above),
			"one_approve_first_payment": cint(one_approve_first_payment),
			"one_approve_bank_days": cint(one_approve_bank_days),
		}
	)
	company.save()
	return approval()
