import frappe
from frappe.model.document import Document


class VoicePack(Document):
	def autoname(self):
		from onedesk.one_display.packs import name_of

		self.name = name_of(self.language, self.voice, self.tone or "Announcement")

	def onload(self):
		from onedesk.one_display.packs import covers

		self.set_onload("covers", covers(self.name))
