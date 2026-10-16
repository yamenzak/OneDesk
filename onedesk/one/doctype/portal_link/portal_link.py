"""A signed link to one record for somebody outside the workspace: a
quotation to accept or decline, a quote request to price, an order or an
invoice to read, without signing in. See one/portal_share.py."""

import hashlib

import frappe
from frappe.model.document import Document


def hashed(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


class PortalLink(Document):
	def before_insert(self):
		token = frappe.generate_hash(length=40)
		self.token = token
		self.token_hash = hashed(token)
		self.flags.token = token
