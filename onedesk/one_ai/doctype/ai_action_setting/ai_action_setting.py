"""What this workspace wants one action to run on, and what it wants added.

`extra` is added to the action's own instruction, never put in its place.
"""

import frappe
from frappe.model.document import Document

#: How much a workspace may add. Long enough for a house style, short enough
#: that nobody pastes a book into every call they are billed for.
MOST = 2000


class AIActionSetting(Document):
	def validate(self) -> None:
		self.extra = (self.extra or "").strip()
		if len(self.extra) > MOST:
			frappe.throw(
				frappe._("Added instructions are {0} characters; the most is {1}.").format(
					len(self.extra), MOST
				)
			)
