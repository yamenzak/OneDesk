"""Your Data for someone who isn't signed in: ask for a copy of what a
workspace holds about you, or that deleted. A signed-in reader has it where
they work (one/privacy.py `where`). See one/privacy_public.py."""

import frappe

no_cache = 1
sitemap = 0


def get_context(context):
	from frappe.core.doctype.navbar_settings.navbar_settings import get_app_logo

	from onedesk.one import privacy, privacy_public

	if frappe.session.user != "Guest" and privacy.where(frappe.session.user) != "/your-data":
		frappe.local.flags.redirect_location = privacy.where(frappe.session.user)
		raise frappe.Redirect

	context.no_cache = 1
	context.workspace = privacy_public.workspace()
	context.signed_in = frappe.session.user != "Guest"
	context.title = frappe._("Your Data")
	context.logo = get_app_logo()
	return context
