"""Buying, the whole way round: a material request when stock runs low, a
request for quotation to two suppliers, their quotes, the order to the
cheaper one, the delivery received, the bill and its payment; glass
returned broken; hardware bought in euros; and the office's monthly supplies,
one bill still unpaid."""

import frappe
from frappe.utils import add_days, flt

from onedesk.one_demo.base import COMPANY, as_user, dated, on, save, today, wh

BUYER = "karim@one.test"
ACCOUNTS = "huda@one.test"


def run(password=None):
	if frappe.db.exists("Material Request", {"docstatus": 1}):
		return
	with as_user(BUYER):
		_round(on(3, 2), (("ALU-6063", 1500), ("SEAL-EPDM", 2000)), ("Al Noor Aluminium", "Gulf Glass Industries"), "Al Noor Aluminium", paid=True)
		_round(on(4, 6), (("GLS-DGU", 300), ("GLS-TMP10", 120)), ("Gulf Glass Industries", "Al Noor Aluminium"), "Gulf Glass Industries", paid=True, broken=("GLS-DGU", 6))
		_round(on(6, 3), (("ALU-6063", 1800), ("FIX-ANCH", 800), ("SIL-CLR", 150)), ("Al Noor Aluminium",), "Al Noor Aluminium", paid=True)
		_round(on(8, 18), (("GLS-DGU", 260), ("GLS-TMP10", 60)), ("Gulf Glass Industries",), "Gulf Glass Industries", paid=False)
		_order("Euro Hardware Trading", on(5, 11), (("HW-HINGE", 400, 8.6), ("HW-HANDLE", 300, 5.2), ("HW-LOCK", 90, 21)), currency="EUR", paid=True)
		_order("Euro Hardware Trading", on(9, 2), (("HW-HINGE", 300, 8.6), ("HW-LOCK", 60, 21)), currency="EUR", paid=False, receive=False)
	with as_user(ACCOUNTS):
		for month in range(1, today().month + 1):
			_supplies(on(month, 5), paid=month < today().month)


def _round(date, lines, asked, chosen, paid, broken=None):
	from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq
	from erpnext.buying.doctype.supplier_quotation.mapper import make_purchase_order
	from erpnext.stock.doctype.material_request.mapper import make_request_for_quotation

	request = frappe.new_doc("Material Request")
	request.material_request_type = "Purchase"
	request.company = COMPANY
	dated(request, date, "transaction_date")
	request.schedule_date = add_days(date, 14)
	for code, qty in lines:
		request.append("items", {"item_code": code, "qty": qty, "schedule_date": request.schedule_date, "warehouse": wh("Stores")})
	save(request, submit=True)

	rfq = make_request_for_quotation(request.name)
	dated(rfq, add_days(date, 1), "transaction_date")
	rfq.message_for_supplier = "Please quote your best price and lead time."
	for supplier in asked:
		rfq.append("suppliers", {"supplier": supplier, "send_email": 0})
	save(rfq, submit=True)

	quotes = {}
	for i, supplier in enumerate(asked):
		quote = make_supplier_quotation_from_rfq(rfq.name, for_supplier=supplier)
		dated(quote, add_days(date, 3), "transaction_date")
		for row in quote.items:
			row.rate = flt(frappe.db.get_value("Item Price", {"item_code": row.item_code, "price_list": "Standard Buying"}, "price_list_rate")) * (1 + 0.06 * i)
		quotes[supplier] = save(quote, submit=True)

	order = make_purchase_order(quotes[chosen].name)
	dated(order, add_days(date, 5), "transaction_date")
	order.schedule_date = add_days(date, 15)
	for row in order.items:
		row.schedule_date = order.schedule_date
		row.warehouse = wh("Stores")
	save(order, submit=True)
	_receive_and_bill(order, add_days(date, 15), paid, broken)


def _order(supplier, date, lines, currency=None, paid=True, receive=True):
	order = frappe.new_doc("Purchase Order")
	order.supplier = supplier
	order.company = COMPANY
	if currency:
		order.currency = currency
	dated(order, date, "transaction_date")
	order.schedule_date = add_days(date, 21)
	for code, qty, rate in lines:
		order.append("items", {"item_code": code, "qty": qty, "rate": rate, "schedule_date": order.schedule_date, "warehouse": wh("Stores")})
	save(order, submit=True)
	if receive:
		_receive_and_bill(order, add_days(date, 21), paid)


def _receive_and_bill(order, date, paid, broken=None):
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt
	from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice, make_purchase_return

	if date > today():
		return
	receipt = make_purchase_receipt(order.name)
	dated(receipt, date)
	receipt = save(receipt, submit=True)
	if broken:
		code, qty = broken
		back = make_purchase_return(receipt.name)
		dated(back, add_days(date, 1))
		back.items = [row for row in back.items if row.item_code == code]
		for row in back.items:
			row.qty = -qty
			row.received_qty = -qty
		save(back, submit=True)
	bill = make_purchase_invoice(receipt.name)
	dated(bill, add_days(date, 2))
	bill.bill_no = f"{order.supplier[:3].upper()}-{order.name[-5:]}"
	bill.bill_date = bill.posting_date
	bill.due_date = add_days(bill.posting_date, 30)
	for row in bill.get("payment_schedule") or []:
		row.due_date = bill.due_date
	bill = save(bill, submit=True)
	if paid:
		_pay(bill, add_days(bill.posting_date, 25))


def _supplies(date, paid):
	if date > today():
		return
	bill = frappe.new_doc("Purchase Invoice")
	bill.supplier = "Gulf Office Supplies"
	bill.company = COMPANY
	dated(bill, date)
	bill.bill_no = f"GOS-{date.month:02d}{date.year}"
	bill.bill_date = date
	bill.due_date = add_days(date, 15)
	bill.append("items", {"item_code": "OFF-SUP", "qty": 4 + date.month % 3, "rate": 150})
	bill = save(bill, submit=True)
	if paid:
		_pay(bill, add_days(date, 12))


def _pay(invoice, date):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if date > today():
		return
	with as_user(ACCOUNTS):
		payment = get_payment_entry(invoice.doctype, invoice.name)
		dated(payment, date)
		payment.reference_no = f"PAY-{invoice.name[-6:]}"
		payment.reference_date = date
		save(payment, submit=True)
