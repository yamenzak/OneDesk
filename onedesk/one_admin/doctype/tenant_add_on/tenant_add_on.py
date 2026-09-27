"""One add-on on a workspace's plan, and how many of it.

A row the workspace changes through the account (quota.py, stripe.py), never
typed: its quantity is what Stripe bills, and a number typed here would be
a limit nobody paid for.
"""

from frappe.model.document import Document


class TenantAddon(Document):
	pass
