"""One Stripe event, recorded before it is acted on.

The record exists so the unique index on `event_id` can do the work. Stripe
delivers an event more than once by design — on a timeout, on a non-2xx, on a
retry hours later — and every one of those redeliveries is a chance to provision
a second workspace for one payment.
"""

from frappe.model.document import Document


class StripeWebhookEvent(Document):
	pass
