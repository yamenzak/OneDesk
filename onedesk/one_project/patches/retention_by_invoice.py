"""Retention moved from the order alone to the project, the order and the
invoice: a project takes its contract's retention as its own, and an
invoice already holding retention says its order's (retention.py)."""

import frappe
from frappe.utils import flt


def execute():
	if not frappe.db.has_column("Project", "one_retention"):
		return
	for project in frappe.get_all("Project", filters={"sales_order": ["is", "set"]}, fields=["name", "sales_order"]):
		order = frappe.db.get_value(
			"Sales Order",
			project.sales_order,
			["one_retention", "one_retention_due", "one_retention_handover"],
			as_dict=True,
		)
		if order and flt(order.one_retention):
			frappe.db.set_value("Project", project.name, dict(order), update_modified=False)
	for doctype, link in (("Sales Invoice", "sales_order"), ("Purchase Invoice", "purchase_order")):
		if not frappe.db.has_column(doctype, "one_retention"):
			continue
		held = set(
			frappe.get_all(
				"Payment Schedule",
				filters={"parenttype": doctype, "payment_term": ["in", ("Retention", "Retention at Handover")]},
				pluck="parent",
			)
		)
		order_type = "Sales Order" if doctype == "Sales Invoice" else "Purchase Order"
		for name in held:
			order = frappe.db.get_value(f"{doctype} Item", {"parent": name, link: ["is", "set"]}, link)
			share = frappe.db.get_value(order_type, order, "one_retention") if order else None
			if flt(share):
				frappe.db.set_value(doctype, name, "one_retention", share, update_modified=False)
