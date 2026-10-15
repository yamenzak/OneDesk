"""frappe's Set Password page (www/update_password.py), kept for a reset link
and for anyone without a desk or a portal. A portal reader who is signed in
has Password in the portal (frontend/portal, Password.vue)."""

import frappe
from frappe.www.update_password import get_context as frappe_context

from onedesk.one import portal

no_cache = 1


def get_context(context):
	if not frappe.form_dict.get("key") and portal.reads():
		frappe.local.flags.redirect_location = "/portal/password"
		raise frappe.Redirect
	frappe_context(context)
