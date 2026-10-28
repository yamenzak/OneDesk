"""frappe's Third Party Apps (www/third_party_apps.py). A portal reader has
them in the portal (frontend/portal, Apps.vue), with frappe's revoke call."""

import frappe
from frappe.www.third_party_apps import get_context as frappe_context

from onedesk.one_portal import portal

no_cache = 1


def get_context(context):
	if portal.reads():
		frappe.local.flags.redirect_location = "/portal/apps"
		raise frappe.Redirect
	frappe_context(context)
