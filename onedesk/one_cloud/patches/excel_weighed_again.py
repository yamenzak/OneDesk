"""OneWorkbook now writes into the Excel file itself, so what it drops is
read again: each xlsx File's list the next time it is opened, and the list
of each workbook editing one now."""

import json

import frappe


def execute():
	frappe.db.set_value("File", {"file_name": ["like", "%.xlsx"], "one_fidelity_of": ["is", "set"]}, "one_fidelity_of", None, update_modified=False)
	from onedesk.one_cloud import api, fidelity

	for book in frappe.get_all("Workbook", filters={"source_kind": "xlsx", "would_lose": ["like", '%"%']}, fields=["name", "file"]):
		item = frappe.db.get_value("File", book.file, ["name", "file_name", "file_url"], as_dict=True)
		if not item or not (item.file_name or "").lower().endswith(".xlsx"):
			continue
		try:
			found = fidelity.workbook(api._content(item))
		except OSError:
			continue
		frappe.db.set_value("Workbook", book.name, "would_lose", json.dumps(found), update_modified=False)
