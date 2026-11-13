"""One of our servers: where it is, what is on it, how full it is. Made by
Order Server and read every five minutes (servers.watch). Open and the limit are
the operators' to change. A connected one is kept as Released once it is let
go (releasing.py), and only then may it be deleted."""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import fleet


class WorkspaceServer(Document):
	def before_insert(self) -> None:
		if not self.flags.ordered:
			frappe.throw(frappe._("Use Order Server or Connect Server to add a server."))

	def on_trash(self) -> None:
		if self.status == fleet.RELEASED or self.flags.dropped:
			return
		if self.connected:
			frappe.throw(frappe._("Release {0} before deleting it.").format(self.server))
		frappe.throw(frappe._("{0} is a box we ordered, and its row goes only with the box.").format(self.server))
