"""A plan names its features now (price_list.Plan.features): every workspace
already sold one takes what its plan declares, and ours and one on a plan
the price list no longer declares take what every plan has, so nothing a
workspace could do yesterday is taken away."""

import frappe

from onedesk.one_admin import features, price_list


def execute():
	frappe.reload_doc("one_admin", "doctype", "plan_feature")
	frappe.reload_doc("one_admin", "doctype", "offering")
	frappe.reload_doc("one_admin", "doctype", "tenant")
	for tenant in frappe.get_all("Tenant", fields=["name", "offering"]):
		if not features.held("Tenant", tenant.name):
			features.write("Tenant", tenant.name, price_list.features_of(tenant.offering))
