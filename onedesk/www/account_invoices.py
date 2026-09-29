"""A One account's invoices, across every workspace it holds
(docs/ONE-ACCOUNT.md, stage 4), at /account/invoices. Admin site only.

Each workspace is its own Stripe customer, so its card is its own too: Update
card is offered per workspace, and opens Stripe's billing portal for it.
"""

import frappe

from onedesk.one_admin import accounts, site

no_cache = 1


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/account/invoices"
		raise frappe.Redirect

	context.no_cache = 1
	context.me = frappe.session.user
	told = accounts.invoices(frappe.session.user)
	context.invoices = told["invoices"]
	context.missed = told["missed"]
	context.cards = [one for one in accounts.workspaces(frappe.session.user) if one.get("stripe_customer")]
	return context
