import re

import frappe
from frappe import _
from frappe.model.document import Document


class SoundZone(Document):
	def validate(self):
		"""A zone's schedule only changes what is heard."""
		for row in self.programme:
			if row.plays not in ("Music", "Muted"):
				frappe.throw(_("Row {0} of the schedule shows {1}. A sound zone schedule can only play music or mute.").format(row.idx, _(row.plays)))
			if row.plays == "Music" and not row.music_playlist:
				frappe.throw(_("Row {0} of the schedule needs a music playlist.").format(row.idx))
		from onedesk.one_display.programme import TIME

		for row in self.ads:
			if row.plays != "At Times":
				continue
			times = [one for one in re.split(r"[,\s]+", row.at_times or "") if one]
			if not times:
				frappe.throw(_("Row {0} of the voice ads needs at least one time.").format(row.idx))
			wrong = [one for one in times if not TIME.fullmatch(one) or int(TIME.fullmatch(one).group(1)) > 23 or int(TIME.fullmatch(one).group(2)) > 59]
			if wrong:
				frappe.throw(_("{1} in row {0} of the voice ads is not a valid time.").format(row.idx, ", ".join(wrong)))
