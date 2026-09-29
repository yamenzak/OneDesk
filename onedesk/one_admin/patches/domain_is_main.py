"""`Tenant Domain.is_main`, from each workspace's `primary_domain`."""

import frappe


def execute():
	if not frappe.db.has_column("Tenant Domain", "is_main"):
		return
	for tenant, main in frappe.get_all(
		"Tenant", filters={"primary_domain": ["is", "set"]}, fields=["name", "primary_domain"], as_list=True
	):
		frappe.db.set_value(
			"Tenant Domain", {"tenant": tenant, "name": main}, "is_main", 1, update_modified=False
		)
