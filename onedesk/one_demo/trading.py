"""Creek Trading, the group's trading company in Deira: it imports office
chairs and desks from Shenzhen in dollars, buys paper, toner and cabinets in
Dubai, keeps them in its stores and sells them to offices, schools, hotels
and clinics. Most sales leave the stores on their invoice; a school's big
order is delivered first and invoiced on delivery."""

import frappe
from frappe.utils import add_days

from onedesk.one_book.currency import bill_in
from onedesk.one_demo import firm, trading_field
from onedesk.one_demo.base import as_user, dated, on, once, save
from onedesk.one_demo.firm import Firm, Person

FIRM = Firm(
	name=trading_field.COMPANY,
	abbr="CRT",
	field=trading_field.TRADING.id,
	emirate="Dubai",
	street="Warehouse 7, Al Ras, Deira",
	phone="+971 4 226 5401",
	email="sales@creektrading.test",
	website="creektrading.test",
	tax_id="100734567800003",
	bank="RAKBANK",
	iban="AE140400378812093340002",
	sales_tax="UAE VAT 5%",
	opening=650000,
	people=(
		Person("Vikram", "Rao", "vikram@one.test", "Management", "General Manager", "Male", "2019-11-10", 22000, (("one_inventory", "Manager"), ("one_book", "Manager"), ("one_crm", "Manager"), ("one_portal", "User"))),
		Person("Lina", "Aziz", "lina@one.test", "Sales", "Sales Coordinator", "Female", "2022-03-07", 9000, (("one_crm", "User"), ("one_inventory", "User"), ("one_book", "User"))),
		Person("Suresh", "Pillai", None, "Dispatch", "Storekeeper", "Male", "2020-08-16", 5500),
		Person("Iqbal", "Hussain", None, "Dispatch", "Driver", "Male", "2021-12-01", 4000),
	),
)

MANAGER = "vikram@one.test"
SALES = "lina@one.test"

ITEMS = (
	("CRT-CHR", "Ergonomic Office Chair", "Office Furniture", "Nos", 690, True),
	("CRT-DSK", "Office Desk 1600", "Office Furniture", "Nos", 1250, True),
	("CRT-CAB", "Steel Filing Cabinet, 4 Drawers", "Office Furniture", "Nos", 880, True),
	("CRT-A4", "A4 Copy Paper, Box of 5 Reams", "Office Supplies", "Box", 95, True),
	("CRT-TNR", "Laser Toner Cartridge", "Office Supplies", "Nos", 340, True),
	("CRT-FRT", "Freight and Clearing", "Office Supplies", "Nos", 0, False),
)

CUSTOMERS = (
	("Emirates Co-working Spaces", "accounts@emiratescowork.example", "+97144550101", ("Yara", "Nassar")),
	("Nexa Telecom FZ-LLC", "procurement@nexatelecom.example", "+97143360202", ("Stefan", "Ilic")),
	("Al Wasl Schools Group", "purchasing@alwaslschools.example", "+97143470303", ("Mona", "Saber")),
	("Harbour View Hotels", "stores@harbourviewhotels.example", "+97143580404", ("Liam", "Gallagher")),
	("Desert Rose Clinics", "admin@desertroseclinics.example", "+97143690505", ("Rasha", "Odeh")),
)

SUPPLIERS = (
	("Shenzhen Ergo Furniture Co.", "Raw Material", "export@szergo.example", ("Li", "Wei"), "USD", "China"),
	("Gulf Paper Mills", "Local", "orders@gulfpaper.example", ("Sanjeev", "Kapoor"), "AED", "United Arab Emirates"),
	("Deira Office Systems", "Local", "trade@deiraoffice.example", ("Faris", "Haddad"), "AED", "United Arab Emirates"),
	("Express Freight Services", "Services", "billing@expressfreight.example", ("Nikhil", "Das"), "AED", "United Arab Emirates"),
)

BOUGHT = (
	("Shenzhen Ergo Furniture Co.", (1, 12), "SEF-0091", (("CRT-CHR", 360, 95), ("CRT-DSK", 120, 180)), 60, (3, 5), 1.0),
	("Gulf Paper Mills", (2, 3), "GPM-3301", (("CRT-A4", 1200, 58),), 30, (3, 1), 1.0),
	("Deira Office Systems", (2, 18), "DOS-1187", (("CRT-TNR", 450, 210), ("CRT-CAB", 90, 520)), 30, (3, 20), 1.0),
	("Shenzhen Ergo Furniture Co.", (5, 20), "SEF-0127", (("CRT-CHR", 450, 97), ("CRT-DSK", 180, 182)), 60, (7, 22), 1.0),
	("Gulf Paper Mills", (6, 10), "GPM-3478", (("CRT-A4", 1500, 59),), 30, (7, 10), 1.0),
	("Deira Office Systems", (8, 25), "DOS-1290", (("CRT-TNR", 360, 212), ("CRT-CAB", 75, 525)), 30, (9, 25), 0.5),
	("Shenzhen Ergo Furniture Co.", (10, 1), "SEF-0163", (("CRT-CHR", 300, 98),), 60, None, 0),
)
"""(supplier, day, their bill's number, lines, days to pay, paid on, part paid)"""

FREIGHT = (((1, 28), "EFS-1102", 6800), ((6, 8), "EFS-1288", 8200), ((10, 18), "EFS-1411", 5600))
"""The shipments from Shenzhen cleared and trucked to the stores."""

SOLD = (
	("Emirates Co-working Spaces", (1, 25), (("CRT-CHR", 120, 690), ("CRT-DSK", 45, 1250)), (2, 20), 1.0),
	("Nexa Telecom FZ-LLC", (2, 24), (("CRT-A4", 360, 95), ("CRT-TNR", 90, 340)), (3, 24), 1.0),
	("Desert Rose Clinics", (2, 26), (("CRT-CHR", 40, 690), ("CRT-TNR", 30, 340)), (3, 26), 1.0),
	("Al Wasl Schools Group", (3, 6), (("CRT-CAB", 54, 880), ("CRT-A4", 240, 95)), (4, 5), 1.0),
	("Harbour View Hotels", (3, 28), (("CRT-CHR", 90, 690),), (4, 30), 1.0),
	("Nexa Telecom FZ-LLC", (4, 16), (("CRT-A4", 300, 95), ("CRT-TNR", 105, 340)), (5, 15), 1.0),
	("Emirates Co-working Spaces", (5, 12), (("CRT-DSK", 60, 1250), ("CRT-CHR", 75, 690)), (6, 10), 1.0),
	("Harbour View Hotels", (5, 27), (("CRT-DSK", 40, 1250), ("CRT-CHR", 80, 690)), (6, 26), 1.0),
	("Nexa Telecom FZ-LLC", (6, 15), (("CRT-CHR", 60, 690), ("CRT-DSK", 30, 1250)), (7, 15), 1.0),
	("Desert Rose Clinics", (7, 9), (("CRT-CAB", 30, 880), ("CRT-A4", 180, 95)), (8, 8), 1.0),
	("Emirates Co-working Spaces", (7, 22), (("CRT-A4", 300, 95), ("CRT-TNR", 75, 340)), (8, 20), 1.0),
	("Nexa Telecom FZ-LLC", (8, 4), (("CRT-A4", 420, 95), ("CRT-TNR", 120, 340)), (9, 3), 0.5),
	("Harbour View Hotels", (9, 2), (("CRT-CHR", 135, 690), ("CRT-DSK", 36, 1250)), None, 0),
	("Al Wasl Schools Group", (9, 29), (("CRT-A4", 450, 92), ("CRT-CAB", 36, 880)), (10, 28), 1.0),
	("Emirates Co-working Spaces", (10, 14), (("CRT-CHR", 90, 690), ("CRT-TNR", 60, 340)), None, 0),
	("Nexa Telecom FZ-LLC", (10, 30), (("CRT-A4", 360, 95), ("CRT-TNR", 90, 340)), None, 0),
)
"""(customer, day, lines, paid on, part paid), each taken from the stores on
its invoice."""

ORDERED = ("Al Wasl Schools Group", (6, 18), (6, 24), (("CRT-CHR", 180, 670), ("CRT-DSK", 75, 1200)), (8, 1))
"""The schools' new building: ordered, delivered a week on, invoiced on
delivery, at a price for the quantity."""


def run(password=None):
	bank = firm.settle(FIRM, password)
	for code, name, group, uom, price, stocked in ITEMS:
		firm.item(code, name, group, uom, price, stocked)
	for name, email, phone, contact in CUSTOMERS:
		firm.customer(name, "Company", email, phone, contact)
	for name, group, email, contact, currency, country in SUPPLIERS:
		found = firm.supplier(name, group, email, contact, FIRM, currency, country)
		if currency != "AED":
			_imported(found)
	if not frappe.db.exists("Sales Invoice", {"company": FIRM.name, "docstatus": 1}):
		_bought()
		_sold()
		_ordered()
	firm.monthly(FIRM, bank, 12000, (3400, 3300, 3600, 4100, 4900, 5800, 6400, 6600, 5900, 4800, 3900))


def _imported(supplier: str) -> None:
	"""A supplier abroad charges no UAE VAT, as the Books Check's rule for a
	country abroad outranks the 5% (one_demo/masters.py, _vat)."""
	once(
		"Tax Rule",
		{"company": FIRM.name, "tax_type": "Purchase", "supplier": supplier},
		{"company": FIRM.name, "tax_type": "Purchase", "supplier": supplier, "purchase_tax_template": f"UAE VAT Zero - {FIRM.abbr}", "priority": 2},
	)


def _bought():
	for supplier, day, number, lines, due, paid, part in BOUGHT:
		bill = firm.buy(FIRM, MANAGER, supplier, on(*day), number, lines, due=due, stock=True)
		if paid:
			firm.settled(FIRM, MANAGER, bill, on(*paid), part)
	for day, number, amount in FREIGHT:
		bill = firm.buy(FIRM, MANAGER, "Express Freight Services", on(*day), number, (("CRT-FRT", 1, amount, "Freight and Forwarding Charges"),))
		firm.settled(FIRM, MANAGER, bill, add_days(on(*day), 20))


def _sold():
	for customer, day, lines, paid, part in SOLD:
		invoice = firm.sell(FIRM, SALES, customer, on(*day), lines, stock=True)
		if paid:
			firm.settled(FIRM, MANAGER, invoice, on(*paid), part)


def _ordered():
	from erpnext.selling.doctype.sales_order.mapper import make_delivery_note
	from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice

	customer, day, delivered, lines, paid = ORDERED
	with as_user(SALES):
		order = frappe.new_doc("Sales Order")
		order.company = FIRM.name
		order.customer = customer
		dated(order, on(*day), "transaction_date")
		bill_in(order, "Customer", customer)
		order.delivery_date = on(*delivered)
		order.set_warehouse = FIRM.wh("Stores")
		for code, qty, rate in lines:
			order.append("items", {"item_code": code, "qty": qty, "rate": rate, "delivery_date": order.delivery_date, "warehouse": FIRM.wh("Stores")})
		order = save(order, submit=True)
	with as_user(MANAGER):
		note = make_delivery_note(order.name)
		dated(note, on(*delivered))
		note = save(note, submit=True)
		invoice = make_sales_invoice(note.name)
		dated(invoice, on(*delivered))
		invoice.due_date = add_days(invoice.posting_date, 30)
		for row in invoice.get("payment_schedule") or []:
			row.due_date = invoice.due_date
		invoice = save(invoice, submit=True)
	firm.settled(FIRM, MANAGER, invoice, on(*paid))
