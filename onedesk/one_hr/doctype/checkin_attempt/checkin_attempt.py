from frappe.model.document import Document


class CheckinAttempt(Document):
	"""One row per clock-in tried, whether it was written or refused.

	Nothing here validates: the row is a record of what happened, and a record
	that can refuse to be written is a record of nothing. Everything that
	decides is in `onedesk/one_hr/gates.py` and `ledger.py`, before this.
	"""

	pass
