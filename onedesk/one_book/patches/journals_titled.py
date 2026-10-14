"""A journal entry is titled by what it is for (journal.titled). Those made
before were titled by their first account."""

import frappe

from onedesk.one_book import journal


def execute():
	for one in frappe.get_all(
		"Journal Entry", fields=["name", "title", "user_remark", "voucher_type", "pay_to_recd_from"]
	):
		doc = frappe.get_doc("Journal Entry", one.name)
		if not journal.untitled(doc):
			continue
		said = journal.title(one.user_remark, one.voucher_type, journal.referenced(doc))
		if said and said != one.title:
			frappe.db.set_value("Journal Entry", one.name, "title", said, update_modified=False)
