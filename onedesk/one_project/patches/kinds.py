"""Every project made before kinds existed is given the kind its records say:
Fixed Price with a sales order, Time and Materials with billable time or a
customer, Internal otherwise (kinds.guess)."""

import frappe

from onedesk.one_project.kinds import guess


def execute():
	if not frappe.db.has_column("Project", "one_kind"):
		return
	ordered = set(
		frappe.get_all("Sales Order", filters={"docstatus": 1, "project": ["is", "set"]}, pluck="project")
	)
	billable = set(
		frappe.get_all(
			"Timesheet Detail", filters={"is_billable": 1, "project": ["is", "set"]}, pluck="project"
		)
	)
	for row in frappe.get_all(
		"Project", filters={"one_kind": ["in", ("", None)]}, fields=["name", "sales_order", "customer"]
	):
		kind = guess(bool(row.sales_order) or row.name in ordered, row.name in billable, row.customer)
		frappe.db.set_value("Project", row.name, "one_kind", kind, update_modified=False)
