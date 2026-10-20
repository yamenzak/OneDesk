"""One edit to a workbook, written by one_sheet/versions.py as it is saved."""

import frappe
from frappe.model.document import Document


class WorkbookChange(Document):
	pass


def on_doctype_update() -> None:
	frappe.db.add_index("Workbook Change", ["workbook", "seq"])
