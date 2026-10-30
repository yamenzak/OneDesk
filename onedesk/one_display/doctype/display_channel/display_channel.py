import re

import frappe
from frappe import _
from frappe.model.document import Document

NEEDS = {"Slides": "slide_playlist", "Widgets": "widget_collection", "Music": "music_playlist"}


class DisplayChannel(Document):
	def validate(self):
		from onedesk.one_display import sizes

		sizes.settle(self)
		for row in self.programme:
			needed = NEEDS.get(row.plays)
			if needed and not row.get(needed):
				frappe.throw(_("Row {0} of the schedule plays {1} but does not say which.").format(row.idx, _(row.plays)))
			for other in set(NEEDS.values()) - {needed}:
				row.set(other, None)
		from onedesk.one_display.programme import TIME

		for row in self.ads:
			if row.plays != "At Times":
				continue
			times = [one for one in re.split(r"[,\s]+", row.at_times or "") if one]
			if not times:
				frappe.throw(_("Row {0} of the voice ads plays at times but names none.").format(row.idx))
			wrong = [one for one in times if not TIME.fullmatch(one) or int(TIME.fullmatch(one).group(1)) > 23 or int(TIME.fullmatch(one).group(2)) > 59]
			if wrong:
				frappe.throw(_("Row {0} of the voice ads has {1}, which is not a time of day.").format(row.idx, ", ".join(wrong)))
