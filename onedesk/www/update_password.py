"""frappe's Set Password page (www/update_password.py), and for a portal
reader who is signed in, its Password page in the portal's shell. frappe's
context and script are kept: the page is drawn with the same fields, so
frappe's checks, strength meter and update_password call run as they are."""

import frappe
from frappe.www.update_password import get_context as frappe_context

no_cache = 1


def get_context(context):
	frappe_context(context)
	from onedesk.one.portal import one_portal_tabs

	signed_in = frappe.session.user != "Guest"
	context.one_shell = bool(signed_in and not frappe.form_dict.get("key") and one_portal_tabs())
	if context.one_shell:
		context.full_width = True
		context.show_sidebar = False
