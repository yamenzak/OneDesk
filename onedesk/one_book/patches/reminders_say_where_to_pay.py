"""Every payment reminder made before it named the account to pay into, given
the company's (one_book/paper.py), so it prints the bank."""

import frappe

from onedesk.one_book import paper


def execute():
	for one in frappe.get_all("Dunning", filters={"one_pay_into": ["is", "not set"]}, fields=["name", "company"]):
		doc = frappe._dict(one_pay_into=None, company=one.company)
		paper.pay_into(doc)
		if doc.one_pay_into:
			frappe.db.set_value("Dunning", one.name, "one_pay_into", doc.one_pay_into, update_modified=False)
