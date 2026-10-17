"""Every invoice made before its lines carried their VAT, and its account to pay
into, given both (one_book/paper.py), so it prints as a new one does."""

import frappe

from onedesk.one_book import paper


def execute():
	for name in frappe.get_all("Sales Invoice", pluck="name"):
		doc = frappe.get_doc("Sales Invoice", name)
		paper.lines(doc)
		paper.pay_into(doc)
		for row in doc.items:
			row.db_set(
				{"one_vat_rate": row.one_vat_rate, "one_vat_amount": row.one_vat_amount, "one_line_total": row.one_line_total},
				update_modified=False,
			)
		doc.db_set("one_pay_into", doc.one_pay_into, update_modified=False)
