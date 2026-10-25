"""How OneAI reads what arrives. See one_ai/reading/README.md."""

from frappe.model.document import Document


class IntakeSettings(Document):
	def onload(self):
		from onedesk.one_ai.reading import digest

		self.set_onload("measured", digest.said(digest.this_month()))
