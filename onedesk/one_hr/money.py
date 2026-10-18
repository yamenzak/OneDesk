"""Nobody is asked what currency they are paid in."""

import frappe

FIELD = "currency"
MODULES = ("HR", "Payroll", "One HR")

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
	_defaults(make_property_setter)
	frappe.clear_cache()


def _defaults(make_property_setter) -> None:
	"""The company's currency as the default of every hidden mandatory
	currency, as company.py does for Company. A field frappe sees hidden,
	mandatory and with no default fails the next sync of that record type's
	customizations, which stops `bench migrate`. The currency it fetches still
	replaces it."""
	currency = frappe.defaults.get_global_default("currency")
	if not currency:
		return
	for doctype in _doctypes(hidden=True):
		field = frappe.get_meta(doctype).get_field(FIELD)
		if not field or not field.reqd or field.default:
			continue
		make_property_setter(doctype, FIELD, "default", currency, "Text", validate_fields_for_doctype=False)


def _doctypes(hidden: bool = False) -> list[str]:
	"""Every HR or payroll Currency link that is filled rather than typed."""
	rows = frappe.db.sql(
		f"""
		select df.parent
		from tabDocField df join tabDocType dt on dt.name = df.parent
		where df.fieldname = %s and df.fieldtype = 'Link' and df.options = 'Currency'
		  and dt.module in %s and dt.istable = 0 {"" if hidden else "and df.hidden = 0"}
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
