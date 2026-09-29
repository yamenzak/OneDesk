"""A One account's own page (docs/ONE-ACCOUNT.md), on the admin site only.

Where an account lands after signing in (accounts.home_page). For now it says
who is signed in and which workspaces the account holds; stage 2 of the plan
adds each one's standing, what is owed, and starting another.
"""

import frappe

from onedesk.one_admin import accounts, site

no_cache = 1


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/account"
		raise frappe.Redirect

	context.no_cache = 1
	context.me = frappe.session.user
	context.held = [
		{**one, "at": one.primary_domain or one.domain} for one in accounts.workspaces(frappe.session.user)
	]
	return context
