"""A link to a file or folder for people outside the team. See links.py."""

import hashlib

import frappe
from frappe import _
from frappe.model.document import Document


def hashed(token: str) -> str:
	return hashlib.sha256(token.encode()).hexdigest()


class CloudLink(Document):
	def before_insert(self):
		token = frappe.generate_hash(length=32)
		self.token = token
		self.token_hash = hashed(token)
		self.flags.token = token

	def validate(self):
		item = frappe.db.get_value("File", self.file, ["file_name", "is_folder"], as_dict=True)
		if not item:
			frappe.throw(_("That is no longer here."))
		self.file_name, self.is_folder = item.file_name, item.is_folder
		if not self.is_folder:
			self.allow_upload = 0
		seen, kept = set(), []
		for one in self.invitees:
			one.email = (one.email or "").strip().lower()
			if one.email and one.email not in seen:
				seen.add(one.email)
				kept.append(one)
		self.invitees = kept
		if self.audience == "Invited people" and not self.invitees:
			frappe.throw(_("Add the email address of at least one person to invite."))
