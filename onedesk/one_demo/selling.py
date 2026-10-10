"""Selling products, apart from the projects: orders delivered and invoiced
and paid, one in pounds, one still to deliver, a window sent back and credited,
two sample windows sent to New York in dollars, balustrades delivered and not
yet invoiced, and a survey fee nobody has paid."""

import frappe
from frappe.utils import add_days

from onedesk.one_book.currency import bill_in
from onedesk.one_demo.base import COMPANY, ago, ahead, as_user, dated, on, rated, save, today, wh

SALES = "omar@one.test"
ACCOUNTS = "huda@one.test"


def run(password=None):
	if frappe.db.exists("Delivery Note", {"docstatus": 1}):
		return
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
