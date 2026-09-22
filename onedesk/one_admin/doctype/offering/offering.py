"""One row in the price list: a plan, a pack of credits, or an add-on.

The old control plane had four doctypes for this — plan, credit pack, add-on and
a catalogue price beside them — and they differed by which fields they left
empty. One doctype with a kind says the same thing and cannot drift, and the
quota set is three named fields rather than a table of open-ended keys, because
a quota nothing enforces is a promise nobody keeps.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import site

#: What each kind is allowed to carry. A credit pack with a storage quota is
#: somebody filling in a field because it was there.
CARRIES = {
	"Plan": ("storage_gb", "seats", "credits_a_month"),
	"Credit Pack": ("credits_a_month",),
	"Add-on": ("storage_gb", "seats", "credits_a_month"),
}


class Offering(Document):
	def validate(self) -> None:
		site.require_admin()
		self.key = (self.key or "").strip().lower()
		for field in ("storage_gb", "seats", "credits_a_month"):
			if self.get(field) and field not in CARRIES[self.kind]:
				frappe.throw(
					frappe._("A {0} does not carry {1}.").format(
						self.kind, self.meta.get_label(field)
					)
				)
		if self.kind == "Credit Pack" and self.recurring:
			frappe.throw(frappe._("A credit pack is bought once, so it does not recur."))
		if self.trial_days and not self.recurring:
			# Stripe carries a trial on the subscription, so there is nowhere to
			# put one on a single payment. A trial here would be a number that
			# shows on the signup page and changes nothing at checkout.
			frappe.throw(frappe._("Only a recurring offering can have a trial."))
