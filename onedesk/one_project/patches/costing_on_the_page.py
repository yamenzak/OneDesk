"""The project form's Costing tab loses what the page now shows.

The customer's side, the cost side, the forecast, the cost types and the
suppliers were HTML fields drawn on the form. The page's Money and Suppliers
views show them now (one_project/AGENTS.md), so the fields go. The tab keeps
the Budget and the fields ERPNext needs."""

import frappe

GONE = (
	"one_customer_section",
	"one_customer",
	"one_cost_section",
	"one_cost",
	"one_forecast_section",
	"one_forecast",
	"one_suppliers_section",
	"one_suppliers",
	"one_budget_section",
	"one_budget",
)


def execute():
	for fieldname in GONE:
		frappe.delete_doc_if_exists("Custom Field", f"Project-{fieldname}")
	frappe.clear_cache(doctype="Project")
