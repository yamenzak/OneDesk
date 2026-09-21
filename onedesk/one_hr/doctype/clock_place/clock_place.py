from frappe import _
from frappe.model.document import Document


class ClockPlace(Document):
	def validate(self):
		if self.radius <= 0:
			from frappe import throw

			throw(_("A zone with no radius is a circle nothing is inside."))
