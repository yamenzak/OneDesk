"""One workspace's claim on a private app: its hashed code, and how far the
install has got (one_admin/private.py)."""

from frappe.model.document import Document


class PrivateAppGrant(Document):
	pass
