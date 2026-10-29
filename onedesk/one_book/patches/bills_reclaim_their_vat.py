"""Box 9 of the UAE VAT return reads what each bill claims back. Bills made
before `vat.reclaimed` filled the figure claim nothing; they claim their VAT."""

import frappe

from onedesk.one_book import vat


def execute():
	for company in frappe.get_all("Company", pluck="name"):
		if vat.in_uae(company):
			vat.reclaim(company)
