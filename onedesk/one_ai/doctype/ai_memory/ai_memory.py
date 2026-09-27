"""A fact somebody asked OneAI to keep.

Written only by approving a card from `one_ai/memory.py`'s `remember`, or by
hand in the list; read by the same module. Private through the doctype's own
if-owner permission, the rule AI Chat already lives by.
"""

import frappe
from frappe.model.document import Document


class AIMemory(Document):
	# The owner's Settings page and panel redraw when a memory is kept,
	# changed or forgotten, from wherever that happened.
	def on_update(self):
		self.told()

	def on_trash(self):
		self.told()

	def told(self):
		frappe.publish_realtime("one_memory", user=self.owner, after_commit=True)
