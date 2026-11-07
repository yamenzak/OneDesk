"""Non Conformance and Quality Action take a company (custom/): each one
made before belongs to the workspace's default company."""

import frappe
from frappe.modules.utils import sync_customizations


def execute():
	sync_customizations("onedesk")
	company = frappe.defaults.get_global_default("company")
	if not company:
		return
	for doctype in ("Non Conformance", "Quality Action"):
		frappe.db.sql(f"update `tab{doctype}` set company = %s where ifnull(company, '') = ''", company)
