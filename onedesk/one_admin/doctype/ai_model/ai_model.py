"""One model a provider offers, and what it publishes for it.

Everything here is written by `catalogue.py` except one field. `offered` is the
operator's decision and the sync never turns it on — a model appearing in a
provider's API is a fact, and selling it is not.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import site

#: The only field a person may change. Everything else is a copy of what a
#: provider said, and a copy somebody edited is a copy that lies.
THEIRS = ("offered",)


class AIModel(Document):
	def validate(self) -> None:
		site.require_admin()
		if self.offered and self.status != "Priced":
			frappe.throw(
				frappe._("{0} is {1}, so it cannot be offered.").format(self.model, self.status)
			)
