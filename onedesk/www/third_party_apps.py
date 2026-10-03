"""frappe's Third Party Apps (www/third_party_apps.py), in the portal's shell.
frappe's context and its revoke call are kept; only the page is One's."""

from frappe.www.third_party_apps import get_context as frappe_context

no_cache = 1


def get_context(context):
	frappe_context(context)
	context.show_sidebar = False
	context.no_breadcrumbs = True
