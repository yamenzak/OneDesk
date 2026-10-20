"""A piece of a document, a message or a record, and its vector.

Written and read only by `one_ai/index.py`; nobody opens one. What a search
finds is checked against the reader through the record it points at.
"""

import frappe
from frappe.model.document import Document


class AIChunk(Document):
	pass


def on_doctype_update() -> None:
	frappe.db.add_index("AI Chunk", ["source_doctype", "source_name"])
