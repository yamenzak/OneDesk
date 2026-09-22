"""A customer's workspace, as we asked press for it.

Not a copy of what press holds. This record has to be readable when press is
unreachable — which is exactly when somebody is asking why a workspace is down —
so it carries what we decided rather than what press reports.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import site


class Tenant(Document):
	def validate(self) -> None:
		site.require_admin()
		self.slug = (self.slug or "").strip().lower()
		if not self.slug.replace("-", "").isalnum():
			frappe.throw(frappe._("A slug is letters, digits and hyphens: {0}").format(self.slug))
		if not self.domain and self.slug:
			self.domain = f"{self.slug}.{_tenant_domain()}"


def _tenant_domain() -> str:
	return frappe.get_cached_value("One Admin Settings", None, "tenant_domain") or "t.4dl.app"
