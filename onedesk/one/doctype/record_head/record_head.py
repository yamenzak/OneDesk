"""What a record's form says above its fields: the pill, the sentence, the
band of numbers and the verbs, as rows one renderer draws. See one/head.py and
docs/SHELL.md, decision 4."""

import frappe
from frappe.model.document import Document


class RecordHead(Document):
	def validate(self):
		from onedesk.one import head

		head.validate(self)

	def on_update(self):
		frappe.cache.delete_value("one_record_heads")

	def on_trash(self):
		frappe.cache.delete_value("one_record_heads")
