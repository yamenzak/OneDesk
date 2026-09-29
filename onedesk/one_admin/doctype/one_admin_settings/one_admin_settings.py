"""The operator's own settings, and the refusal that keeps them the operator's.

Nothing in here is a secret a tenant site is ever given. The press token, the
Cloudflare token and the bucket names stay on this site; a tenant holds its own
token and the URL to send it to, and asks for what it needs.
"""

import frappe
from frappe.model.document import Document

from onedesk.one_admin import site

#: Written by Set Up Cloudflare, not by a person, so not news.
NOT_NEWS = ("cloudflare_setup", "cloudflare_deployed")


class OneAdminSettings(Document):
	def before_validate(self) -> None:
		# A key arrives in the clear only on the save that changes it; frappe
		# stores it and leaves asterisks before validate runs, so this is the
		# one moment to see which were changed. Never what they are.
		self.flags.keys_changed = [
			df.label
			for df in self.meta.fields
			if df.fieldtype == "Password"
			and self.get(df.fieldname)
			and set(str(self.get(df.fieldname))) != {"*"}
		]

	def validate(self) -> None:
		site.require_admin()

	def on_update(self) -> None:
		self._tell()
		# The catalogue's list shows each model's price after markup, so a new
		# default markup or credit rate is a new price on every row of it.
		if self.has_value_changed("default_markup") or self.has_value_changed("credits_per_dollar"):
			from onedesk.one_admin.doctype.ai_model.ai_model import reprice

			reprice(self)

	def _tell(self) -> None:
		"""The other operators hear what changed and who changed it: a price,
		a markup or a grace period with its old and new value, a key only that
		it changed."""
		from frappe.model import no_value_fields

		before = self.get_doc_before_save()
		if not before:
			return
		said = []
		for df in self.meta.fields:
			if df.fieldtype in no_value_fields or df.fieldtype == "Password" or df.fieldname in NOT_NEWS:
				continue
			if not self.has_value_changed(df.fieldname):
				continue
			if df.fieldtype in ("Float", "Currency", "Int", "Select", "Data"):
				said.append(
					f"{frappe._(df.label)}: {before.get(df.fieldname) or '—'} → {self.get(df.fieldname) or '—'}"
				)
			else:
				said.append(frappe._(df.label))
		said += [
			frappe._("{0} (changed)").format(frappe._(label))
			for label in self.flags.get("keys_changed") or []
		]
		if said:
			from onedesk.one_admin import tell

			tell.settings_changed(said)
