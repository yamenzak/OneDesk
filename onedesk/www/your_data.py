"""Your Data: a copy of what a workspace holds about you, or that deleted,
for somebody who is not a user. See one/privacy_public.py.

On every workspace's own site, for a guest: a customer's contact, a
supplier, a lead or an applicant has no account to ask from. A user is
pointed to their profile, where they need no mailed link.
"""

import frappe

no_cache = 1
sitemap = 0


def get_context(context):
	context.no_cache = 1
	context.workspace = frappe.db.get_single_value("Workspace Account", "workspace_name") or frappe.local.site
	context.signed_in = frappe.session.user != "Guest"
	context.title = frappe._("Your data")
	return context
