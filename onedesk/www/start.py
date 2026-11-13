"""The signup page, on the admin site and nowhere else: the setup wizard
(one_admin/wizard.py), drawn by the portal at /portal/start, with what the
address asked for kept (a plan, a name)."""

from urllib.parse import urlencode

import frappe

from onedesk.one_admin import site

no_cache = 1

KEPT = ("plan", "name", "request", "key")


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError
	said = {key: frappe.form_dict.get(key) for key in KEPT if frappe.form_dict.get(key)}
	frappe.local.flags.redirect_location = "/portal/start" + (f"?{urlencode(said)}" if said else "")
	raise frappe.Redirect
