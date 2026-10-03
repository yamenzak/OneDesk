"""Frappe's not-found page, as One's portal draws a page."""


def get_context(context):
	context.http_status_code = 404
