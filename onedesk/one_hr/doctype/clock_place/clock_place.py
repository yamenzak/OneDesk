from frappe import _
from frappe.model.document import Document


class ClockPlace(Document):
	def validate(self):
		if self.radius <= 0:
			from frappe import throw

			throw(_("Radius must be greater than 0."))
