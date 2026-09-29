"""A One account's own name and address (docs/ONE-ACCOUNT.md, stage 5), at
/account/profile. Admin site only.

A new address is not taken on trust: it is mailed a link, and the account
moves to it only when that link is followed (accounts.ask_email_change).
"""

import frappe

from onedesk.one_admin import site

no_cache = 1


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/account/profile"
		raise frappe.Redirect

	context.no_cache = 1
	context.tab = "profile"
	context.me = frappe.db.get_value(
		"User", frappe.session.user, ["name", "first_name", "last_name"], as_dict=True
	)
	context.changed = frappe.form_dict.get("changed") == "1"
	return context
