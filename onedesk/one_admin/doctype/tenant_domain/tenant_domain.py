"""A name a customer owns, pointed at their workspace.

The row is ours; the domain is press's to verify and certify. So there is
nothing to validate here beyond the shape of the name, which `one_admin.hosts`
already did before this was written — see `one_admin/domains.py`.
"""

import frappe
from frappe.model.document import Document


class TenantDomain(Document):
	def validate(self):
		from onedesk.one_admin import hosts

		try:
			self.domain = hosts.tidy(self.domain)
		except hosts.Unclaimable as why:
			frappe.throw(str(why))
