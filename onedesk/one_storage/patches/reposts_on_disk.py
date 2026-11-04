"""Stock revaluations that failed on R2 run again. ERPNext rewrites its
working file in place by disk path, which an R2 file has none of, so every
back-dated stock change failed and left the books and the warehouses apart
(store.IN_PLACE keeps new ones on disk). Each failed one loses its R2
working file, which ERPNext makes again, and is queued for the worker."""

import frappe

from onedesk.one_storage import store


def execute():
	for repost in frappe.get_all(
		"Repost Item Valuation",
		filters={"status": ["in", ["Failed", "Queued"]], "docstatus": 1},
		fields=["name", "status", "reposting_data_file"],
	):
		stored = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Repost Item Valuation", "attached_to_name": repost.name},
			fields=["name", "file_url"],
		)
		gone = [one for one in stored if store.is_stored(one.file_url)]
		if not gone and repost.status == "Queued":
			continue
		for one in gone:
			frappe.delete_doc("File", one.name, ignore_permissions=True, force=True)
		frappe.db.set_value(
			"Repost Item Valuation", repost.name, {"status": "Queued", "reposting_data_file": None}, update_modified=False
		)
