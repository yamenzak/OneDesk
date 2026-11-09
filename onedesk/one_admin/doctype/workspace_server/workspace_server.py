"""One of our servers: where it is, what is on it, how full it is. Made by
Order Server and read every five minutes (servers.watch). Open and the limit are
the operators' to change."""

import frappe
from frappe.model.document import Document


class WorkspaceServer(Document):
	def before_insert(self) -> None:
		if not self.flags.ordered:
			frappe.throw(frappe._("Use Order Server or Connect Server to add a server."))
