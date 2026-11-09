"""An app made for some workspaces only (one_admin/private.py)."""

import re

import frappe
from frappe import _
from frappe.model.document import Document

APP_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


class PrivateApp(Document):
	def validate(self):
		if not APP_NAME.match(self.app or ""):
			frappe.throw(_("An app's name is lowercase letters, digits and underscores."))
		before = self.get_doc_before_save()
		if not before:
			return
		kept = {row.name for row in self.grants}
		gone = [row.tenant for row in before.grants if row.status != "Offered" and row.name not in kept]
		if gone:
			frappe.throw(_("{0} claimed this app, and an installed app stays.").format(", ".join(gone)))
