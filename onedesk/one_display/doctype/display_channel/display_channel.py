import frappe
from frappe import _
from frappe.model.document import Document

NEEDS = {"Slides": "slide_playlist", "Widgets": "widget_collection"}


class DisplayChannel(Document):
	def validate(self):
		from onedesk.one_display import sizes

		sizes.settle(self)
		for row in self.programme:
			if row.plays == "Music":
				frappe.throw(_("Row {0} of the schedule plays music. Set music in a sound zone instead.").format(row.idx))
			needed = NEEDS.get(row.plays)
			if needed and not row.get(needed):
				frappe.throw(_("Row {0} of the schedule needs a {1}.").format(row.idx, _(row.plays)))
			for other in {*NEEDS.values(), "music_playlist"} - {needed}:
				row.set(other, None)
