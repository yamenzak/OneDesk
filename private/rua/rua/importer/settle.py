"""A Retention Check for each project that billed or was paid, so the
project asks whether its client still holds retention from invoices made
outside the old app (rua/settle.py). A project that already holds
retention in One is not asked."""

import frappe

from rua.settle import CHECK


def run(run_):
	held = set(
		frappe.get_all("Sales Invoice", filters={"docstatus": 1, "one_retention": [">", 0]}, pluck="project")
	)
	asked = set(
		frappe.get_all("Sales Invoice", filters={"docstatus": 1, "project": ["is", "set"]}, pluck="project")
	)
	asked |= set(
		frappe.get_all(
			"Payment Entry",
			filters={"docstatus": 1, "payment_type": "Receive", "project": ["is", "set"]},
			pluck="project",
		)
	)
	for project in sorted(asked - held):
		if frappe.db.exists("Project", project) and not frappe.db.exists(CHECK, project):
			frappe.get_doc({"doctype": CHECK, "project": project, "answer": "To Ask"}).insert(
				ignore_permissions=True
			)
	waiting = frappe.db.count(CHECK, {"answer": "To Ask"})
	if waiting:
		run_.note(
			"To Check", None, None, f"{waiting} projects ask whether retention is still held from before One"
		)
