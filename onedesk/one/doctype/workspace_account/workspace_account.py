"""What this workspace last heard about itself, kept so a screen never waits.

Read-only to everybody. It is written by `one/account.py` from the administrator's
answer and by nothing else — a field somebody can type into here would be a
number that disagrees with the invoice.
"""

from frappe.model.document import Document


class WorkspaceAccount(Document):
	pass
