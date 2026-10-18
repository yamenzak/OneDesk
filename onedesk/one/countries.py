"""Screens that belong to one country, shown where a company of the workspace
is in it, as ERPNext switches its own regional features on by country."""

import frappe

ONLY_IN = {
	"UAE VAT 201": "United Arab Emirates",
	"UAE VAT Settings": "United Arab Emirates",
	"Lower Deduction Certificate": "India",
	"South Africa VAT Settings": "South Africa",
	"VAT Audit Report": "South Africa",
	"Import Supplier Invoice": "Italy",
}


def ours() -> set[str]:
	"""The countries the workspace's companies are in."""
	return set(frappe.get_all("Company", pluck="country", distinct=True)) - {None, ""}


def shown(target: str, here: set[str] | None = None) -> bool:
	"""Whether a screen is for everybody or for a country one of the companies is in."""
	country = ONLY_IN.get(target)
	return not country or country in (ours() if here is None else here)
