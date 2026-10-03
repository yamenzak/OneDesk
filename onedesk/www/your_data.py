"""Your Data: a copy of what a workspace holds about you, or that deleted.
See one/privacy_public.py and one/privacy.py.

On every workspace's own site. A guest (a customer's contact, a supplier, a
lead or an applicant with no account) gives their address and is mailed a
link. A portal reader signed in asks as a user does, in the portal's shell,
under Account: the same state and calls as You > Profile > Your Data on the
desk. Someone with a desk is pointed to their profile.
"""

import frappe

no_cache = 1
sitemap = 0


def get_context(context):
	from onedesk.one import privacy
	from onedesk.one.portal import one_portal_tabs

	context.no_cache = 1
	context.workspace = frappe.db.get_single_value("Workspace Account", "workspace_name") or frappe.local.site
	context.signed_in = frappe.session.user != "Guest"
	context.title = frappe._("Your Data")
	context.one_shell = bool(context.signed_in and one_portal_tabs())
	if context.one_shell:
		context.full_width = True
		context.show_sidebar = False
		context.privacy = privacy.state()
	return context
