"""One workspace is one company, so nobody is ever asked which.

Multi-company is not a thing One does. A group that runs four companies buys
four workspaces, which is the commercial decision and also the simpler product:
there is no consolidation, no inter-company anything, and no screen anywhere
that has to ask *whose* this is. What is left over from erpnext and hrms is a
mandatory `Company` Link on about two hundred and fifty doctypes, showing the
same value every time — a field that can only be got wrong and never right.

So every one of them is hidden, and the global default fills it. Where a
document can do better than the default it does: an attendance request and a
shift request take the company from the employee, because that is the answer
even on a site somebody has left two Company records on.

**This is derived from the site rather than shipped as a fixture.** A generated
fixture would have to be pinned to one bench's set of apps, and a site that does
not carry erpnext would fail to import rows naming doctypes it has never heard
of. The list is a query over the schema the site actually has, which is a thing
only the site knows — so it runs after every migrate, beside `policy.seed`, and
by the same rule: write it once, and never overrule a tenant who changed it.
"""

import frappe

#: The field, and the two other places it would otherwise keep showing up.
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
	frappe.clear_cache()


def _fields() -> list[dict]:
	"""Every Company Link called `company`, standard and custom alike."""
	where = {"fieldname": FIELD, "fieldtype": "Link", "options": "Company"}
	columns = ["hidden", "in_list_view", "in_standard_filter"]
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
