"""One model a provider offers, and what it publishes for it.

Everything here is written by `catalogue.py` except one field. `offered` is the
operator's decision and the sync never turns it on — a model appearing in a
provider's API is a fact, and selling it is not.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import capability, site

#: What a person may change. Everything else is a copy of what a provider said,
#: and a copy somebody edited is a copy that lies — except the rates, and only
#: on a model nobody could read a price for, where a person typing one off the
#: page is taking responsibility rather than inventing a default.
THEIRS = ("offered", "default_for", "priced_by_hand", "markup", "rates")


class AIModel(Document):
	def validate(self) -> None:
		site.require_admin()
		if self.offered and self.status != "Priced":
			frappe.throw(
				frappe._("{0} is {1}, so it cannot be offered.").format(self.model, self.status)
			)
		if self.priced_by_hand and not self.rates:
			frappe.throw(
				frappe._("A model priced by hand needs at least one rate on it.")
			)
		if self.default_for:
			if not self.offered:
				frappe.throw(
					frappe._("{0} is not offered, so nothing can default to it.").format(self.model)
				)
			if not capability.able(self.capability, self.default_for):
				frappe.throw(
					frappe._("A {0} model cannot be the default for {1}.").format(
						self.capability, self.default_for
					)
				)
			held = frappe.db.get_value(
				"AI Model", {"default_for": self.default_for, "name": ["!=", self.name]}, "name"
			)
			if held:
				frappe.throw(
					frappe._("{0} is already the default for {1}.").format(held, self.default_for)
				)
		if self.markup is not None and self.markup < 0:
			frappe.throw(frappe._("A markup below nothing would pay somebody to call the model."))
		for rate in self.rates or []:
			if not rate.unit or not rate.per or rate.usd is None:
				frappe.throw(
					frappe._("A rate needs a unit, how many of them, and what they cost.")
				)
