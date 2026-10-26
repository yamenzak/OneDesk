"""A browser somebody signed in on, which an administrator may name and sort.
See one_account/devices.py."""

import frappe
from frappe.model.document import Document


class Device(Document):
	def validate(self):
		if self.use != "Assigned":
			self.user = None
		elif not self.user and self.asset:
			holder = frappe.db.get_value("Asset", self.asset, "custodian")
			self.user = holder and frappe.db.get_value("Employee", holder, "user_id")
		if self.status != "Active":
			self.token_hash = None

	def on_update(self):
		"""Passkeys that no longer belong on it stop working, however it was
		changed: every one on a shared, lost or retired device, and everybody's
		but its person's on an assigned one. Lost also signs out whoever is on it."""
		from onedesk.one_account import devices

		if self.status != "Active" or self.use == "Shared":
			devices.retire_passkeys(self.name)
		elif self.use == "Assigned":
			devices.retire_passkeys(self.name, keep=self.user)
		if self.status == "Lost" and self.has_value_changed("status"):
			devices.sign_out(self.name)
