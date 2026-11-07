"""Screens and print formats that belong to one country, shown where a company
of the workspace is in it, as ERPNext switches its own regional features on by
country; and the countries whose law calls a sales invoice a tax invoice."""

import frappe

ONLY_IN = {
	"UAE VAT 201": "United Arab Emirates",
	"UAE VAT Settings": "United Arab Emirates",
	"Lower Deduction Certificate": "India",
	"South Africa VAT Settings": "South Africa",
	"VAT Audit Report": "South Africa",
	"Import Supplier Invoice": "Italy",
	"One Simplified Tax Invoice": "United Arab Emirates",
}

#: Countries with no personal income tax, where the income tax screens have
#: nothing to hold.
NO_INCOME_TAX = ("Bahrain", "Kuwait", "Oman", "Qatar", "Saudi Arabia", "United Arab Emirates")

#: Screens for a country that taxes income, benefits and accrued earnings
#: with them, hidden where every company is in one that does not.
NOT_IN = {
	name: NO_INCOME_TAX
	for name in (
		"Income Tax Computation",
		"Income Tax Deductions",
		"Income Tax Slab",
		"Employee Tax Exemption Declaration",
		"Employee Tax Exemption Proof Submission",
		"Employee Other Income",
		"Employee Tax Exemption Category",
		"Employee Tax Exemption Sub Category",
		"Employee Benefit Application",
		"Employee Benefit Claim",
		"Accrued Earnings Report",
	)
}

TAX_INVOICE = (
	"Australia",
	"Bahrain",
	"India",
	"Kenya",
	"New Zealand",
	"Oman",
	"Saudi Arabia",
	"Singapore",
	"South Africa",
	"United Arab Emirates",
)


def ours() -> set[str]:
	"""The countries the workspace's companies are in."""
	return set(frappe.get_all("Company", pluck="country", distinct=True)) - {None, ""}


def shown(target: str, here: set[str] | None = None) -> bool:
	"""Whether a screen is for everybody or for a country one of the companies is in."""
	here = ours() if here is None else here
	country = ONLY_IN.get(target)
	if country and country not in here:
		return False
	away = NOT_IN.get(target)
	return not (away and here and here <= set(away))


def tax_invoice(company: str | None) -> bool:
	"""Whether the law where the company is calls its sales invoice, carrying
	its tax number, a tax invoice."""
	return bool(company) and frappe.get_cached_value("Company", company, "country") in TAX_INVOICE
