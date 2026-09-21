import frappe
from frappe import _
from frappe.model.document import Document

from onedesk.one_hr import rules


class ClockNetwork(Document):
	def validate(self):
		# A range nobody can parse would sit in the list looking like a rule and
		# matching nothing, which is worse than being told at the point of typing.
		if not rules.networks(self.address):
			frappe.throw(
				_("{0} is not an address or a range. Try 203.0.113.7 or 203.0.113.0/24.").format(
					self.address
				)
			)
		self.address = str(rules.networks(self.address)[0])
