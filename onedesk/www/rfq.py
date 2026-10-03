"""A request for quotation on the portal, answered by the supplier, as One's
(one/portal.py). erpnext's own context, which finds the reader's supplier,
refuses a request not sent to them, and lists the quotes they sent for it."""

from erpnext.templates.pages import rfq

no_cache = 1


def get_context(context):
	rfq.get_context(context)
