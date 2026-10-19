"""Invoices on a project made before claim numbers get theirs, in the order
they were posted (one_project/claims.py)."""

import frappe


def execute():
	if not frappe.get_meta("Sales Invoice").get_field("one_claim"):
		return
	done: dict = {}
	for row in frappe.get_all(
		"Sales Invoice",
		filters={"project": ["is", "set"], "docstatus": ["!=", 0], "is_return": 0},
		fields=["name", "project", "one_claim"],
		order_by="posting_date asc, creation asc",
	):
		number = row.one_claim or done.get(row.project, 0) + 1
		done[row.project] = max(done.get(row.project, 0), number)
		if not row.one_claim:
			frappe.db.set_value("Sales Invoice", row.name, "one_claim", number, update_modified=False)
