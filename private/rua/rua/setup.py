"""Rua Company's workspace, set the way the old app worked: its years from
2023, its supplier kinds, its products, its quotation sections and its pay.

Everything here is idempotent: it runs on install and again before every
import, and a thing already there is left as it is.
"""

import frappe
from frappe.utils import getdate, today

COMPANY = "Rua Company"
ABBR = "RC"
FIRST_YEAR = 2023

SUPPLIER_GROUPS = ("Aluminium", "Glass", "Cladding")

# The products a quotation is priced in, after the costing sheet. A piece
# carries its size without being counted by it; cladding and handrails are
# sold by the area and the length.
PRODUCTS = (
	("Curtain Wall", "Nos", "Piece"),
	("Window", "Nos", "Piece"),
	("Door", "Nos", "Piece"),
	("Louver", "Nos", "Piece"),
	("Skylight", "Nos", "Piece"),
	("Shower Partition", "Nos", "Piece"),
	("ACP Cladding", "Square Meter", "Area"),
	("Glass Handrail", "Meter", "Length"),
	("Steel Handrail", "Meter", "Length"),
	("Aluminium Works", "Nos", "Piece"),
)
SITE_EXPENSE = "Site Expenses"

TERMS = "Rua Quotation"
SECTIONS = (
	"Specification",
	"Standard Qualifications",
	"Scope of Work",
	"Exclusions",
	"Maintenance and Warranty",
	"Duration and Payment",
	"Terms and Conditions",
	"Proposal Basis",
)

STRUCTURE = "Rua Monthly"
BASIC = "Basic"
ALLOWANCE = "Allowance"


def run():
	wizard()
	company = frappe.db.get_default("company") or frappe.get_all("Company", pluck="name", limit=1)[0]
	years(company)
	books(company)
	groups()
	items(company)
	terms()
	pay(company)
	frappe.db.commit()
	return company


def wizard():
	"""A site nobody has set up yet (a copy made to try the import on) is set
	up as Rua: a workspace in use has been set up by the person who signed
	up, and is left as it is."""
	if frappe.is_setup_complete():
		return
	from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

	year = getdate(today()).year
	said = setup_complete(
		{
			"language": "English",
			"country": "United Arab Emirates",
			"timezone": "Asia/Dubai",
			"currency": "AED",
			"company_name": COMPANY,
			"company_abbr": ABBR,
			"chart_of_accounts": "U.A.E - Chart of Accounts",
			"fy_start_date": f"{year}-01-01",
			"fy_end_date": f"{year}-12-31",
			"setup_demo": 0,
		}
	)
	if (said or {}).get("status") != "ok":
		frappe.throw(f"The setup wizard did not finish: {said}")
	frappe.db.commit()


def years(company):
	"""Every calendar year from Rua's first payment to this one."""
	for year in range(FIRST_YEAR, getdate(today()).year + 1):
		start = f"{year}-01-01"
		found = frappe.db.get_value("Fiscal Year", {"year_start_date": start})
		if not found:
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": str(year),
					"year_start_date": start,
					"year_end_date": f"{year}-12-31",
					"companies": [{"company": company}],
				}
			).insert(ignore_permissions=True)


def books(company):
	"""What OneBook's Get Started asks of a UAE company before its first sale:
	VAT charged on every invoice and bill, the VAT accounts the return reads,
	and the emirate sales are reported under. Rua works from Abu Dhabi, and
	held retention once, so retention is on, taxed when it is released as
	the UAE taxes it."""
	from onedesk.one_book import ready, vat

	frappe.db.set_single_value("Accounts Settings", "add_taxes_from_taxes_and_charges_template", 1)
	frappe.db.set_single_value("Accounts Settings", "check_supplier_invoice_uniqueness", 1)
	for doctype in ("Sales Taxes and Charges Template", "Purchase Taxes and Charges Template"):
		template = frappe.db.get_value(doctype, {"company": company, "title": "UAE VAT 5%"})
		if template and not ready.ruled(company, doctype, template):
			ready.charge(company, doctype, template)
	settings = frappe.get_single("Projects Settings")
	if not settings.get("one_retention"):
		settings.one_retention = 1
		settings.flags.ignore_permissions = True
		settings.save()
	from onedesk.one_project import retention

	retention.ready()
	if vat.in_uae(company):
		if not vat.settled_accounts(company):
			vat.uae_accounts(company)
		if not vat.company_address(company):
			vat.add_address(company, "Abu Dhabi", "Abu Dhabi", "Abu Dhabi")


def groups():
	for name in SUPPLIER_GROUPS:
		if not frappe.db.exists("Supplier Group", name):
			frappe.get_doc(
				{
					"doctype": "Supplier Group",
					"supplier_group_name": name,
					"parent_supplier_group": "All Supplier Groups",
				}
			).insert(ignore_permissions=True)


def _uom(name):
	if not frappe.db.exists("UOM", name):
		frappe.get_doc({"doctype": "UOM", "uom_name": name}).insert(ignore_permissions=True)
	return name


def item(code, uom="Nos", group="Products", measured_by=None, stock=0, description=None):
	"""An item by its name, made when missing. Nothing Rua buys or sells is
	kept in stock: it goes to a project as it comes."""
	if frappe.db.exists("Item", code):
		return code
	if not frappe.db.exists("Item Group", group):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": group, "parent_item_group": "All Item Groups"}
		).insert(ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": code[:140],
			"description": description or code,
			"item_group": group,
			"stock_uom": _uom(uom),
			"is_stock_item": stock,
			"include_item_in_manufacturing": 0,
		}
	)
	if measured_by and doc.meta.has_field("one_measured_by"):
		doc.one_measured_by = measured_by
	doc.insert(ignore_permissions=True)
	return code


def items(company):
	for code, uom, measured_by in PRODUCTS:
		item(code, uom, "Products", measured_by)
	expense = frappe.db.get_value(
		"Account", {"company": company, "account_name": "Miscellaneous Expenses", "is_group": 0}
	)
	code = item(SITE_EXPENSE, "Nos", "Services")
	if expense and not frappe.db.exists("Item Default", {"parent": code, "company": company}):
		doc = frappe.get_doc("Item", code)
		doc.append("item_defaults", {"company": company, "expense_account": expense})
		doc.save(ignore_permissions=True)


def terms():
	"""The headings the old quotations were written under, for each new one
	to fill in."""
	if frappe.db.exists("Terms and Conditions", TERMS):
		return
	body = "".join(f"<h4>{heading}</h4><p></p>" for heading in SECTIONS)
	frappe.get_doc(
		{"doctype": "Terms and Conditions", "title": TERMS, "terms": body, "selling": 1, "buying": 0}
	).insert(ignore_permissions=True)


def _component(name, abbr, kind):
	if not frappe.db.exists("Salary Component", name):
		frappe.get_doc(
			{
				"doctype": "Salary Component",
				"salary_component": name,
				"salary_component_abbr": abbr,
				"type": kind,
			}
		).insert(ignore_permissions=True)


def pay(company):
	"""Basic and allowance, as the old app paid them, and a day off without
	leave taking a thirtieth of each whatever the month's length."""
	payable(company)
	if frappe.db.exists("Salary Structure", STRUCTURE):
		return
	_component(BASIC, "B", "Earning")
	_component(ALLOWANCE, "AL", "Earning")
	short = "(total_working_days - payment_days)"
	doc = frappe.get_doc(
		{
			"doctype": "Salary Structure",
			"name": STRUCTURE,
			"__newname": STRUCTURE,
			"company": company,
			"payroll_frequency": "Monthly",
			"currency": frappe.db.get_value("Company", company, "default_currency"),
			"is_active": "Yes",
			"earnings": [
				{
					"salary_component": BASIC,
					"abbr": "B",
					"amount_based_on_formula": 1,
					"formula": f"base - base / 30 * {short}",
					"depends_on_payment_days": 0,
				},
				{
					"salary_component": ALLOWANCE,
					"abbr": "AL",
					"amount_based_on_formula": 1,
					"formula": f"variable - variable / 30 * {short}",
					"depends_on_payment_days": 0,
				},
			],
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()


def payable(company):
	"""Where pay owed is booked until it is paid: the UAE chart has none."""
	if frappe.db.get_value("Company", company, "default_payroll_payable_account"):
		return
	account = frappe.db.get_value(
		"Account", {"company": company, "account_name": "Payroll Payable", "is_group": 0}
	)
	if not account:
		parent = frappe.db.get_value(
			"Account", {"company": company, "account_name": "Current Liabilities", "is_group": 1}
		) or frappe.db.get_value("Account", {"company": company, "root_type": "Liability", "is_group": 1})
		account = (
			frappe.get_doc(
				{
					"doctype": "Account",
					"account_name": "Payroll Payable",
					"company": company,
					"parent_account": parent,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	frappe.db.set_value("Company", company, "default_payroll_payable_account", account)
