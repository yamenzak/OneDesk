"""A One account's own page (docs/ONE-ACCOUNT.md), on the admin site only.

Where an account lands after signing in (accounts.home_page): who is signed
in, the workspaces the account holds with where each stands, Pay for one that
owes (Stripe's portal), Open for one that runs, and starting another.
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
	context.tab = "workspaces"
	context.me = frappe.session.user
	context.held = accounts.workspaces(frappe.session.user)
	return context
