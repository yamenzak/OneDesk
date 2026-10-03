"""Frappe's server error page, as One's. The traceback is shown only where
frappe allows it."""

import frappe
from frappe import _
from frappe.www import error

no_cache = 1


def get_context(context):
	# Frappe's own words are "Server Error" and "There was an error building this page".
	context.title = context.title or _("Something went wrong")
	context.message = context.message or _("Try again in a moment.")
	return error.get_context(context)
