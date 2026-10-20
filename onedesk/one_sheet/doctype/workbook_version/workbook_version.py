"""A workbook whole, at one point in its history (one_sheet/versions.py)."""

import frappe
from frappe.model.document import Document


class WorkbookVersion(Document):
	pass


def on_doctype_update() -> None:
	frappe.db.add_index("Workbook Version", ["workbook", "seq"])
