"""Frappe's server error page, as One's portal draws a page. The traceback is
shown only where frappe allows it."""

from frappe.www import error

no_cache = 1


def get_context(context):
	return error.get_context(context)
