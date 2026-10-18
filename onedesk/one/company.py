"""One workspace is one company, so nobody is ever asked which.

Every `Company` Link is hidden and filled by the global default, worked out
from the site's own schema after every migrate.
"""

import frappe

FIELD = "company"
OFF = (("hidden", "1"), ("in_list_view", "0"), ("in_standard_filter", "0"))


def hide(*_args) -> None:
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for field in _fields():
		for prop, value in OFF:
			if field.get(prop) == int(value):
				continue
			if _written(field["parent"], prop):
				continue
			make_property_setter(
				field["parent"],
				FIELD,
				prop,
				value,
				"Check",
				validate_fields_for_doctype=False,
			)
	_defaults(make_property_setter)
	frappe.clear_cache()


def _defaults(make_property_setter) -> None:
	"""The company as the default of every hidden mandatory Company field, and
	again when the company it named is gone."""
	company = frappe.defaults.get_global_default("company")
	if not company or not frappe.db.exists("Company", company):
		return
	for field in _fields():
		if not field.get("reqd") or field.get("default"):
			continue
		said = frappe.db.get_value(
			"Property Setter", {"doc_type": field["parent"], "field_name": FIELD, "property": "default"}, "value"
		)
		if said and frappe.db.exists("Company", said):
			continue
		make_property_setter(
			field["parent"], FIELD, "default", company, "Text", validate_fields_for_doctype=False
		)


def _fields() -> list[dict]:
	"""Every Company Link called `company`, standard and custom alike."""
	where = {"fieldname": FIELD, "fieldtype": "Link", "options": "Company"}
	columns = ["hidden", "in_list_view", "in_standard_filter", "reqd", "default"]
	standard = frappe.get_all("DocField", filters=where, fields=["parent", *columns])
	custom = frappe.get_all(
		"Custom Field",
		filters=where,
		fields=["dt as parent", *columns],
	)
	return standard + custom


def _written(doctype: str, prop: str) -> bool:
	"""Whether anybody has already set this property, us or the tenant.

	Same rule as `policy.seed`: a workspace that deliberately put the field back
	keeps it, because a default that reasserts itself every migrate is not a
	default.
	"""
	return bool(
		frappe.db.exists(
			"Property Setter", {"doc_type": doctype, "field_name": FIELD, "property": prop}
		)
	)
