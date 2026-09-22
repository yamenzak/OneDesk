"""One address a workspace answers at.

A row rather than a record: the domains belong to the administrator, and this
is a copy written by `one.account.refresh` so a screen can be drawn without a
round trip. Nothing here is edited — adding and removing go through the
account, which asks the administrator, which asks Frappe Cloud.
"""

from frappe.model.document import Document


class WorkspaceDomain(Document):
	pass
