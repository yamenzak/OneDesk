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

CARRIES = {
	"Plan": ("storage_gb", "database_gb", "seats", "credits_a_month"),
	"Credit Pack": ("credits",),
	"Add-on": ("storage_gb", "database_gb", "seats", "credits_a_month"),
}


RANK = {"Plan": 1, "Add-on": 2, "Credit Pack": 3}


class Offering(Document):
	def validate(self) -> None:
		site.require_admin()
		self.key = (self.key or "").strip().lower()
		if self.kind == "Credit Pack":
			self.recurring = 0
		elif self.kind == "Add-on":
			self.recurring = 1
		if self.kind != "Plan":
			self.trial_days = 0
		for field in ("storage_gb", "database_gb", "seats", "credits", "credits_a_month"):
			if self.get(field) and field not in CARRIES[self.kind]:
				frappe.throw(
					frappe._("A {0} can't have {1}.").format(
						self.kind, self.meta.get_label(field)
					)
				)
		if self.kind == "Credit Pack":
			if self.recurring:
				frappe.throw(frappe._("A credit pack can't be recurring."))
			if not self.credits:
				frappe.throw(frappe._("A credit pack needs credits."))
		if self.kind == "Add-on":
			held = [one for one in CARRIES["Add-on"] if self.get(one)]
			if len(held) != 1:
				frappe.throw(frappe._("An add-on adds exactly one thing."))
			if not self.recurring:
				frappe.throw(frappe._("An add-on must be recurring."))
		if not self.is_new() and (self.has_value_changed("amount") or self.has_value_changed("currency") or self.has_value_changed("recurring")):
			self.stripe_price = None
		if self.trial_days and not self.recurring:
			frappe.throw(frappe._("Only a recurring offering can have a trial."))
		self.gives = gives(self)
		self.sort_key = RANK.get(self.kind, 9) * 1_000_000 + (self.amount or 0)


def gives(offering) -> str:
	"""What an offering gives, in one line: "20 GB · 1 GB database · 5 seats
	· 1,000 credits a month". Zero on a plan is unlimited; on an add-on or
	a pack it is simply not part of it."""
	from frappe import _
	from frappe.utils import fmt_money

	def number(value):
		return fmt_money(value, precision=0)

	plan = offering.kind == "Plan"
	said = []
	for field, words, unlimited in (
		("storage_gb", _("{0} GB storage"), _("unlimited storage")),
		("database_gb", _("{0} GB database"), _("unlimited database")),
		("seats", _("{0} seats"), _("unlimited seats")),
	):
		if field not in CARRIES.get(offering.kind, ()):
			continue
		value = offering.get(field)
		if value:
			said.append(words.format(number(value)))
		elif plan:
			said.append(unlimited)
	if offering.get("credits_a_month"):
		said.append(_("{0} credits a month").format(number(offering.credits_a_month)))
	if offering.get("credits"):
		said.append(_("{0} credits").format(number(offering.credits)))
	return " · ".join(said)
