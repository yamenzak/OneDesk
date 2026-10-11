"""Selling products, apart from the projects: orders delivered and invoiced
and paid, one in pounds, one still to deliver, a window sent back and credited,
two sample windows sent to New York in dollars, balustrades delivered and not
yet invoiced, a survey fee nobody has paid, and the villa's sliding doors held
for it while its first windows are picked, packed and sent to site."""

import frappe
from frappe.utils import add_days

from onedesk.one_book.currency import bill_in
from onedesk.one_demo.base import COMPANY, ago, ahead, as_user, dated, on, once, rated, save, today, wh

SALES = "omar@one.test"
ACCOUNTS = "huda@one.test"


STORES = "karim@one.test"
DRIVER = "yousef@one.test"


def run(password=None):
	if not frappe.db.exists("Delivery Note", {"docstatus": 1}):
		_sell()
	_to_site()


def _sell():
	with as_user(SALES):
		classrooms = _order("Crescent Schools", on(6, 2), (("WIN-CS12", 24, 2350),))
		note = _deliver(classrooms, on(6, 24))
		invoice = _invoice(note, on(6, 25))
		_return(note, invoice, "WIN-CS12", 1, on(7, 2))
		_pay(invoice.reload() or invoice, on(7, 20))

		depot = _order("Harbour Logistics", on(7, 14), (("DR-SL24", 3, 1450),))
		invoice = _invoice(_deliver(depot, on(8, 6)), on(8, 6))
		_pay(invoice, on(9, 1))

		samples = _order("Acme Holdings", on(8, 3), (("WIN-CS12", 2, 650),))
		_invoice(_deliver(samples, on(8, 20)), on(8, 20))

		_order("Marina Hotels Group", ago(18), (("BAL-GL", 30, 1420), ("SVC-INST", 40, 180)), delivery=ahead(12))

		railings = _order("Gulf Properties REIT", ago(25), (("BAL-GL", 12, 1420),))
		_deliver(railings, ago(6))

		fee = frappe.new_doc("Sales Invoice")
		fee.customer = "Palm Interiors"
		fee.company = COMPANY
		dated(fee, on(7, 3))
		bill_in(fee, "Customer", fee.customer)
		fee.due_date = add_days(fee.posting_date, 14)
		fee.append("items", {"item_code": "SVC-SURV", "qty": 1, "rate": 900})
		save(fee, submit=True)


def _to_site():
	"""Goods sent to site and stock held for an order, as the stores do it: the
	villa's first twenty-four windows are picked from Finished Goods, packed in
	three crates and put on tomorrow's trip to Al Barsha with Yousef driving,
	and its twenty sliding doors are set aside for it."""
	if frappe.db.exists("Delivery Trip", {"docstatus": 1}):
		return
	from erpnext.selling.doctype.sales_order.mapper import create_pick_list
	from erpnext.stock.doctype.pick_list.mapper import create_delivery_note

	project = frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	villa = frappe.db.get_value("Sales Order", {"project": project, "docstatus": 1})
	if not villa:
		return
	# The van and its driver are the fleet's, kept by whoever set the workspace up.
	van = once(
		"Vehicle",
		{"license_plate": "DXB K 41207"},
		{
			"license_plate": "DXB K 41207",
			"make": "Isuzu",
			"model": "NPR 75",
			"last_odometer": 48210,
			"fuel_type": "Diesel",
			"uom": "Litre",
		},
	).name
	employee = frappe.db.get_value("Employee", {"user_id": DRIVER})
	driver = once(
		"Driver",
		{"employee": employee},
		{"full_name": "Yousef Bakr", "employee": employee, "status": "Active"},
	).name
	customer = frappe.db.get_value("Sales Order", villa, "customer")
	with as_user(STORES):
		pick = create_pick_list(villa)
		pick.pick_manually = 1
		pick.locations = [row for row in pick.locations if row.item_code == "WIN-CS12"][:1]
		for row in pick.locations:
			row.warehouse = wh("Finished Goods")
			row.qty = row.stock_qty = row.picked_qty = 24
		save(pick, submit=True)
		# ERPNext's mapper saves the draft itself.
		note = create_delivery_note(pick.name)
		if note.is_new():
			note = save(note)
		slip = frappe.new_doc("Packing Slip")
		slip.delivery_note = note.name
		slip.from_case_no, slip.to_case_no = 1, 3
		slip.append("items", {"item_code": "WIN-CS12", "qty": 24, "net_weight": 28, "weight_uom": "Kg", "dn_detail": note.items[0].name})
		slip.gross_weight_pkg, slip.gross_weight_uom = 735, "Kg"
		save(slip, submit=True)
		note.reload()
		note.submit()
		trip = frappe.new_doc("Delivery Trip")
		trip.company = COMPANY
		trip.driver = driver
		trip.vehicle = van
		trip.departure_time = f"{ahead(1)} 07:30:00"
		trip.append(
			"delivery_stops",
			{
				"customer": customer,
				"address": frappe.db.get_value("Dynamic Link", {"link_doctype": "Customer", "link_name": customer, "parenttype": "Address"}, "parent"),
				"delivery_note": note.name,
				"details": "Villa site, Al Barsha. Ground floor windows, three crates.",
			},
		)
		save(trip, submit=True)
	# ERPNext makes no pick list for an order that has stock held, so the
	# doors are held once the windows are on their way.
	settings = frappe.get_single("Stock Settings")
	if not settings.enable_stock_reservation:
		settings.enable_stock_reservation = 1
		settings.save()
	with as_user(SALES):
		order = frappe.get_doc("Sales Order", villa)
		doors = next(row for row in order.items if row.item_code == "DR-SL24")
		doors.reserve_stock = 1
		order.save()
		order.create_stock_reservation_entries(
			items_details=[
				{
					"sales_order_item": doors.name,
					"item_code": "DR-SL24",
					"warehouse": wh("Finished Goods"),
					"qty_to_reserve": 20,
				}
			],
			notify=False,
		)


def _order(customer, date, lines, delivery=None):
	order = frappe.new_doc("Sales Order")
	order.customer = customer
	order.company = COMPANY
	dated(order, date, "transaction_date")
	bill_in(order, "Customer", customer)
	order.delivery_date = delivery or add_days(date, 21)
	order.set_warehouse = wh("Finished Goods")
	for code, qty, rate in lines:
		order.append("items", {"item_code": code, "qty": qty, "rate": rate, "delivery_date": order.delivery_date, "warehouse": wh("Finished Goods")})
	return save(order, submit=True)


def _deliver(order, date):
	from erpnext.selling.doctype.sales_order.mapper import make_delivery_note

	note = make_delivery_note(order.name)
	dated(note, date)
	return save(note, submit=True)


def _invoice(note, date):
	from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice

	invoice = make_sales_invoice(note.name)
	dated(invoice, date)
	invoice.due_date = add_days(date, 30)
	for row in invoice.get("payment_schedule") or []:
		row.due_date = invoice.due_date
	return save(invoice, submit=True)


def _return(note, invoice, code, qty, date):
	"""A unit sent back against its delivery, and the credit note against
	its invoice."""
	from erpnext.accounts.doctype.sales_invoice.mapper import make_sales_return as credit_note
	from erpnext.stock.doctype.delivery_note.mapper import make_sales_return

	for back in (make_sales_return(note.name), credit_note(invoice.name)):
		dated(back, date)
		back.items = [row for row in back.items if row.item_code == code]
		for row in back.items:
			row.qty = -qty
		if back.doctype == "Sales Invoice":
			back.payment_schedule = []
		save(back, submit=True)


def _pay(invoice, date):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if date > today():
		return
	with as_user(ACCOUNTS):
		payment = get_payment_entry(invoice.doctype, invoice.name)
		dated(payment, date)
		payment.reference_no = f"RCPT-{invoice.name[-6:]}"
		payment.reference_date = date
		save(rated(payment), submit=True)
