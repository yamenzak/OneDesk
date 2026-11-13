"""A signed link to one record for somebody outside the workspace: a
quotation to accept or decline, a quote request to price, an order or an
invoice to read, without signing in. See one_portal/share.py."""

import frappe
from frappe.model.document import Document
from frappe.utils import sha256_hash


class PortalLink(Document):
	def before_insert(self):
		token = frappe.generate_hash(length=40)
		self.token = token
		self.token_hash = sha256_hash(token)
		self.flags.token = token
