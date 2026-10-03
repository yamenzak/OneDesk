"""Custom collections made before they were numbered had a random ID on every
record. New records of each are numbered from its initials now
(record_types.series); the records it has keep their IDs."""

import frappe

from onedesk.one_studio import record_types


def execute():
	for doctype in frappe.get_all(record_types.RECORD_TYPE, pluck="record_doctype"):
		if frappe.db.get_value("DocType", doctype, "autoname") == "hash":
			frappe.db.set_value("DocType", doctype, "autoname", record_types.series(doctype, doctype))
			frappe.clear_cache(doctype=doctype)
