"""One movement of credit, submitted on insert and never edited in place.

Submittable because that is what an append-only record is in Frappe: a balance
is a sum over these rows, so a row somebody could edit is a balance that can be
changed without leaving a trace. Amending one leaves an `amended_from` trail and
cancelling leaves the cancelled row.

The sign is carried on the row rather than implied by the kind, so `balance` is
one SQL sum and not a mapping somebody has to keep in step — and `validate`
refuses a grant that takes credit away.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import site

#: Which way each kind has to point. A refund is positive because it gives back
#: an over-charge; a spend that added credit would be a very quiet bug.
POINTS = {"Grant": 1, "Spend": -1, "Refund": 1}

#: A grant is the only kind that starts a bucket, so it is the only one that may
#: carry a date and the only one that may not be drawn from something else.
STARTS_A_BUCKET = "Grant"


class CreditLedgerEntry(Document):
	def validate(self) -> None:
		site.require_admin()
		if not self.credits:
			frappe.throw(frappe._("A ledger entry of zero credits records nothing."))

		want = POINTS[self.kind]
		if (self.credits > 0) != (want > 0):
			frappe.throw(
				frappe._("A {0} of {1} credits points the wrong way.").format(
					self.kind, self.credits
				)
			)

		if self.kind == STARTS_A_BUCKET:
			if self.against:
				frappe.throw(frappe._("A grant is not drawn from anything."))
			return

		self.expires_on = None
		if self.against and frappe.db.get_value("Credit Ledger Entry", self.against, "kind") != (
			STARTS_A_BUCKET
		):
			frappe.throw(frappe._("{0} is not a grant.").format(self.against))
