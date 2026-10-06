"""A fact somebody asked OneAI to keep.

Written only by approving a card from `one_ai/memory.py`'s `remember`, or by
hand in the list; read by the same module. Private through the doctype's own
if-owner permission, the rule AI Chat already lives by.
"""

import frappe
from frappe import _
from frappe.model.document import Document


class AIMemory(Document):
	# A fact is one line of up to 500 characters, and it is about a record its
	# keeper may open, however it is written (the panel, Settings, the list).
	def validate(self):
		self.fact = " ".join((self.fact or "").split())[:500]
		if not self.fact:
			frappe.throw(_("Say what OneAI should keep in mind."))
		if self.about_doctype and self.about_name and not frappe.has_permission(
			self.about_doctype, "read", doc=self.about_name, user=self.owner or frappe.session.user
		):
			frappe.throw(_("You cannot open that record."), frappe.PermissionError)

	# The owner's Settings page and panel redraw when a memory is kept,
	# changed or forgotten, from wherever that happened.
	def on_update(self):
		self.told()

	def on_trash(self):
		self.told()

	def told(self):
		frappe.publish_realtime("one_memory", user=self.owner, after_commit=True)
