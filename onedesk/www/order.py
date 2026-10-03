"""A quotation, order, invoice, shipment or purchase document on the portal,
as One's (one/portal.py). erpnext's own context, which reads the record, checks
the reader may see it and says whether it can be paid; One adds its public
attachments."""

from erpnext.templates.pages import order

no_cache = 1


def get_context(context):
	order.get_context(context)
	context.attachments = order.get_attachments(context.doc.doctype, context.doc.name)
