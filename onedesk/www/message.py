"""Frappe's message page, as One's portal draws a page. What it says is
frappe's own: the message set for the request, or kept under its id."""

from frappe.www import message

no_cache = 1


def get_context(context):
	return message.get_context(context)
