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
	"Plan": ("storage_gb", "database_gb", "seats", "credits_a_month"),
	# A pack is bought once, so it grants once. The same number under the
	# monthly field would be a lump somebody's nightly job kept granting.
	"Credit Pack": ("credits",),
	# An add-on is one thing in one size, so it can be bought several times.
	"Add-on": ("storage_gb", "database_gb", "seats", "credits_a_month"),
}


#: The price list's order: plans first, then add-ons, then packs, each by
#: price. `sort_key` carries it, since frappe's list sorts by one field.
RANK = {"Plan": 1, "Add-on": 2, "Credit Pack": 3}


class Offering(Document):
	def validate(self) -> None:
		site.require_admin()
		self.key = (self.key or "").strip().lower()
		# Whether it recurs is the kind's for a pack and an add-on, so neither
		# form asks; only a plan may be paid once or monthly.
		if self.kind == "Credit Pack":
			self.recurring = 0
		elif self.kind == "Add-on":
			self.recurring = 1
		if self.kind != "Plan":
			self.trial_days = 0
		for field in ("storage_gb", "database_gb", "seats", "credits", "credits_a_month"):
			if self.get(field) and field not in CARRIES[self.kind]:
				frappe.throw(
					frappe._("A {0} does not carry {1}.").format(
						self.kind, self.meta.get_label(field)
					)
				)
		if self.kind == "Credit Pack":
			if self.recurring:
				frappe.throw(frappe._("A credit pack is bought once, so it does not recur."))
			if not self.credits:
				frappe.throw(frappe._("A credit pack with no credits in it sells nothing."))
		if self.kind == "Add-on":
			held = [one for one in CARRIES["Add-on"] if self.get(one)]
			if len(held) != 1:
				frappe.throw(frappe._("An add-on adds one thing, in one size."))
			if not self.recurring:
				frappe.throw(frappe._("An add-on is paid for monthly with the plan, so it recurs."))
		if not self.is_new() and (self.has_value_changed("amount") or self.has_value_changed("currency") or self.has_value_changed("recurring")):
			# A Stripe price cannot be changed, so the next sale makes a new one
			# (stripe.price_for). Customers already on the old one keep it.
			self.stripe_price = None
		if self.trial_days and not self.recurring:
			# Stripe carries a trial on the subscription, so there is nowhere to
			# put one on a single payment. A trial here would be a number that
			# shows on the signup page and changes nothing at checkout.
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
