# Copyright (c) 2026, One and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class RecordType(Document):
	def on_trash(self):
		from onedesk.one_studio import record_types

		record_types.remove(self)
