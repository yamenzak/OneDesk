"""Your Data: a copy of what a workspace holds about you, or that deleted.
See one/privacy_public.py and one/privacy.py.
"""

import frappe

no_cache = 1
sitemap = 0


def get_context(context):
	from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo

	from onedesk.one import privacy
	from onedesk.one.portal import one_portal_tabs

	if frappe.session.user != "Guest" and privacy.where(frappe.session.user) != "/your-data":
		frappe.local.flags.redirect_location = privacy.where(frappe.session.user)
		raise frappe.Redirect

	context.no_cache = 1
	context.workspace = frappe.db.get_single_value("Workspace Account", "workspace_name") or frappe.local.site
	context.signed_in = frappe.session.user != "Guest"
	context.title = frappe._("Your Data")
	context.one_shell = bool(context.signed_in and one_portal_tabs())
	context.logo = get_app_logo()
	if context.one_shell:
		context.full_width = True
		context.show_sidebar = False
		context.privacy = privacy.state()
	return context
