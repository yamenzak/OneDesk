"""A field's options name a thing, as its label does (tests/guards/
test_wording.py): the options that read as sentences were renamed, and the
records that hold them are moved to the new names."""

import frappe

RENAMED = (
	("Extension", "event", "On a Schedule", "Scheduled"),
	("Reading", "state", "Needs a Password", "Password Protected"),
	("Reading", "kind", "Letter From an Authority", "Authority Letter"),
	("Cloud Link", "audience", "Anyone with the link", "Anyone With Link"),
	("Mail Rule", "match", "All of these", "All Conditions"),
	("Mail Rule", "match", "Any of these", "Any Condition"),
	("Sales Order", "one_retention_tax", "With the Invoice", "With Invoice"),
	("Purchase Order", "one_retention_tax", "With the Invoice", "With Invoice"),
)
SINGLES = (("Projects Settings", "one_retention_tax", "With the Invoice", "With Invoice"),)


def execute():
	for doctype, field, old, new in RENAMED:
		if frappe.db.table_exists(doctype) and frappe.db.has_column(doctype, field):
			frappe.db.set_value(doctype, {field: old}, field, new, update_modified=False)
	for doctype, field, old, new in SINGLES:
		if frappe.db.get_single_value(doctype, field) == old:
			frappe.db.set_single_value(doctype, field, new)
