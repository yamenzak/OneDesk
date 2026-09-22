"""The operator's own settings, and the refusal that keeps them the operator's.

Nothing in here is a secret a tenant site is ever given. The press token, the
Cloudflare token and the bucket names stay on this site; a tenant holds its own
token and the URL to send it to, and asks for what it needs.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import site


class OneAdminSettings(Document):
	def validate(self) -> None:
		site.require_admin()
