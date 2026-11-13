import frappe
from frappe import _
from frappe.model.document import Document


class SlidePlaylist(Document):
	def validate(self):
		self.plays_what_its_maker_may_open()

	def plays_what_its_maker_may_open(self):
		"""A row plays a presentation whoever sets it may open, so a playlist
		is never a way to show somebody else's private slides (README, Slides)."""
		from onedesk.one_deck import api

		before = {row.name: row.presentation for row in (self.get_doc_before_save() or frappe._dict(slides=[])).slides}
		for row in self.slides:
			if row.kind != "Presentation" or not row.presentation or before.get(row.name) == row.presentation:
				continue
			name = api.presentation_of(frappe.db.get_value("File", row.presentation, "file_url"))
			if not name:
				frappe.throw(_("Row {0}: {1} is not a presentation.").format(row.idx, row.presentation))
			api._may(name, "read")
