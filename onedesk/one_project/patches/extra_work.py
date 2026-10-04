"""Sub-project Of becomes the project and a tick.

A quotation or an order named its project in one of two fields: Project, for
work on it, or Sub-project Of, for extra work that becomes a sub-project when
ordered. Every money document now names its project the one way (chain.py),
so Sub-project Of is Project with **Extra Work** ticked. An order already made
into a sub-project keeps it as its project."""

import frappe


def execute():
	for doctype in ("Quotation", "Sales Order"):
		# The column outlives its Custom Field, which the sync may have taken
		# already, so it is read as a column.
		if not frappe.db.has_column(doctype, "one_project"):
			continue
		rows = frappe.db.sql(
			f"select name, one_project, project from `tab{doctype}` where ifnull(one_project, '') != ''",
			as_dict=True,
		)
		for row in rows:
			values = {"one_extra_work": 1}
			if not row.project:
				values["project"] = row.one_project
			frappe.db.set_value(doctype, row.name, values, update_modified=False)
		frappe.delete_doc("Custom Field", f"{doctype}-one_project", ignore_missing=True, force=True)
