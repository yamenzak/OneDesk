"""One published price, in the provider's own unit.

Nothing here converts anything. `per` and `unit` are read together — a price for
a million tokens is never divided down to one, because a provider that moves to
per-thousand has changed its price and we want to see that rather than paper
over it. See `one_admin/prices.py`.
"""

from frappe.model.document import Document


class AIModelRate(Document):
	pass
