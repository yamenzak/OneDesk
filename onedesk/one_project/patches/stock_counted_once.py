"""Projects that bought stock into a store had it in their purchase cost as
well as in what was issued to them: their purchase cost is summed again
without it (one_project/materials.py)."""

import frappe

from onedesk.one_project import materials


def execute():
	for name in frappe.get_all("Project", pluck="name"):
		if not materials.into_store([name]):
			continue
		project = frappe.get_doc("Project", name)
		project.update_purchase_costing()
		project.db_set("total_purchase_cost", project.total_purchase_cost, update_modified=False)
