"""One movement of credit, submitted on insert and never edited in place.

A balance is a sum over these rows, so they are submittable; the sign is
carried on the row, so `balance` is one SQL sum.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import site

POINTS = {"Grant": 1, "Spend": -1, "Refund": 1}

STARTS_A_BUCKET = "Grant"


class CreditLedgerEntry(Document):
	def validate(self) -> None:
		site.require_admin()
		if not self.credits:
			frappe.throw(frappe._("Credits can't be zero."))

		want = POINTS[self.kind]
		if (self.credits > 0) != (want > 0):
			frappe.throw(
				frappe._("A {0} can't be {1} credits.").format(
					self.kind, self.credits
				)
			)

		if self.kind == STARTS_A_BUCKET:
			if self.against:
				frappe.throw(frappe._("A grant can't be drawn from another entry."))
			return

		self.expires_on = None
		if self.against and frappe.db.get_value("Credit Ledger Entry", self.against, "kind") != (
			STARTS_A_BUCKET
		):
			frappe.throw(frappe._("{0} is not a grant.").format(self.against))
