"""One thing a model is asked to do, and the instruction it is asked with.

A fixture, so a new action arrives with a migrate and an operator's edit to one
survives the next. It exists on every site because a workspace has to know what
it may ask for — but **the copy that decides is the one on the administrator**,
which is where a call is made from. A workspace editing its own copy changes
nothing, and the permissions say so: only the operator role may write here, and
nobody on a tenant site has it.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import capability


class AIAction(Document):
	def validate(self) -> None:
		self.key = (self.key or "").strip().lower()
		if self.capability not in capability.WORDS:
			frappe.throw(
				frappe._("{0} is not a capability any model carries.").format(self.capability)
			)
		if not (self.instruction or "").strip():
			frappe.throw(frappe._("An action with no instruction is a prompt with no shape."))
