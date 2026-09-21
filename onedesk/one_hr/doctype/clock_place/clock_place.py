import frappe
from frappe import _
from frappe.model.document import Document


class ClockPlace(Document):
	def validate(self):
		if self.radius <= 0:
			frappe.throw(_("Radius must be greater than 0."))

		# The section's own sentence offers one or the other; both set would
		# read as an intersection and is matched as a union.
		if self.shift_location and self.employee:
			frappe.throw(_("A place belongs to a Shift Location or to one employee, not to both."))
