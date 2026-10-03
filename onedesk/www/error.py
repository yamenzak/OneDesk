"""Frappe's error page, as One's. Frappe renders it for a page that failed to
build, and for one that does not exist (DoesNotExistError, 404); the code it
gives decides which. The traceback is shown only for a failure, and only where
frappe allows it."""

import frappe
from frappe import _
from frappe.www import error

no_cache = 1


def get_context(context):
	code = frappe.utils.cint(context.http_status_code) or 500
	context.lost_code = str(code)
	if code == 404:
		context.title = _("Page not found")
		context.message = _("The link may be broken, or the page has moved.")
		return {}
	# Frappe's own words are "Server Error" and "There was an error building this page".
	context.title = context.title or _("Something went wrong")
	context.message = context.message or _("Try again in a moment.")
	return error.get_context(context)
