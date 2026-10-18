import frappe
from frappe import _
from frappe.model.document import Document

from onedesk.one_hr import rules


class ClockNetwork(Document):
	def validate(self):
		if not rules.networks(self.address):
			frappe.throw(
				_("{0} is not a valid address or range. Example: 203.0.113.7 or 203.0.113.0/24").format(
					self.address
				)
			)
		self.address = str(rules.networks(self.address)[0])

		if self.shift_location and self.employee:
			frappe.throw(
				_("A network belongs to a Shift Location or to one employee, not to both.")
			)
