"""Kinds of employee papers that belong to one country, added where a
company of the workspace is in it (one/countries.py), beside the ones every
workspace has (fixtures/identification_document_type.json). Each kind says
its country (`one_country`, empty for every country), and the kinds a person
picks from are their workspace's countries' and the ones for every country
(`offered`). A workspace adds its own in OneHR's Lists, for any country."""

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

	for country in sorted(countries.ours()):
		for name in wanted({country}):
			if not frappe.db.exists(KIND, name):
				frappe.get_doc({"doctype": KIND, "identification_document_type": name, "one_country": country}).insert(ignore_permissions=True)
			elif not frappe.db.get_value(KIND, name, "one_country"):
				frappe.db.set_value(KIND, name, "one_country", country)


def company_saved(doc, method=None) -> None:
	if doc.get("country") in BY_COUNTRY:
		settle()


def offered() -> list[str]:
	"""The kinds a person in this workspace picks from: every country's, and
	those of the countries its companies are in."""
	from onedesk.one import countries

	ours = countries.ours()
	return [
		one.name
		for one in frappe.get_all(KIND, fields=["name", "one_country"], order_by="name asc")
		if not one.one_country or one.one_country in ours
	]
