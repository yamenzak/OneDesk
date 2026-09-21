"""An employee link says the person's name, so nothing has to repeat it.

Frappe already knows how to show a link by its title: set
`show_title_field_in_link` on the doctype and every link to it — on a form, in
a grid, in a list, in a printed document — reads the title instead of the id.
Employee has a title field (`employee_name`) and had the switch off, so every
link to it read `HR-EMP-00004` and erpnext's answer was to hang a read-only
`Employee Name` beside it, fetched from the same record.

That is fifty-odd doctypes each saying the same thing twice:

    Employee      HR-EMP-00004: Tarek Nassar
    Employee Name Tarek Nassar

The switch is set in `one_hr/custom/employee.json`, and this sweeps away the
mirrors it makes redundant. Only fields that are literally `fetch_from` the
link are touched — a mirror by definition, kept in step by the framework rather
than typed — and only on parent doctypes, because in a grid the mirror *is* the
column somebody reads.

A list keeps its name: `employee_name` is the title field on almost all of
these, and a list's title column is drawn from the doctype's `title_field`
rather than from the field being visible. Where it is not the title field and
is `in_list_view`, it is left alone — `Goal` is the one such row — because
hiding it there would take the person's name off the list and put nothing back.

The other half is the list column. Where `employee_name` is the title field the
list already opens with the person's name, and the `employee` column beside it
now reads the name too, because the link renders its title. So a Salary Slip
list said *Rania Sabbagh · Draft · Rania Sabbagh*. That column comes off — but
only where the title is the name, because everywhere else it is the only place
the person appears.

Derived from the site rather than shipped as a fixture, for the same reason
`one/company.py` is: the set of doctypes depends on which apps the site
carries, and only the site knows that.
"""

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
