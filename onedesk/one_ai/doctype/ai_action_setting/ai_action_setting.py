"""What this workspace wants one action to run on, and what it wants added.

The model is a name on the administrator rather than a link, because the
catalogue lives there and a workspace holds no copy of it — the picker asks for
the list and stores what was chosen.

`extra` is the whole of what a workspace may say to a model, and it is **added**
to the action's own instruction rather than replacing it. That distinction is
the safety of the feature: a workspace can tell the summariser to write in
Arabic and keep it terse, and cannot tell it to ignore what it was told about
what it may touch.
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
