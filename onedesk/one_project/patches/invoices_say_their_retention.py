"""Invoices made before their totals said their retention: what each held
back and what it asked now, from its payment terms, or the work it billed and
what it held, from its Retention lines."""

import frappe
from frappe.utils import flt

from onedesk.one_project.retention import HELD


def execute():
	for name in frappe.get_all(
		"Payment Schedule", filters={"parenttype": "Sales Invoice", "payment_term": ["in", HELD]}, pluck="parent", distinct=True
	):
		rows = frappe.get_all("Payment Schedule", filters={"parent": name, "parenttype": "Sales Invoice"}, fields=["payment_term", "payment_amount"])
		held = sum(flt(one.payment_amount) for one in rows if one.payment_term in HELD)
		now = sum(flt(one.payment_amount) for one in rows if one.payment_term not in HELD)
		frappe.db.set_value("Sales Invoice", name, {"one_retention_held": held, "one_due_now": now}, update_modified=False)
	for name in frappe.get_all("Sales Invoice Item", filters={"one_held": ["is", "set"]}, pluck="parent", distinct=True):
		rows = frappe.get_all("Sales Invoice Item", filters={"parent": name}, fields=["one_held", "net_amount"])
		frappe.db.set_value(
			"Sales Invoice",
			name,
			{
				"one_work_billed": sum(flt(one.net_amount) for one in rows if not one.one_held),
				"one_retention_held": -sum(flt(one.net_amount) for one in rows if one.one_held),
			},
			update_modified=False,
		)
