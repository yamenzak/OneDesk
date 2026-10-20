"""Rua Company's workspace, set the way the old app worked: its years from
2023, its supplier kinds, its products, its quotation sections and its pay.

Everything here is idempotent: it runs on install and again before every
import, and a thing already there is left as it is.
"""

import json

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

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
	store(company)
	costing()
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
	"""An item by its name, made when missing. Only profiles and accessories
	are kept in stock (store); the rest goes to a project as it comes."""
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


#: Kept in stock: profiles by the bar, accessories by the metre or the piece.
#: Everything else Rua buys goes to a project as it comes.
STOCKED = ("Profiles", "Accessories")
STORE = "Store"


def store(company):
	"""Rua's one store, the two groups kept in it, and the units they're
	counted in. A profile is kept in metres and bought and issued by the
	bar, each with its own length (profile), so a cut piece can come back."""
	for unit in ("Bar", "Meter", "Nos"):
		_uom(unit)
	warehouse = frappe.db.get_value("Warehouse", {"warehouse_name": STORE, "company": company})
	if not warehouse:
		warehouse = (
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": STORE,
					"company": company,
					"parent_warehouse": frappe.db.get_value(
						"Warehouse", {"company": company, "is_group": 1, "parent_warehouse": ["in", ["", None]]}
					),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	for name in STOCKED:
		if not frappe.db.exists("Item Group", name):
			frappe.get_doc(
				{"doctype": "Item Group", "item_group_name": name, "parent_item_group": "All Item Groups"}
			).insert(ignore_permissions=True)
		group = frappe.get_doc("Item Group", name)
		if not any(one.company == company for one in group.item_group_defaults):
			group.append("item_group_defaults", {"company": company, "default_warehouse": warehouse})
			group.save(ignore_permissions=True)
	return warehouse


def profile(code, description, bar_length):
	"""A profile: kept in metres, bought and issued by the bar of its length."""
	code = item(code, "Meter", "Profiles", stock=1, description=description)
	doc = frappe.get_doc("Item", code)
	doc.purchase_uom = _uom("Bar")
	doc.set("uoms", [one for one in doc.uoms if one.uom != "Bar"])
	doc.append("uoms", {"uom": "Bar", "conversion_factor": flt(bar_length)})
	doc.save(ignore_permissions=True)
	return code


def accessory(code, description, uom="Nos"):
	"""An accessory: rubber by the metre, the rest by the piece."""
	return item(code, uom, "Accessories", stock=1, description=description)


COSTING_LINES = 100
#: Rua's costing sheets, one a family of aluminium systems, each a template
#: for a quotation's items laid out under the company's brand
#: (one_sheet/style.branded): the header, the formulas on every line, the
#: totals. Nothing a job types (a line's item, sizes, prices, kilos) is in a
#: template. `scale` turns a size into millimetres; `kinds` says which
#: columns hold money, counts, sizes, areas and kilos, which are the key
#: figures and which is wide.
COSTINGS = (
	{
		"title": "Costing (Alumil, Gutmann, Technal)",
		"was": "Rua Costing",
		"scale": 1,
		"head": (
			"ITEM", "DESCRIPTION", "QTY", "WIDTH (mm)", "HEIGHT (mm)", "AREA (sqm)", "GLASS UNIT", "GLASS PRICE",
			"TOTAL GLASS", "ALU UNIT", "TOTAL ALU", "ACT UNIT", "PROFIT 74%", "UNIT RATE", "RATE", "OVERALL PRICE",
			None, None, "CW", "INSERTION", "EXTRA", "ALUMIL PRICE", "VAT 5%", "TOTAL", "ALL PRICE inc PC and VAT",
		),
		# Area, glass by the square metre, Alumil's price with insertion and
		# extras, VAT, 74% profit, and the rate rounded up to 5.
		"line": {
			"F": "=(D{r}*E{r})/1000000", "H": "=G{r}*F{r}", "I": "=H{r}*C{r}", "J": "=Y{r}", "K": "=J{r}*C{r}",
			"L": "=H{r}+J{r}", "M": "=L{r}*0.74", "N": "=L{r}+M{r}", "O": "=CEILING(N{r},5)", "P": "=O{r}*C{r}", "R": "=A{r}",
			"V": "=S{r}+T{r}+U{r}", "W": "=V{r}*1.05", "X": "=W{r}*C{r}", "Y": "=W{r}*1.13",
		},
		"totals": {"O": "TOTAL", "P": "=SUM(P{first}:P{last})"},
		"kinds": {"money": "GHIJKLMNOPSTUVWXY", "count": "C", "size": "DE", "area": "F", "key": "OP", "wide": "B"},
	},
	{
		"title": "Costing (Gulf Extrusion)",
		"scale": 10,
		"head": (
			"Item", "Description", "Qty", "Width (CM)", "Height (CM)", "Area (sqm)", "GLASS UNIT", "GLASS PRICE",
			"TOTAL GLASS", "ALU UNIT", "TOTAL ALU", "ACT UNIT", "PROFIT 35%", "UNIT RATE", "PRICE", "Overall Price",
			None, "Powder KG", "Mill KG", "Accs.", "ALU UNIT PR", "ALU TOTAL",
		),
		# Area from centimetres, glass by the square metre, the aluminium from
		# its weight (powder coated at 24 a kilo, mill finish at 19) and its
		# accessories, and 35% profit. O starts at the unit rate; the
		# estimator types the price over it.
		"line": {
			"F": "=(D{r}*E{r})/10000", "H": "=F{r}*G{r}", "I": "=H{r}*C{r}", "J": "=U{r}", "K": "=J{r}*C{r}",
			"L": "=H{r}+J{r}", "M": "=L{r}*0.35", "N": "=L{r}+M{r}", "O": "=N{r}", "P": "=O{r}*C{r}",
			"U": "=(R{r}*24)+(S{r}*19)+T{r}", "V": "=U{r}*C{r}",
		},
		"totals": {
			"A": "GRAND TOTALS", "C": "=SUM(C{first}:C{last})", "I": "=SUM(I{first}:I{last})", "K": "=SUM(K{first}:K{last})",
			"M": "=SUM(M{first}:M{last})", "P": "=SUM(P{first}:P{last})", "V": "=SUM(V{first}:V{last})",
		},
		"kinds": {"money": "GHIJKLMNOPTUV", "count": "C", "size": "DE", "area": "F", "kilos": "RS", "key": "OP", "wide": "B"},
	},
)
#: Which product a line is, read from its description: the first that fits,
#: "+" joining words that must all be there.
KINDS = (
	("louv", "Louver"), ("composite", "ACP Cladding"), ("cladding", "ACP Cladding"), ("acp", "ACP Cladding"),
	("steel+handrail", "Steel Handrail"), ("handrail", "Glass Handrail"), ("curtain", "Curtain Wall"),
	("window", "Window"), ("door", "Door"), ("skylight", "Skylight"), ("shower", "Shower Partition"),
)


def kind(description) -> str:
	"""The product a description is, by KINDS. Pure."""
	said = (description or "").lower()
	return next((product for words, product in KINDS if all(one in said for one in words.split("+"))), "Aluminium Works")


def kind_formula(first: int = 6) -> str:
	"""KINDS as one formula over the Costing sheet's descriptions, the
	product of each line it fills down. Pure."""
	said = '"Aluminium Works"'
	for words, product in reversed(KINDS):
		test = "*".join(f'ISNUMBER(SEARCH("{one}",Costing!B{first}:B))' for one in words.split("+"))
		said = f'IF({test},"{product}",{said})'
	return f'=IF(Costing!A{first}:A="","",{said})'


def costing_items(first: int = 6, scale: int = 1) -> dict:
	"""The quotation's items, each column one formula that fills it down
	from the Costing sheet, a line for each line with an ITEM. The rate is
	the line's overall price over its quantity: O is a unit rate on a
	curtain wall's line but the whole price on a cladding or handrail line,
	where P is just O. Pure."""
	key = f'=IF(Costing!A{first}:A="","",'
	size = f"*{scale}" if scale != 1 else ""
	return {
		"item_code": kind_formula(first),
		"item_name": f"=Costing!A{first}:A",
		"description": f"{key}Costing!B{first}:B)",
		"qty": f"{key}Costing!C{first}:C)",
		"one_length": f'{key}IF(ISNUMBER(Costing!D{first}:D),Costing!D{first}:D{size},""))',
		"one_width": f'{key}IF(ISNUMBER(Costing!E{first}:E),Costing!E{first}:E{size},""))',
		"rate": f"{key}Costing!P{first}:P/Costing!C{first}:C)",
	}


#: What each costing sheet shows of the quotation it is for, beside the brand.
COSTING_META = (
	("Quotation", '=RECORD("name")'),
	("Customer", '=RECORD("customer_name")'),
	("Date", '=RECORD("transaction_date")'),
	("Valid Till", '=RECORD("valid_till")'),
	("Currency", '=RECORD("currency")'),
	("Status", '=RECORD("status")'),
)


def costing_sheet(spec: dict, colour: str, currency: str) -> dict:
	"""A costing sheet laid out under the company's brand. Pure but for the
	labels' translation."""
	from onedesk.one_sheet import style

	meta = [(_(label), formula) for label, formula in COSTING_META]
	return style.branded(spec["title"], list(spec["head"]), spec["line"], spec["totals"], spec["kinds"], colour, currency, meta, COSTING_LINES)


def costing():
	"""Rua's costing sheets as templates for a quotation's items: the
	estimators' columns under the company's brand, a curtain wall's formulas
	on every line, and the items sheet whose formulas read it. One already
	there and laid out is left as it is, so what somebody changed in it
	stays; one made under its old name or before it was laid out is made
	again in place."""
	from onedesk.one_sheet import api, storage, style, table, templates

	brand = style.brand()
	for spec in COSTINGS:
		held = frappe.db.get_value(
			api.WORKBOOK, {"is_template": 1, "title": ["in", [spec["title"], spec.get("was") or spec["title"]]]}, ["name", "title", "file", "sheets_data"], as_dict=True
		)
		if held and held.title == spec["title"] and "Costing" in (json.loads(storage.decode_sheets_data(held.sheets_data) or "{}").get("formats") or {}):
			continue
		said = costing_items(style.FIRST, spec["scale"])
		cols = table.columns([one.as_dict() for one in frappe.get_meta("Quotation Item").fields], list(said))
		sheet = _("Items")
		lines = {"0": [table.MARK] + [col["header"] for col in cols[1:]], "1": [None] + [said.get(col["fieldname"]) for col in cols[1:]]}
		laid = costing_sheet(spec, brand["colour"], brand["currency"])
		look = style.table(cols, brand["colour"], brand["currency"], style.precisions())
		data = {
			"sheet": {"v": 2, "current": "Costing", "sheets": {sheet: {"rows": lines}, "Costing": {"rows": laid["rows"]}}},
			"formats": {"Costing": laid["formats"], sheet: look["formats"]},
			"merge": {"Costing": laid["merge"]},
			"view": {"Costing": laid["view"], sheet: {"colW": look["colW"], "rowH": look["rowH"], "freezeRows": 1, "hiddenCols": [0]}},
		}
		if not held:
			templates.make(spec["title"], data, "Quotation", "items", sheet, cols)
			continue
		frappe.db.set_value(
			api.WORKBOOK,
			held.name,
			{"title": spec["title"], "sheets_data": storage.encode_sheets_data(json.dumps(data)), "bound_sheet": sheet, "bound_columns": json.dumps(cols)},
		)
		if held.file:
			frappe.db.set_value("File", held.file, "file_name", spec["title"])


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
