"""The lists everything else names: customers and suppliers, in their own
currencies, with the people to talk to and where they are; the items Sahara
buys, makes, sells and owns; what they cost and sell for; and what an hour
of each kind of work costs and bills at."""

import frappe

from onedesk.one_demo.base import ABBR, COMPANY, make, tag, wh

CUSTOMERS = (
	("Mansour & Sons", "Commercial", "Company", "AED", "Dubai", ("Khalid", "Mansour", "khalid@mansour.example", "+971501112233"), "Dubai"),
	("Bayview Developments", "Commercial", "Company", "AED", "Dubai", ("Hessa", "Al Marri", "hessa@bayview.example", "+971502223344"), "Dubai"),
	("Acme Holdings", "Commercial", "Company", "USD", "Rest Of The World", ("Jordan", "Blake", "jordan@acme.example", "+12125550147"), "New York"),
	("Marina Hotels Group", "Commercial", "Company", "AED", "Dubai", ("Rashid", "Saeed", "rashid@marinahotels.example", "+971503334455"), "Dubai"),
	("Nordlicht GmbH", "Commercial", "Company", "EUR", "Rest Of The World", ("Lena", "Vogt", "lena@nordlicht.example", "+4930555012"), "Berlin"),
	("Gulf Properties REIT", "Commercial", "Company", "AED", "Abu Dhabi", ("Saif", "Al Nuaimi", "saif@gulfprop.example", "+971504445566"), "Abu Dhabi"),
	("Aisha Rahman", "Individual", "Individual", "AED", "Dubai", ("Aisha", "Rahman", "aisha.rahman@example.com", "+971505556677"), "Dubai"),
	("Palm Interiors", "Commercial", "Company", "AED", "Dubai", ("Grace", "Lim", "grace@palminteriors.example", "+971506667788"), "Dubai"),
	("Crescent Schools", "Commercial", "Company", "AED", "Sharjah", ("Mona", "Darwish", "mona@crescent.example", "+971507778899"), "Sharjah"),
	("Harbour Logistics", "Commercial", "Company", "GBP", "Rest Of The World", ("Tom", "Archer", "tom@harbour.example", "+442075550188"), "London"),
)

TRNS = {
	"Mansour & Sons": "100345678900003",
	"Bayview Developments": "100456789000003",
	"Marina Hotels Group": "100567890100003",
	"Gulf Properties REIT": "100678901200003",
	"Palm Interiors": "100789012300003",
	"Crescent Schools": "100890123400003",
}

SUPPLIERS = (
	("Al Noor Aluminium", "Raw Material", "AED", ("Faisal", "Noor", "sales@alnoor.example")),
	("Gulf Glass Industries", "Raw Material", "AED", ("Priya", "Nair", "orders@gulfglass.example")),
	("Euro Hardware Trading", "Hardware", "EUR", ("Marco", "Bianchi", "marco@eurohardware.example")),
	("Precision Installers", "Services", "AED", ("Hamza", "Qureshi", "hamza@precision.example")),
	("Rapid Scaffolding", "Services", "AED", ("Vikram", "Singh", "hire@rapidscaffold.example")),
	("Desert Logistics", "Services", "AED", ("Amal", "Fares", "dispatch@desertlog.example")),
	("Gulf Office Supplies", "Local", "AED", ("Sara", "Ali", "sara@gulfoffice.example")),
	("Emirates Fleet Motors", "Local", "AED", ("Ahmed", "Yousuf", "fleet@efm.example")),
	("CNC Machines Europe", "Hardware", "EUR", ("Jan", "Kowalski", "jan@cnceurope.example")),
	("Emirates Sealants & Fixings", "Hardware", "AED", ("Rami", "Haddad", "sales@emiratessealants.example")),
	("Gulf Powder Coating", "Services", "AED", ("Kareem", "Saeed", "jobs@gulfpowder.example")),
)

ITEMS = (
	("ALU-6063", "Aluminium Profile 6063", "Raw Material", "Meter", "stock", 28, None, 400),
	("GLS-DGU", "Double Glazed Unit 24mm", "Raw Material", "Square Meter", "stock", 165, None, 60),
	("GLS-TMP10", "Tempered Glass 10mm", "Raw Material", "Square Meter", "stock", 120, None, 40),
	("HW-HINGE", "Concealed Hinge", "Hardware", "Nos", "stock", 38, None, 100),
	("HW-HANDLE", "Window Handle", "Hardware", "Nos", "stock", 24, None, 80),
	("HW-LOCK", "Multipoint Lock", "Hardware", "Nos", "stock", 95, None, 30),
	("SEAL-EPDM", "EPDM Gasket", "Raw Material", "Meter", "stock", 4.5, None, 500),
	("SIL-CLR", "Structural Silicone", "Consumable", "Nos", "stock", 32, None, 60),
	("FIX-ANCH", "Wall Anchor Set", "Consumable", "Nos", "stock", 6, None, 300),
	("WIN-CS12", "Casement Window 1200", "Products", "Nos", "made", None, 2400, 0),
	("DR-SL24", "Sliding Door 2400", "Products", "Nos", "made", None, 6800, 0),
	("BAL-GL", "Glass Balustrade", "Products", "Meter", "made", None, 1450, 0),
	("ALU-6063-PC", "Aluminium Profile 6063, Powder Coated", "Raw Material", "Meter", "coated", None, None, 0),
	("SVC-PCOAT", "Powder Coating", "Services", "Meter", "service", 4.5, None, 0),
	("SVC-INST", "Installation", "Services", "Hour", "service", None, 180, 0),
	("SVC-DES", "Design", "Services", "Hour", "service", None, 320, 0),
	("SVC-SURV", "Site Survey", "Services", "Nos", "service", None, 900, 0),
	("SVC-MAINT", "Glazing Maintenance Visit", "Services", "Nos", "service", None, 1500, 0),
	("SVC-SUB", "Subcontract Installation", "Services", "Lump Sum", "service", 0, None, 0),
	("SVC-SCAF", "Scaffolding Hire", "Services", "Nos", "service", 2200, None, 0),
	("SVC-TRANS", "Transport", "Services", "Nos", "service", 650, None, 0),
	("SVC-VREP", "Vehicle Repair", "Services", "Nos", "service", None, None, 0),
	("OFF-SUP", "Office Supplies", "Consumable", "Nos", "service", 150, None, 0),
	("VEH-PICKUP", "Pickup Truck", "Fixed Assets", "Nos", "asset", 145000, None, 0),
	("MCH-CNC", "CNC Profile Machining Centre", "Fixed Assets", "Nos", "asset", 520000, None, 0),
	("IT-LAPTOP", "Laptop", "Fixed Assets", "Nos", "asset", 6500, None, 0),
)

ACTIVITIES = (
	("Design", 110, 320),
	("Site Survey", 90, 260),
	("Fabrication", 60, 180),
	("Installation", 55, 180),
	("Project Management", 140, 350),
	("Maintenance", 55, 200),
	("Site Work", 55, 180),
)


def run(password=None):
	for group in ("Commercial", "Individual"):
		if not frappe.db.exists("Customer Group", group):
			make({"doctype": "Customer Group", "customer_group_name": group, "parent_customer_group": "All Customer Groups"})
	for territory, parent in (("Dubai", "United Arab Emirates"), ("Abu Dhabi", "United Arab Emirates"), ("Sharjah", "United Arab Emirates"), ("Rest Of The World", "All Territories")):
		if not frappe.db.exists("Territory", parent):
			make({"doctype": "Territory", "territory_name": parent, "parent_territory": "All Territories", "is_group": 1})
		elif not frappe.db.get_value("Territory", parent, "is_group"):
			frappe.db.set_value("Territory", parent, "is_group", 1)
		if not frappe.db.exists("Territory", territory):
			make({"doctype": "Territory", "territory_name": territory, "parent_territory": parent})
	for group in ("Raw Material", "Hardware", "Services", "Local"):
		if not frappe.db.exists("Supplier Group", group):
			make({"doctype": "Supplier Group", "supplier_group_name": group, "parent_supplier_group": "All Supplier Groups"})
	for group in ("Raw Material", "Hardware", "Consumable", "Products", "Services", "Fixed Assets"):
		if not frappe.db.exists("Item Group", group):
			make({"doctype": "Item Group", "item_group_name": group, "parent_item_group": "All Item Groups"})
	for uom in ("Meter", "Square Meter", "Hour", "Nos"):
		if not frappe.db.exists("UOM", uom):
			make({"doctype": "UOM", "uom_name": uom})

	for name, group, kind, currency, territory, person, city in CUSTOMERS:
		if frappe.db.exists("Customer", name):
			if currency != "AED":
				_party_account("Customer", frappe.get_doc("Customer", name), currency)
			continue
		customer = make(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": group,
				"customer_type": kind,
				"territory": territory,
				"default_currency": currency,
				"tax_id": TRNS.get(name),
			}
		)
		_contact(person, "Customer", customer.name)
		_address(customer.name, "Customer", city)
		if currency != "AED":
			_party_account("Customer", customer, currency)

	for name, group, currency, person in SUPPLIERS:
		if frappe.db.exists("Supplier", name):
			if currency != "AED":
				_party_account("Supplier", frappe.get_doc("Supplier", name), currency)
			continue
		supplier = make(
			{"doctype": "Supplier", "supplier_name": name, "supplier_group": group, "default_currency": currency, "country": ABROAD.get(name, "United Arab Emirates")}
		)
		_contact((*person, None), "Supplier", supplier.name)
		if currency != "AED":
			_party_account("Supplier", supplier, currency)

	_asset_categories()
	for code, name, group, uom, kind, buy, sell, reorder in ITEMS:
		if frappe.db.exists("Item", code):
			continue
		values = {
			"doctype": "Item",
			"item_code": code,
			"item_name": name,
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": int(kind in ("stock", "made", "coated")),
			"include_item_in_manufacturing": int(kind in ("stock", "coated")),
			"is_sub_contracted_item": int(kind == "coated"),
			"is_sales_item": int(bool(sell)),
			"is_purchase_item": int(kind not in ("made", "coated")),
			"is_fixed_asset": int(kind == "asset"),
			"valuation_rate": buy or (sell or 0) * 0.45,
			"standard_rate": sell or 0,
		}
		if kind == "asset":
			values.update({"is_stock_item": 0, "asset_category": "Vehicles" if code == "VEH-PICKUP" else "Machinery" if code == "MCH-CNC" else "IT Equipment"})
		if kind == "made":
			values["default_bom"] = None
		if reorder:
			values["reorder_levels"] = [
				{"warehouse": wh("Stores"), "warehouse_reorder_level": reorder, "warehouse_reorder_qty": reorder * 2, "material_request_type": "Purchase"}
			]
		item = make(values)
		for price_list, rate in (("Standard Buying", buy), ("Standard Selling", sell)):
			if rate and not frappe.db.exists("Item Price", {"item_code": item.name, "price_list": price_list}):
				make({"doctype": "Item Price", "item_code": item.name, "price_list": price_list, "price_list_rate": rate})

	for name, cost, bills in ACTIVITIES:
		if not frappe.db.exists("Activity Type", name):
			make({"doctype": "Activity Type", "activity_type": name, "costing_rate": cost, "billing_rate": bills})

	_vat()
	_uae()


def _uae():
	"""The UAE return's two Books Check items, done before the first sale so
	every invoice carries the company's emirate (one_book/vat.py): the VAT
	accounts the return reads, and the company's address in Dubai."""
	from onedesk.one_book import ready, vat

	if not vat.settled_accounts(COMPANY):
		ready.fix("uae_vat")
	address = vat.company_address(COMPANY)
	if not (address and frappe.db.get_value("Address", address, "emirate")):
		ready.fix("emirate", emirate="Dubai", address_line1="Warehouse 14, Al Quoz Industrial Area 3", city="Dubai")


ABROAD = {"Euro Hardware Trading": "Italy", "CNC Machines Europe": "Poland"}

EXPORTS = ("United States", "Germany", "United Kingdom")


def _vat():
	"""VAT as the accounts team sets it up before the first sale. The Books
	Check charges 5% on every invoice and bill however it is made
	(one_book/ready.py), and a Tax Rule for each country abroad, and for each
	supplier abroad, outranks it with nothing charged."""
	from onedesk.one_book import ready

	if frappe.db.exists("Tax Rule", {"company": COMPANY}):
		return
	ready.fix("template_taxes")
	ready.fix("sales_tax", template=f"UAE VAT 5% - {ABBR}")
	ready.fix("purchase_tax", template=f"UAE VAT 5% - {ABBR}")
	zero = f"UAE VAT Zero - {ABBR}"
	for country in EXPORTS:
		make({"doctype": "Tax Rule", "company": COMPANY, "tax_type": "Sales", "billing_country": country, "sales_tax_template": zero, "priority": 2})
	for supplier in ABROAD:
		make({"doctype": "Tax Rule", "company": COMPANY, "tax_type": "Purchase", "supplier": supplier, "purchase_tax_template": zero, "priority": 2})


def _contact(person, doctype, name):
	first, last, email, phone = person
	contact = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": first,
			"last_name": last,
			"email_ids": [{"email_id": email, "is_primary": 1}],
			"phone_nos": [{"phone": phone, "is_primary_mobile_no": 1}] if phone else [],
			"links": [{"link_doctype": doctype, "link_name": name}],
		}
	)
	contact.insert()
	tag(contact)
	frappe.db.set_value(doctype, name, f"{doctype.lower()}_primary_contact", contact.name)


STREETS = {
	"Dubai": ("Business Bay", None),
	"Abu Dhabi": ("Al Reem Island", None),
	"Sharjah": ("Al Majaz", None),
	"Berlin": ("Friedrichstraße", "10117"),
	"New York": ("Park Avenue", "10022"),
	"London": ("Old Street", "EC1V 9HL"),
}


def _address(name, doctype, city):
	street, postcode = STREETS[city]
	make(
		{
			"doctype": "Address",
			"address_title": name,
			"address_type": "Billing",
			"address_line1": f"{street} {len(name) * 7}" if city == "Berlin" else f"{len(name) * 7} {street}",
			"city": city,
			"pincode": postcode,
			"country": "United Arab Emirates" if city in ("Dubai", "Abu Dhabi", "Sharjah") else "United States" if city == "New York" else "Germany" if city == "Berlin" else "United Kingdom",
			"is_primary_address": 1,
			"links": [{"link_doctype": doctype, "link_name": name}],
		}
	)


def _party_account(doctype, party, currency):
	"""A receivable or payable account in the party's own currency, as ERPNext
	wants for a party billed in another one."""
	kind = "Receivable" if doctype == "Customer" else "Payable"
	parent = frappe.db.get_value("Account", {"company": COMPANY, "account_type": kind, "is_group": 0}, "parent_account")
	name = f"{'Debtors' if kind == 'Receivable' else 'Creditors'} {currency}"
	account = frappe.db.get_value("Account", {"company": COMPANY, "account_name": name})
	if not account:
		account = make(
			{
				"doctype": "Account",
				"account_name": name,
				"parent_account": parent,
				"company": COMPANY,
				"account_type": kind,
				"account_currency": currency,
			}
		).name
	party.reload()
	if any(row.company == COMPANY for row in party.get("accounts")):
		return
	party.append("accounts", {"company": COMPANY, "account": account})
	party.save()


def _asset_categories():
	fixed = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Fixed Asset", "is_group": 0}, "name")
	depreciation = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Accumulated Depreciation", "is_group": 0}, "name")
	expense = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Depreciation", "is_group": 0}, "name")
	for name, years in (("Vehicles", 5), ("Machinery", 10), ("IT Equipment", 3)):
		if frappe.db.exists("Asset Category", name):
			continue
		make(
			{
				"doctype": "Asset Category",
				"asset_category_name": name,
				"accounts": [
					{
						"company_name": COMPANY,
						"fixed_asset_account": fixed,
						"accumulated_depreciation_account": depreciation,
						"depreciation_expense_account": expense,
					}
				],
				"finance_books": [
					{"depreciation_method": "Straight Line", "total_number_of_depreciations": years * 12, "frequency_of_depreciation": 1}
				],
			}
		)
