"""A field OneAI wrote, and what it wrote.

One row per document and field, replaced when it is written again. Nothing
reads it but `one_ai/touch.py`, which hands the form the fields that still say
what was written — so the badge needs no hook on anybody's write path: a
person's edit makes the field differ and the badge simply stops being true.
"""

import frappe
from frappe.model.document import Document


class AITouch(Document):
	pass


def on_doctype_update() -> None:
	# Read on every form load, by document.
	frappe.db.add_index("AI Touch", ["for_doctype", "record"])
