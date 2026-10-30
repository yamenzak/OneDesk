import re

import frappe
from frappe import _
from frappe.model.document import Document


class SoundZone(Document):
	def validate(self):
		"""A zone's schedule only changes what is heard."""
		for row in self.programme:
			if row.plays not in ("Music", "Muted"):
				frappe.throw(_("Row {0} of the schedule plays {1}, which is seen, not heard. A zone plays music or is muted.").format(row.idx, _(row.plays)))
			if row.plays == "Music" and not row.music_playlist:
				frappe.throw(_("Row {0} of the schedule plays music but does not say which.").format(row.idx))
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
