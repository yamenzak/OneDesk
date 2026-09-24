"""A server shown as a folder in OneCloud. See one_storage/mounts.py."""

import frappe
from frappe import _
from frappe.model.document import Document

from onedesk.one import roles


class CloudMount(Document):
	def validate(self):
		self.title = " ".join((self.title or "").replace("/", " ").split())
		if self.shared and roles.ADMINISTRATOR not in frappe.get_roles() and frappe.session.user != "Administrator":
			frappe.throw(_("Only a Workspace Administrator can share a server with everyone."))
		if self.protocol == "WebDAV" and not (self.url or "").startswith(("https://", "http://")):
			frappe.throw(_("A WebDAV address starts with https://."))
		if self.protocol == "SFTP" and not self.host:
			frappe.throw(_("Say which server to connect to."))
		self.root_path = "/" + (self.root_path or "").strip("/")
