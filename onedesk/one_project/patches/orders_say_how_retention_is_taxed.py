"""Orders made before each said how its retention is taxed: as their
invoices already hold it, in Retention lines (When Released) or in payment
terms (With the Invoice), and an order not yet invoiced as Projects Settings
says."""

import frappe
from frappe.utils import flt

from onedesk.one_project.retention import HELD, WHEN_RELEASED, WITH_INVOICE, default_tax


def execute():
	for order_type, invoice_type, link in (
		("Sales Order", "Sales Invoice", "sales_order"),
		("Purchase Order", "Purchase Invoice", "purchase_order"),
	):
		for name in frappe.get_all(
			order_type, filters={"one_retention": [">", 0], "one_retention_tax": ["in", ("", None)]}, pluck="name"
		):
			invoices = frappe.get_all(f"{invoice_type} Item", filters={link: name, "docstatus": 1}, pluck="parent", distinct=True)
			said = default_tax()
			if invoices and frappe.db.exists(f"{invoice_type} Item", {"parent": ["in", invoices], "one_held": ["is", "set"]}):
				said = WHEN_RELEASED
			elif invoices and frappe.db.exists(
				"Payment Schedule", {"parent": ["in", invoices], "parenttype": invoice_type, "payment_term": ["in", HELD]}
			):
				said = WITH_INVOICE
			if flt(frappe.db.get_value(order_type, name, "one_retention")):
				frappe.db.set_value(order_type, name, "one_retention_tax", said, update_modified=False)
