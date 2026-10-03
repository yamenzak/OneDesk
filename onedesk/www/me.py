"""Frappe's /me, as One's. Someone with a desk has their profile there, and an
account holder on the admin site has /account; anyone else (a customer's
contact on a workspace's portal) gets this page in One's portal look, with
frappe's account pages and no link to a desk they cannot open."""

import frappe
from frappe import _

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.throw(_("You need to be logged in to access this page"), frappe.PermissionError)
	if frappe.session.data.user_type == "System User":
		frappe.local.flags.redirect_location = "/desk/settings?section=profile"
		raise frappe.Redirect
	from onedesk.one_admin import site

	if site.is_admin():
		frappe.local.flags.redirect_location = "/account"
		raise frappe.Redirect
	context.current_user = frappe.get_doc("User", frappe.session.user)
	# frappe's Third Party Apps, only for someone who has let an app in.
	context.has_apps = bool(frappe.db.exists("OAuth Bearer Token", {"user": frappe.session.user}))
	context.show_sidebar = False
