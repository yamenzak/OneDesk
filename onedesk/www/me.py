"""Frappe's /me, as One's. Someone with a desk has their profile there, and an
account holder on the admin site has /account; anyone else (a customer's
contact on a workspace's portal) has their Profile, the first of the
portal's Account pages (one/portal.py)."""

from urllib.parse import quote

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
	frappe.local.flags.redirect_location = f"/update-profile/{quote(frappe.session.user)}/edit"
	raise frappe.Redirect
