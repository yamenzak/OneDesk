"""Nobody is asked what currency they are paid in.

One workspace is one company, and a company pays in one currency — the one on
the Company record. Every payroll and HR doctype carries a `Currency` Link
anyway, twenty-two of them, and on a single-company site every one of them shows
the same three letters beside an amount that is already formatted in them.

**Only the ones nobody types are hidden.** A `read_only` currency or one with a
`fetch_from` is filled by the framework or by their own controller, so hiding it
cannot stop a document being saved — that is the whole test, and it is checked
against the schema rather than assumed. Fourteen of the twenty-two qualify.

What stays visible, and why:

* **Salary Structure** declares the currency the assignments and slips fetch
  from. It is the root of the chain and the one place the answer is given.
* **Job Applicant**, **Job Opening** and **Job Opening Template** quote a salary
  range on an advertisement, which is a thing a workspace may genuinely want to
  write in somebody else's currency.
* **Employee Tax Exemption Declaration** and **Proof Submission** are part of the
  India-specific tax surface, which gets one decision rather than six.
* **Payroll Entry** is hidden by its own customization instead, because it is
  neither read-only nor fetched — their form script fills it from the company,
  which was checked in the browser rather than read off the schema.

Derived from the site rather than shipped as a fixture, for the same reason
`one/company.py` is.
"""

import frappe

FIELD = "currency"
MODULES = ("HR", "Payroll", "One HR")


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
	return sorted(set(rows))


def _written(doctype: str) -> bool:
	"""Whether anybody has already decided this one, us or the tenant."""
	return bool(
		frappe.db.exists(
			"Property Setter", {"doc_type": doctype, "field_name": FIELD, "property": "hidden"}
		)
	)
