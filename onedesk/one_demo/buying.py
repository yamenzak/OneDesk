"""Buying, the whole way round: a material request when stock runs low, a
request for quotation to two suppliers, their quotes, the order to the
cheaper one, the delivery received, the bill and its payment; glass
returned broken; more broken glass found after the bill, sent back and
debited; hardware bought in euros, with its freight and duty added to what it
cost; tempered glass turned away on arrival; seals received and not yet
billed; and the office's monthly supplies, one bill still unpaid."""

import frappe
from frappe.utils import add_days, flt

from onedesk.one_demo.base import COMPANY, account, ago, as_user, dated, on, once, rated, save, today, wh

BUYER = "karim@one.test"
ACCOUNTS = "huda@one.test"


def run(password=None):
	if not frappe.db.exists("Material Request", {"docstatus": 1}):
		_rounds()
	_landed()
	_inspected()


def _rounds():
	with as_user(BUYER):
		_round(on(3, 2), (("ALU-6063", 1500), ("SEAL-EPDM", 2000)), ("Al Noor Aluminium", "Gulf Glass Industries"), "Al Noor Aluminium", paid=True)
		_round(on(4, 6), (("GLS-DGU", 300), ("GLS-TMP10", 120)), ("Gulf Glass Industries", "Al Noor Aluminium"), "Gulf Glass Industries", paid=True, broken=("GLS-DGU", 6))
		_round(on(6, 3), (("ALU-6063", 1800), ("FIX-ANCH", 800), ("SIL-CLR", 150)), ("Al Noor Aluminium",), "Al Noor Aluminium", paid=True)
		_round(on(8, 18), (("GLS-DGU", 260), ("GLS-TMP10", 60)), ("Gulf Glass Industries",), "Gulf Glass Industries", paid=False, debited=("GLS-DGU", 4))
		_order("Euro Hardware Trading", on(5, 11), (("HW-HINGE", 400, 8.6), ("HW-HANDLE", 300, 5.2), ("HW-LOCK", 90, 21)), currency="EUR", paid=True)
		_order("Euro Hardware Trading", on(9, 2), (("HW-HINGE", 300, 8.6), ("HW-LOCK", 60, 21)), currency="EUR", paid=False, receive=False)
		_order("Al Noor Aluminium", ago(30), (("SEAL-EPDM", 600, 4.5),), paid=False, bill=False)
	with as_user(ACCOUNTS):
		for month in range(1, today().month + 1):
			_supplies(on(month, 5), paid=month < today().month)


def _landed():
	"""Desert Logistics' freight and the customs duty on the first euro
	hardware, added to what each hinge, handle and lock cost, by the accountant
	who keeps the forwarder's bill."""
	receipt = frappe.db.get_value(
		"Purchase Receipt",
		{"supplier": "Euro Hardware Trading", "docstatus": 1, "is_return": 0},
		["name", "posting_date", "base_grand_total"],
		as_dict=True,
		order_by="posting_date asc",
	)
	if not receipt or frappe.db.exists("Landed Cost Purchase Receipt", {"receipt_document": receipt.name, "docstatus": 1}):
		return
	duty = once(
		"Account",
		{"account_name": "Customs Duty", "company": COMPANY},
		{
			"account_name": "Customs Duty",
			"company": COMPANY,
			"parent_account": account("Indirect Expenses"),
			"account_type": "Chargeable",
		},
	).name
	with as_user(ACCOUNTS):
		landed = frappe.new_doc("Landed Cost Voucher")
		landed.company = COMPANY
		dated(landed, add_days(receipt.posting_date, 4))
		landed.append(
			"purchase_receipts",
			{
				"receipt_document_type": "Purchase Receipt",
				"receipt_document": receipt.name,
				"supplier": "Euro Hardware Trading",
				"posting_date": receipt.posting_date,
				"grand_total": receipt.base_grand_total,
			},
		)
		landed.get_items_from_purchase_receipts()
		landed.distribute_charges_based_on = "Amount"
		landed.append("taxes", {"description": "Freight from Genoa, Desert Logistics", "expense_account": account("Freight and Forwarding Charges"), "amount": 1150})
		landed.append("taxes", {"description": "Customs duty, 5%", "expense_account": duty, "amount": flt(receipt.base_grand_total * 0.05, 2)})
		save(landed, submit=True)


def _inspected():
	"""Forty square metres of tempered glass from Gulf Glass, six of them
	chipped on the edge. Tempered glass is inspected on arrival from now on:
	the inspection passes the delivery and finds the chips, the receipt rejects
	those six into Rejected for Gulf Glass to collect, and the stores take the
	rest. An inspection marked Rejected would stop the whole receipt, as
	ERPNext's Stock Settings say."""
	if frappe.db.exists("Quality Inspection", {"reference_type": "Purchase Receipt", "item_code": "GLS-TMP10"}):
		return
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	rejected = once(
		"Warehouse",
		{"warehouse_name": "Rejected", "company": COMPANY},
		{
			"warehouse_name": "Rejected",
			"company": COMPANY,
			"parent_warehouse": wh("All Warehouses"),
			"is_rejected_warehouse": 1,
		},
	).name
	frappe.db.set_value("Item", "GLS-TMP10", "inspection_required_before_purchase", 1)
	for name in ("Chips or cracks", "Thickness within 0.2 mm"):
		once("Quality Inspection Parameter", {"parameter": name}, {"parameter": name})
	with as_user(BUYER):
		order = frappe.new_doc("Purchase Order")
		order.supplier = "Gulf Glass Industries"
		order.company = COMPANY
		dated(order, ago(12), "transaction_date")
		order.schedule_date = ago(4)
		rate = flt(frappe.db.get_value("Item Price", {"item_code": "GLS-TMP10", "price_list": "Standard Buying"}, "price_list_rate"))
		order.append("items", {"item_code": "GLS-TMP10", "qty": 40, "rate": rate, "schedule_date": order.schedule_date, "warehouse": wh("Stores")})
		save(order, submit=True)
		receipt = make_purchase_receipt(order.name)
		dated(receipt, ago(4))
		receipt.supplier_delivery_note = "GG-DN-8812"
		receipt.lr_no = "D 41207"
		row = receipt.items[0]
		row.received_qty, row.qty, row.rejected_qty = 40, 34, 6
		row.rejected_warehouse = rejected
		receipt = save(receipt)
		inspection = frappe.new_doc("Quality Inspection")
		inspection.update(
			{
				"company": COMPANY,
				"inspection_type": "Incoming",
				"reference_type": "Purchase Receipt",
				"reference_name": receipt.name,
				"child_row_reference": receipt.items[0].name,
				"item_code": "GLS-TMP10",
				"sample_size": 40,
				"inspected_by": BUYER,
				"manual_inspection": 1,
				"status": "Accepted",
				"remarks": "Thirty-four square metres accepted. Six chipped on the edge, rejected and set aside for Gulf Glass to collect.",
			}
		)
		dated(inspection, ago(4), "report_date")
		inspection.append("readings", {"specification": "Chips or cracks", "numeric": 0, "manual_inspection": 1, "status": "Rejected", "reading_value": "3 panes chipped"})
		inspection.append("readings", {"specification": "Thickness within 0.2 mm", "numeric": 0, "manual_inspection": 1, "status": "Accepted", "reading_value": "10.1 mm"})
		save(inspection, submit=True)
		receipt.reload()
		receipt.submit()


def _round(date, lines, asked, chosen, paid, broken=None, debited=None):
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
	_receive_and_bill(order, add_days(date, 15), paid, broken, debited=debited)


def _order(supplier, date, lines, currency=None, paid=True, receive=True, bill=True):
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
		_receive_and_bill(order, add_days(date, 21), paid, bill=bill)


def _receive_and_bill(order, date, paid, broken=None, debited=None, bill=True):
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
	if not bill:
		return
	bill = make_purchase_invoice(receipt.name)
	dated(bill, add_days(date, 2))
	bill.bill_no = f"{order.supplier[:3].upper()}-{order.name[-5:]}"
	bill.bill_date = bill.posting_date
	bill.due_date = add_days(bill.posting_date, 30)
	for row in bill.get("payment_schedule") or []:
		row.due_date = bill.due_date
	bill = save(bill, submit=True)
	if debited:
		_debit(receipt, bill, *debited, add_days(bill.posting_date, 3))
	if paid:
		_pay(bill, add_days(bill.posting_date, 25))


def _debit(receipt, bill, code, qty, date):
	"""Broken units found after the bill: they go back on the receipt, and the
	supplier's bill is debited for them."""
	from erpnext.accounts.doctype.purchase_invoice.mapper import make_debit_note
	from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_return

	if date > today():
		return
	for back in (make_purchase_return(receipt.name), make_debit_note(bill.name)):
		dated(back, date)
		back.items = [row for row in back.items if row.item_code == code]
		for row in back.items:
			row.qty = -qty
			if back.doctype == "Purchase Receipt":
				row.received_qty = -qty
		if back.doctype == "Purchase Invoice":
			back.bill_no = f"{bill.bill_no}-DN"
			back.payment_schedule = []
		save(back, submit=True)


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
		save(rated(payment), submit=True)
