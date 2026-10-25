"""A number a document refers to: an invoice, an order, a case. See one_ai/reading/understand.py."""

from frappe.model.document import Document


class ReadingReference(Document):
	pass
