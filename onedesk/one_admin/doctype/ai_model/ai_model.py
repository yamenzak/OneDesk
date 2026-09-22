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
			# A withdrawn model does not hold a capability's default against a
			# live one. Measured: Cloudflare dropped llama-3.1-8b-fp8-fast while
			# it was the default, and every attempt to name a replacement was
			# refused by a row for a model that no longer exists.
			held = frappe.db.get_value(
				"AI Model",
				{
					"default_for": self.default_for,
					"name": ["!=", self.name],
					"status": ["!=", "Withdrawn"],
				},
				"name",
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
		# Zero where there is no token price. The column cannot hold nothing, so
		# the list and the form both read zero as "not priced in tokens".
		held, said = priced(self)
		self.input_per_million, self.output_per_million = held or 0, said or 0


def priced(model, money=None) -> tuple[float | None, float | None]:
	"""What this model sells for per million tokens, with today's markup.

	Worked out here rather than read off the rates on the list, because the
	number an operator is choosing on is the one after markup, and the markup is
	either this model's own or the default.
	"""
	from onedesk.one_admin import pricing
	from onedesk.one_admin.prices import Rate

	money = money or frappe.get_cached_doc("One Admin Settings")
	rates = [
		Rate(kind=row.kind, modality=row.modality, unit=row.unit, per=row.per or 1, usd=row.usd or 0)
		for row in model.rates or []
	]
	return pricing.per_million(
		rates, model.markup or money.default_markup or 0, money.credits_per_dollar or 0
	)


def reprice(money) -> None:
	"""Every model's list price again, after the default markup or the credit rate moved.

	Handed the settings being saved, because the cached copy is still the old one
	until the save has finished.
	"""
	for name in frappe.get_all("AI Model", pluck="name"):
		model = frappe.get_doc("AI Model", name)
		held, said = priced(model, money)
		model.db_set({"input_per_million": held or 0, "output_per_million": said or 0}, update_modified=False)
