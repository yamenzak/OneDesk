# Copyright (c) 2026, One and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class RecordType(Document):
	# Where it lives holds however it is changed. See record_types.held.
	def validate(self):
		from onedesk.one_studio import record_types

		record_types.held(self)

	def on_update(self):
		from onedesk.one_studio import record_types

		record_types.moved(self)

	def on_trash(self):
		from onedesk.one_studio import record_types

		record_types.remove(self)
