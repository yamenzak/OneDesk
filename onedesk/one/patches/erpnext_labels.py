"""OneInventory, OneProject and OneTask call a thing what ERPNext calls it,
the name Ctrl+K finds (docs/WORDING.md, On a Screen). The labels they had
renamed are taken off; a property setter is not removed by its custom file
leaving it, so this removes it."""

import frappe

RENAMED = (
	("Asset", "value_after_depreciation"),
	("BOM", "with_operations"),
	("BOM Operation", "time_in_mins"),
	("Material Request", "transaction_date"),
	("Project", "actual_end_date"),
	("Project", "actual_start_date"),
	("Project", "actual_time"),
	("Project", "cost_center"),
	("Project", "daily_time_to_send"),
	("Project", "day_to_send"),
	("Project", "estimated_costing"),
	("Project", "expected_end_date"),
	("Project", "expected_start_date"),
	("Project", "first_email"),
	("Project", "frequency"),
	("Project", "gross_margin"),
	("Project", "per_gross_margin"),
	("Project", "percent_complete"),
	("Project", "second_email"),
	("Project", "section_break_18"),
	("Project", "total_billable_amount"),
	("Project", "total_billed_amount"),
	("Project", "total_consumed_material_cost"),
	("Project", "total_costing_amount"),
	("Project", "total_expense_claim"),
	("Project", "total_purchase_cost"),
	("Project", "total_sales_amount"),
	("Project", "users"),
	("Project", "users_section"),
	("Project", "weekly_time_to_send"),
	("Projects Settings", "fetch_timesheet_in_sales_invoice"),
	("Projects Settings", "ignore_employee_time_overlap"),
	("Projects Settings", "ignore_user_time_overlap"),
	("Purchase Order", "per_billed"),
	("Purchase Order", "per_received"),
	("Stock Entry", "from_warehouse"),
	("Stock Entry", "to_warehouse"),
	("Stock Reconciliation Item", "current_qty"),
	("Stock Reconciliation Item", "qty"),
	("Stock Reconciliation Item", "quantity_difference"),
	("Task", "exp_end_date"),
	("Timesheet", "billing_details"),
	("Timesheet", "total_billable_hours"),
	("Timesheet", "total_hours"),
	("Work Order", "expected_delivery_date"),
	("Work Order", "produced_qty"),
)


def execute():
	for doctype, field in RENAMED:
		frappe.db.delete("Property Setter", {"doc_type": doctype, "field_name": field, "property": "label"})
		frappe.clear_cache(doctype=doctype)
