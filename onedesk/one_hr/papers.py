"""Kinds of employee papers that belong to one country, added where a
company of the workspace is in it (one/countries.py), beside the ones every
workspace has (fixtures/identification_document_type.json)."""

import frappe
from frappe import _lt

BY_COUNTRY = {
	"United Arab Emirates": (_lt("Emirates ID"), _lt("Labour Card"), _lt("Health Insurance"), _lt("Medical Fitness")),
}

KIND = "Identification Document Type"


def wanted(countries: set) -> list[str]:
	"""The kinds the countries need. Pure."""
	return [str(one) for country in sorted(countries) for one in BY_COUNTRY.get(country, ())]


def settle(*_args) -> None:
	"""after_migrate, and when a company is saved: each kind its country
	needs, once. A kind is never taken away; papers may point at it."""
	from onedesk.one import countries

	for name in wanted(countries.ours()):
		if not frappe.db.exists(KIND, name):
			frappe.get_doc({"doctype": KIND, "identification_document_type": name}).insert(ignore_permissions=True)


def company_saved(doc, method=None) -> None:
	if doc.get("country") in BY_COUNTRY:
		settle()
