"""A fact somebody asked OneAI to keep.

Written only by approving a card from `one_ai/memory.py`'s `remember`, or by
hand in the list; read by the same module. Private through the doctype's own
if-owner permission, the rule AI Chat already lives by.
"""

from frappe.model.document import Document


class AIMemory(Document):
	pass
