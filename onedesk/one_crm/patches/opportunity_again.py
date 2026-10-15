"""An Opportunity is called an Opportunity again, the name Ctrl+K finds: the
rows that called it a Deal go, and so do the two reports named for deals."""

import frappe


def execute():
	for name in frappe.get_all("Translation", filters={"name": ["like", "one-deal-%"]}, pluck="name"):
		frappe.delete_doc("Translation", name, force=True, ignore_permissions=True)
	for report in ("Deal Forecast", "How Long Deals Take"):
		if frappe.db.exists("Report", report):
			frappe.delete_doc("Report", report, force=True, ignore_permissions=True)
	frappe.clear_cache()
