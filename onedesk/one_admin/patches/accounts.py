"""An account for everybody who already holds a workspace (accounts.hold), and
sign-in by mailed link switched on, since that is how an account signs in. On
the admin site only; a customer's site has no Tenants."""

import frappe

from onedesk.one_admin import accounts, site


def execute():
	if not site.is_admin():
		return
	for tenant in frappe.get_all(
		"Tenant",
		filters={"account": ["is", "not set"], "is_house": 0, "owner_email": ["is", "set"]},
		fields=["name", "owner_email"],
	):
		accounts.hold(tenant.name, tenant.owner_email)
	frappe.db.set_single_value("System Settings", "login_with_email_link", 1)
