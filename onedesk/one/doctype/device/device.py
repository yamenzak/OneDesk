"""A machine the company owns: one person's, or shared. See one/devices.py."""

import frappe
from frappe.model.document import Document


class Device(Document):
	def validate(self):
		if self.use == "Shared":
			self.user = None
		elif not self.user and self.asset:
			# The asset's custodian, as OneInventory records who holds it.
			holder = frappe.db.get_value("Asset", self.asset, "custodian")
			self.user = holder and frappe.db.get_value("Employee", holder, "user_id")
