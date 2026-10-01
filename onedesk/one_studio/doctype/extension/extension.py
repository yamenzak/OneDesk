# Copyright (c) 2026, One and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class Extension(Document):
	def validate(self):
		from onedesk.one_studio import extensions

		extensions.validate(self)

	def on_update(self):
		from onedesk.one_studio import extensions

		extensions.sync(self)

	def on_trash(self):
		from onedesk.one_studio import extensions

		extensions.remove(self)
