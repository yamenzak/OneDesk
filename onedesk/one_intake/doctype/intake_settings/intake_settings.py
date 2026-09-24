"""How OneAI reads what arrives. See one_intake/README.md."""

from frappe.model.document import Document


class IntakeSettings(Document):
	def onload(self):
		# The monthly number, at the top of the settings. See one_intake/digest.py.
		from onedesk.one_intake import digest

		self.set_onload("measured", digest.said(digest.this_month()))
