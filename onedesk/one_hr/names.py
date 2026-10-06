"""An employee link says the person's name, so nothing has to repeat it."""

import frappe

MIRROR = "employee_name"
LINK = "employee"
FETCHED = "employee.employee_name"


def hide(*_args) -> None:
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for doctype in _doctypes():
		if not _written(doctype, MIRROR, "hidden"):
			make_property_setter(
				doctype, MIRROR, "hidden", "1", "Check", validate_fields_for_doctype=False
			)
		if _doubled(doctype) and not _written(doctype, LINK, "in_list_view"):
			make_property_setter(
				doctype, LINK, "in_list_view", "0", "Check", validate_fields_for_doctype=False
			)
	frappe.clear_cache()


def _doubled(doctype: str) -> bool:
	"""Whether the list would name the person twice — as its title and as a column."""
	meta = frappe.get_meta(doctype)
	field = meta.get_field(LINK)
	return bool(meta.title_field == MIRROR and field and field.in_list_view)


def _doctypes() -> list[str]:
	"""Every parent doctype whose Employee Name is fetched from its Employee."""
	fields = frappe.get_all(
		"DocField",
		filters={"fieldname": MIRROR, "fetch_from": FETCHED, "parenttype": "DocType"},
		fields=["parent", "in_list_view", "hidden"],
	)
	out = []
	for field in fields:
		if field.hidden:
			continue
		meta = frappe.get_meta(field.parent)
		if meta.istable:
			continue
		if field.in_list_view and meta.title_field != MIRROR:
			continue
		out.append(field.parent)
	return sorted(set(out))


def _written(doctype: str, field: str, prop: str) -> bool:
	"""Whether anybody has already decided this one, us or the tenant."""
	return bool(
		frappe.db.exists(
			"Property Setter", {"doc_type": doctype, "field_name": field, "property": prop}
		)
	)
