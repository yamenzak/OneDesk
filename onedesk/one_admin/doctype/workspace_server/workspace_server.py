"""One of our servers new workspaces may be built on.

A row in Settings, not a table of Frappe Cloud's state: the server is bought
and added to the bench group in Frappe Cloud, and listed here to say it may
take workspaces, whether EU ones, and how many. Its region is read back from
Frappe Cloud rather than typed (one_admin_settings.py).
"""

from frappe.model.document import Document


class WorkspaceServer(Document):
	pass
