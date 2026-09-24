"""A mailbox OneAI already reads stops Frappe making a Contact for every
address on every message; OneAI makes them for the people writing."""

import frappe


def execute():
	for account in frappe.get_all("Email Account", filters={"one_intake": 1}, pluck="name"):
		frappe.db.set_value("Email Account", account, "create_contact", 0, update_modified=False)
