"""Credits held while a call is in flight.

Not a ledger entry: a reservation changes — it is taken, then settled for what
the call actually cost — and a ledger entry is written once and never edited.
Keeping them two doctypes is what lets the ledger be append-only.

Written only by `one_admin/ledger.py`, under a lock on the workspace's own row.
"""

from frappe.model.document import Document


class CreditReservation(Document):
	pass
