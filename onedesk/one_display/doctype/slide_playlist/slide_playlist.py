from frappe.model.document import Document


class SlidePlaylist(Document):
	def validate(self):
		from onedesk.one_display import slides

		slides.drawn(self)
