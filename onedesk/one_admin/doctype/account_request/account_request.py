"""Somebody asking for a workspace, before any money has moved.

Kept apart from `Tenant` on purpose. A request is a thing that can be abandoned,
refused or paid for twice; a tenant is a workspace that exists. Merging them
would mean a Tenant table full of people who changed their minds.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import signup, site


class AccountRequest(Document):
	def validate(self) -> None:
		site.require_admin()
		self.slug = signup.tidy_slug(self.slug or self.workspace_name or "")
		if self.is_new():
			signup.refuse_a_taken_slug(self.slug)
