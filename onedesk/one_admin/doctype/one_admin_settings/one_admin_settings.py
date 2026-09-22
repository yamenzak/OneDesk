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

	def on_update(self) -> None:
		# The catalogue's list shows each model's price after markup, so a new
		# default markup or credit rate is a new price on every row of it.
		if self.has_value_changed("default_markup") or self.has_value_changed("credits_per_dollar"):
			from onedesk.one_admin.doctype.ai_model.ai_model import reprice

			reprice(self)
