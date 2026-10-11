"""The rules of making that hold however a work order is saved."""

import frappe


def steps(doc, method=None) -> None:
	"""Work Order before_validate: a draft whose bill of materials has steps
	takes them. The form fetches them when the bill is chosen, so one made by
	Data Import, OneAI or a script would otherwise have none, and so no job
	cards when it is submitted."""
	if doc.docstatus != 0 or not doc.bom_no or doc.get("operations"):
		return
	if frappe.get_cached_value("BOM", doc.bom_no, "with_operations"):
		doc.set_work_order_operations()
