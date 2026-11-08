import frappe


def execute():
	"""The DocType Link from Non Conformance to Quality Action goes; the
	connection is now one_quality.connections.dashboard."""
	frappe.db.delete("DocType Link", {"parent": "Non Conformance", "link_doctype": "Quality Action", "link_fieldname": "one_non_conformance"})
	frappe.clear_cache(doctype="Non Conformance")
