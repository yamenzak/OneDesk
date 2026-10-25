"""One thing a model is asked to do, and the instruction it is asked with.

A fixture. The copy that decides is the one on the administrator, and only the
operator role may write here.
"""

import frappe
from frappe.model.document import Document


class AIAction(Document):
	def validate(self) -> None:
		self.key = (self.key or "").strip().lower()
		if not (self.instruction or "").strip():
			frappe.throw(frappe._("An action with no instruction is a prompt with no shape."))
