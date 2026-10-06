"""Nobody is asked what currency they are paid in."""

import frappe

FIELD = "currency"
MODULES = ("HR", "Payroll", "One HR")

#: Filled by their own form script rather than by the schema, so the rule below
#: cannot see it. Checked by reading the script, not by assuming.
ALSO = (
	"Employee Tax Exemption Declaration",
	"Employee Tax Exemption Proof Submission",
)


def hide(*_args) -> None:
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	for doctype in _doctypes():
		if _written(doctype):
			continue
		make_property_setter(
			doctype, FIELD, "hidden", "1", "Check", validate_fields_for_doctype=False
		)
	frappe.clear_cache()


def _doctypes() -> list[str]:
	"""Every HR or payroll Currency link that is filled rather than typed."""
	rows = frappe.db.sql(
		"""
		select df.parent
		from tabDocField df join tabDocType dt on dt.name = df.parent
		where df.fieldname = %s and df.fieldtype = 'Link' and df.options = 'Currency'
		  and dt.module in %s and dt.istable = 0 and df.hidden = 0
		  and (df.read_only = 1 or ifnull(df.fetch_from, '') != '')
		""",
		(FIELD, MODULES),
		pluck=True,
	)
	return sorted(set(rows) | {dt for dt in ALSO if frappe.db.exists("DocType", dt)})


def _written(doctype: str) -> bool:
	"""Whether anybody has already decided this one, us or the tenant."""
	return bool(
		frappe.db.exists(
			"Property Setter", {"doc_type": doctype, "field_name": FIELD, "property": "hidden"}
		)
	)
