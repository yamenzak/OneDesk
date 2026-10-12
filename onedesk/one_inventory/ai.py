"""What OneAI does in OneInventory: reads items, the stores, receipts,
deliveries, movements, counts, buying, the workshop and equipment as the
reader sees them, and drafts what it suggests there as a card the reader
approves. The README's Under the hood lists each tool.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import flt, get_fullname

#: An item's page (page/item_view), by its open view, from `?view=`.
PAGE = "item-view"
#: Stock on Hand (page/stock_on_hand).
STOCK = "stock-on-hand"
#: Shop Floor (page/floor).
FLOOR = "floor"

_HOW = {
	"label": _lt("How is this item doing?"),
	"ask": _lt(
		"How is this item doing? Say how much is on hand and free to sell, whether it is low anywhere, what is "
		"on order or being made, and what it last cost."
	),
	"can": "read",
	"doctype": "Item",
	"expects": "item_facts",
}
_ORDER = {
	"label": _lt("Should I order more?"),
	"ask": _lt(
		"Should I order more of this item? Say what is on hand and promised, its reorder level, what is already "
		"on order, and who it was last bought from and at what price."
	),
	"can": "read",
	"doctype": "Item",
	"expects": "item_facts",
}
_CHANGE = {
	# The reader says what; the model suggests the card.
	"label": _lt("Change this item…"),
	"ask": _lt("Change this item: "),
	"fill": True,
	"can": "write",
	"doctype": "Item",
	"expects": "plan_item_change",
}
_LOW = {
	"label": _lt("What is running low?"),
	"ask": _lt(
		"Which items are at or below their reorder level, where, and what is already on order for them."
	),
	"expects": "running_low",
}

_HELD = {
	"label": _lt("What is short?"),
	"ask": _lt(
		"Which items have more promised to customers than is on hand, by how much, and what is on order for them."
	),
	"expects": "stock_on_hand",
}
_WORTH = {
	"label": _lt("What is this warehouse worth?"),
	"ask": _lt("What does this warehouse hold, what is it worth, and what in it is low or short?"),
	"can": "read",
	"doctype": "Warehouse",
	"expects": "stock_on_hand",
}

_RECEIVED = {
	"label": _lt("What came in on this receipt?"),
	"ask": _lt(
		"What came in on this receipt? Say what was accepted and rejected and why, what it cost with freight and "
		"duty, which order it was for, and whether it is billed."
	),
	"can": "read",
	"doctype": "Purchase Receipt",
	"expects": "receipt_facts",
}
_ARRIVING = {
	"label": _lt("What is still to arrive?"),
	"ask": _lt("What is still to arrive from suppliers, what is late, and from whom?"),
	"expects": "still_to_arrive",
}
_RECEIVE = {
	"label": _lt("Receive this order"),
	"ask": _lt("Draft a receipt for what is still to come on this order."),
	# Offered to whoever may make the receipt, not whoever may read the order.
	"can": "create",
	"doctype": "Purchase Receipt",
	"expects": "plan_receipt",
}

_SENT = {
	"label": _lt("What went out on this delivery?"),
	"ask": _lt(
		"What went out on this delivery? Say which order it was for, what it was worth, how it was packed, which "
		"trip takes it and who drives, and whether it is billed."
	),
	"can": "read",
	"doctype": "Delivery Note",
	"expects": "delivery_facts",
}
_TO_DELIVER = {
	"label": _lt("What is still to deliver?"),
	"ask": _lt("What is still to deliver to customers, what is late, and is the stock there for it?"),
	"expects": "still_to_deliver",
}
_DELIVER = {
	"label": _lt("Deliver this order"),
	"ask": _lt("Draft a delivery for what is still to go out on this order."),
	# Offered to whoever may make the delivery, not whoever may read the order.
	"can": "create",
	"doctype": "Delivery Note",
	"expects": "plan_delivery",
}

_MOVED = {
	"label": _lt("What did this movement do?"),
	"ask": _lt("What did this stock movement do? Say from where to where, for which project, what it was worth and who made it."),
	"can": "read",
	"doctype": "Stock Entry",
	"expects": "movement_facts",
}
_SEND = {
	"label": _lt("Send stock to a site"),
	"ask": _lt("Draft a transfer of stock from the stores to a site or another warehouse."),
	"can": "create",
	"doctype": "Stock Entry",
	"expects": "plan_transfer",
}
_COUNTED = {
	"label": _lt("What did this count find?"),
	"ask": _lt("What did this stock count find? Say what the books held and what was counted, and what it did to the books."),
	# On the count's own form, so the reader's right to read it is the count's.
	"can": "read",
	"expects": "count_facts",
}

_ASK = {
	"label": _lt("Ask suppliers for prices"),
	"ask": _lt("Draft a request for quotation for this material request, to the suppliers who sold us these items before."),
	"can": "create",
	"doctype": "Request for Quotation",
	"expects": "plan_quote_request",
}
_COMPARE = {
	"label": _lt("Compare the quotes"),
	"ask": _lt("Compare the quotes suppliers sent for this request, line by line, and say who is cheapest on each."),
	"can": "read",
	"doctype": "Supplier Quotation",
	"expects": "quote_comparison",
}
#: On a quote's own form, where the reader's right to read it is the form's.
_COMPARE_HERE = {key: value for key, value in _COMPARE.items() if key != "doctype"}
_LATE = {
	"label": _lt("Which orders are late?"),
	"ask": _lt("Which purchase orders are late, from whom, since when, and what is still to come on each?"),
	"can": "read",
	"expects": "late_orders",
}

_IN_HAND = {
	"label": _lt("What is the workshop making?"),
	"ask": _lt("Which work orders are open, for what, how far along, and which are late?"),
	"can": "read",
	"expects": "work_in_hand",
}
_ON_FLOOR = {
	"label": _lt("What is running on the floor?"),
	"ask": _lt("Which steps is someone on now, for how long, which are paused, and which are short of materials?"),
	"can": "read",
	"expects": "on_the_floor",
}
_HOW_FAR = {
	"label": _lt("How far along is it?"),
	"ask": _lt("How far along is this work order, step by step, and is everything it needs in the stores?"),
	"can": "read",
	"expects": "work_order_facts",
}
_MAKE = {
	"label": _lt("Make a work order"),
	"ask": _lt("Draft a work order to make ten of this, with its own bill of materials."),
	"can": "create",
	"doctype": "Work Order",
	"expects": "plan_work_order",
}

_ASSET = {
	"label": _lt("How is this asset doing?"),
	"ask": _lt(
		"How is this asset doing? Say who has it and where, what it is worth, its next service and whether it "
		"is late, and its repairs."
	),
	"can": "read",
	"doctype": "Asset",
	"expects": "asset_facts",
}
_DUE = {
	"label": _lt("Which services are due?"),
	"ask": _lt("Which services on our equipment are late or due in the next month, and who does each?"),
	"expects": "services_due",
}
_HAND = {
	# The reader says to whom; the model suggests the card.
	"label": _lt("Hand this to somebody…"),
	"ask": _lt("Hand this asset to "),
	"fill": True,
	"can": "write",
	"doctype": "Asset",
	"expects": "plan_handover",
}

SUGGESTIONS = {
	f"page:{PAGE}": [_HOW, _ORDER, _CHANGE],
	f"page:{PAGE}/stock": [_HOW, _ORDER],
	f"page:{PAGE}/buying": [_ORDER, _HOW],
	"Item": [_LOW, _HOW],
	f"page:{STOCK}": [_LOW, _HELD],
	f"page:{FLOOR}": [_ON_FLOOR, _IN_HAND],
	"Warehouse": [_WORTH, _LOW],
	"Purchase Receipt": [_RECEIVED, _ARRIVING],
	"Purchase Order": [_RECEIVE, _LATE, _ARRIVING],
	"Material Request": [_ASK, _COMPARE],
	"Request for Quotation": [_COMPARE],
	"Supplier Quotation": [_COMPARE_HERE],
	"Delivery Note": [_SENT, _TO_DELIVER],
	"Sales Order": [_DELIVER, _TO_DELIVER],
	"Stock Entry": [_MOVED, _SEND],
	"Stock Reconciliation": [_COUNTED],
	"Work Order": [_HOW_FAR, _IN_HAND],
	"BOM": [_MAKE, _IN_HAND],
	"Job Card": [_ON_FLOOR, _IN_HAND],
	"Asset": [_ASSET, _HAND, _DUE],
	"Asset Maintenance Log": [_DUE],
	"Asset Maintenance": [_DUE],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on an item's page or Stock on Hand."""
	if said.get("page") == STOCK:
		return (
			"The reader is on Stock on Hand, which lists what each item has on hand, free to sell, on order and "
			"its worth, in every warehouse or one. stock_on_hand reads it as the page shows it. How the page works "
			"is in OneInventory's documentation (how_to)."
		)
	if said.get("page") == FLOOR:
		return (
			"The reader is on the Shop Floor, which shows the open work orders with how far their steps have got, "
			"and each step's job card to start, pause, record and close. on_the_floor reads what is running now; "
			"work_order_facts reads one work order. How the page works is in OneInventory's documentation (how_to)."
		)
	if said.get("page") != PAGE:
		return None
	name = (said.get("record") or "").strip()
	if not name or not frappe.db.exists("Item", name) or not frappe.has_permission("Item", "read", doc=name):
		return "The reader is on an item's page."
	title = frappe.db.get_value("Item", name, "item_name")
	return (
		f"The reader is on the page of item {name} (“{title}”). item_facts reads it as its page shows it: "
		"how much is on hand in each warehouse, free to sell, on order and being made, its reorder levels, "
		"its suppliers and last prices, its open orders and what it is made from; plan_item_change suggests "
		"a change to it as a card, as the page makes it. Nothing is changed until the reader approves. How "
		"an item's page works is in OneInventory's documentation (how_to)."
	)


def item_facts(item: Annotated[str, "The item's code, such as ALU-6063."]) -> dict:
	"""An item as its page shows it to the reader: what it is, how much is on
	hand in each warehouse and what that is worth, how much is free to sell,
	on order and being made, where it is low, its suppliers and what it last
	cost, its open purchase and sales orders, and what it is made from. Read
	before answering about an item's stock or whether to order more."""
	from onedesk.one_inventory import view

	if not frappe.db.exists("Item", item) or not frappe.has_permission("Item", "read", doc=item):
		return {"error": f"No item the reader may see is {item}."}
	said = view.read(item)
	summary = said["summary"] or {}
	stock = said["stock"] or {}
	buying = said["buying"] or {}
	selling = said["selling"] or {}
	making = said["making"] or {}
	out = {
		"code": said["name"],
		"name": said["item_name"],
		"kind": said["kind"],
		"group": said["item_group"],
		"unit": said["stock_uom"],
		"disabled": bool(said["disabled"]),
		"currency": said["currency"],
		"on_hand": summary.get("on_hand"),
		"free_to_sell": summary.get("free"),
		"held_for_orders": summary.get("held") or None,
		"on_order": summary.get("ordered"),
		"worth": summary.get("value"),
		"low_in": summary.get("below") or [],
		"warehouses": [
			{
				"warehouse": one["warehouse"],
				"on_hand": one["on_hand"],
				"promised": one["reserved"],
				"on_order": one["ordered"],
				"reorder_level": one["level"] or None,
				"reorder_qty": one["order_qty"] or None,
				"low": one["low"],
			}
			for one in stock.get("places") or []
		],
		"last_bought": _last(said["last_bought"]),
		"last_made": {"qty": said["last_made"].qty, "on": str(said["last_made"].posting_date)}
		if said["last_made"]
		else None,
		"suppliers": [
			{
				"supplier": one["supplier"],
				"last_rate": one["rate"],
				"currency": one["currency"],
				"rate_before": one["before"],
				"last_ordered": str(one["last"]) if one["last"] else None,
				"part_no": one["part_no"],
				"agreed": {"rate": one["agreed"]["rate"], "left": one["agreed"]["left"]} if one["agreed"] else None,
				"default": one["default"],
			}
			for one in buying.get("suppliers") or []
		],
		"open_quotes": [
			{
				"quote": one.name,
				"supplier": one.supplier,
				"rate": one.rate,
				"currency": one.currency,
				"unit": one.uom,
				"valid_till": str(one.valid_till) if one.valid_till else None,
				"cheapest": one.cheapest,
			}
			for one in buying.get("quotes") or []
		],
		"manufacturers": [
			{"manufacturer": one.manufacturer, "part_no": one.manufacturer_part_no, "default": bool(one.is_default)}
			for one in buying.get("manufacturers") or []
		],
		"purchase_orders": [_order(one) for one in buying.get("orders") or []],
		"sales_orders": [
			{**_order(one), "can_go_now": one.get("can_go"), "short": one.get("short")}
			for one in selling.get("orders") or []
		],
		"customers_last_year": [
			{
				"customer": one["customer"],
				"qty": one["qty"],
				"returned": one["returned"] or None,
				"amount": one["amount"],
				"last_rate": one["rate"],
				"currency": one["currency"],
				"code": one["code"],
			}
			for one in selling.get("customers") or []
		],
		"open_quotations": [
			{
				"quotation": one.name,
				"for": one.customer_name or one.party_name,
				"rate": one.rate,
				"currency": one.currency,
				"qty": one.qty,
				"valid_till": str(one.valid_till) if one.valid_till else None,
			}
			for one in selling.get("quotes") or []
		],
		"made_from": [
			{"item": one.item_name, "qty": one.qty, "unit": one.uom, "enough_for": one.get("covers")}
			for one in making.get("materials") or []
		],
		"can_make_now": making.get("can_make"),
		"steps": [
			{"step": one.operation, "workstation": one.workstation, "minutes": one.time_in_mins}
			for one in making.get("steps") or []
		],
		"being_made": [
			{
				"work_order": one.name,
				"qty": one.qty,
				"made": one.produced_qty,
				"project": one.project,
				"late": one.get("late") or None,
				"steps": [{"step": step.operation, "done": step.completed_qty} for step in one.get("steps") or []],
			}
			for one in making.get("orders") or []
		],
		"made_last_year": [
			{"work_order": one.name, "made": one.produced_qty, "project": one.project}
			for one in making.get("made") or []
		],
		"needed_for_making": [
			{"work_order": one.name, "for": one.item_name, "still_to_take": one.left}
			for one in making.get("needed") or []
		],
	}
	return {key: value for key, value in out.items() if value not in (None, [], {})}


def stock_on_hand(
	warehouse: Annotated[str, "Only this warehouse, as named, such as Stores - SGA."] | None = None,
	search: Annotated[str, "Only items whose name or code has this in it."] | None = None,
) -> dict:
	"""What the stores hold now, as Stock on Hand shows it: each item's
	quantity on hand, free to sell (on hand less what is promised), on order
	and worth, where it is low and whether more is promised than is there,
	with what each warehouse holds and is worth. Read before answering what is
	in stock, short or worth what."""
	from onedesk.one_inventory import stock

	if warehouse and not frappe.db.exists("Warehouse", warehouse):
		return {"error": f"There is no warehouse called {warehouse}. Ask which one they meant."}
	if not frappe.has_permission("Bin", "read"):
		return {"error": "The reader may not see stock levels."}
	said = stock.on_hand(warehouse=warehouse, search=search)
	return {
		"currency": said["currency"],
		"warehouse": said["warehouse"],
		"worth": said["worth"],
		"items": said["count"],
		"low": said["low"],
		"short": said["short"],
		"warehouses": [
			{"warehouse": one["name"], "items": one["items"], "worth": one["worth"]} for one in said["warehouses"]
		],
		"lines": [
			{
				"item": one["item"],
				"name": one["item_name"],
				"unit": one["uom"],
				"on_hand": one["on_hand"],
				"free_to_sell": one["free"],
				"on_order": one["on_order"],
				"worth": one["worth"],
				"low_in": one["low_in"],
			}
			for one in said["items"][:100]
		],
	}


def receipt_facts(receipt: Annotated[str, "The receipt's number, such as MAT-PRE-2026-00010."]) -> dict:
	"""What came in on a receipt, as its form shows it to the reader: from
	whom and on what order, each line received, accepted and rejected, what it
	was valued at with freight and duty, the inspections on arrival, and what
	of it is billed. Read before answering about a delivery."""
	if not frappe.db.exists("Purchase Receipt", receipt) or not frappe.has_permission(
		"Purchase Receipt", "read", doc=receipt
	):
		return {"error": f"No receipt the reader may see is {receipt}."}
	doc = frappe.get_doc("Purchase Receipt", receipt)
	company = frappe.get_cached_value("Company", doc.company, "default_currency")
	landed = frappe.get_all(
		"Landed Cost Purchase Receipt",
		filters={"receipt_document": doc.name, "docstatus": 1},
		pluck="parent",
	)
	charges = (
		frappe.get_all(
			"Landed Cost Taxes and Charges",
			filters={"parent": ["in", landed]},
			fields=["description", "base_amount"],
		)
		if landed
		else []
	)
	inspections = frappe.get_all(
		"Quality Inspection",
		filters={"reference_type": "Purchase Receipt", "reference_name": doc.name, "docstatus": 1},
		fields=["name", "item_code", "status", "remarks", "sample_size"],
	)
	bills = frappe.get_all(
		"Purchase Invoice Item",
		filters={"purchase_receipt": doc.name, "docstatus": 1},
		pluck="parent",
		distinct=True,
	)
	out = {
		"receipt": doc.name,
		"supplier": doc.supplier_name or doc.supplier,
		"on": str(doc.posting_date),
		"status": doc.status,
		"returned": bool(doc.is_return),
		"their_delivery_note": doc.supplier_delivery_note,
		"project": doc.project,
		"currency": doc.currency,
		"company_currency": company,
		"exchange_rate": flt(doc.conversion_rate) if doc.currency != company else None,
		"orders": list(dict.fromkeys(row.purchase_order for row in doc.items if row.purchase_order)),
		"lines": [
			{
				"item": row.item_code,
				"name": row.item_name,
				"unit": row.uom,
				"received": flt(row.received_qty),
				"accepted": flt(row.qty),
				"rejected": flt(row.rejected_qty),
				"into": row.warehouse,
				"rejected_into": row.rejected_warehouse if flt(row.rejected_qty) else None,
				"price": flt(row.rate),
				"valued_each_in_company_currency": flt(row.valuation_rate) if doc.docstatus == 1 else None,
				"freight_and_duty": flt(row.landed_cost_voucher_amount),
			}
			for row in doc.items
		],
		"total": flt(doc.grand_total),
		"total_in_company_currency": flt(doc.base_grand_total),
		"freight_and_duty": [{"what": one.description, "amount": flt(one.base_amount)} for one in charges],
		"inspections": [
			{"item": one.item_code, "result": one.status, "said": one.remarks, "sample": flt(one.sample_size)}
			for one in inspections
		],
		"billed_percent": flt(doc.per_billed),
		"bills": bills,
	}
	return {key: value for key, value in out.items() if value not in (None, [], "")}


def still_to_arrive(
	supplier: Annotated[str, "Only from this supplier."] | None = None,
	item: Annotated[str, "Only this item, by its code."] | None = None,
) -> dict:
	"""What is ordered from suppliers and not yet received, as the reader's
	purchase orders say it: each order's lines still to come, when they were
	due, and which are late, the latest first."""
	if not frappe.has_permission("Purchase Order", "read"):
		return {"error": "The reader may not see purchase orders."}
	filters = {"docstatus": 1, "per_received": ["<", 100], "status": ["not in", ("Closed", "On Hold", "Completed")]}
	if supplier:
		filters["supplier"] = supplier
	orders = {
		one.name: one
		for one in frappe.get_list(
			"Purchase Order",
			filters=filters,
			fields=["name", "supplier", "supplier_name", "currency", "project"],
			limit_page_length=0,
		)
	}
	if not orders:
		return {"lines": [], "count": 0}
	rows = frappe.get_all(
		"Purchase Order Item",
		filters={"parent": ["in", list(orders)], **({"item_code": item} if item else {})},
		fields=["parent", "item_code", "item_name", "qty", "received_qty", "uom", "schedule_date", "rate"],
	)
	day = frappe.utils.getdate(frappe.utils.today())
	lines = []
	for row in rows:
		left = flt(row.qty) - flt(row.received_qty)
		if left <= 0:
			continue
		order = orders[row.parent]
		due = frappe.utils.getdate(row.schedule_date) if row.schedule_date else None
		lines.append(
			{
				"order": row.parent,
				"supplier": order.supplier_name or order.supplier,
				"item": row.item_code,
				"name": row.item_name,
				"still_to_come": left,
				"unit": row.uom,
				"due": str(due) if due else None,
				"late_by_days": (day - due).days if due and due < day else 0,
				"project": order.project,
			}
		)
	lines.sort(key=lambda one: (-one["late_by_days"], one["due"] or ""))
	return {"lines": lines[:60], "count": len(lines), "late": sum(1 for one in lines if one["late_by_days"])}


def plan_receipt(
	order: Annotated[str, "The purchase order the goods came on, such as PUR-ORD-2026-00012."],
	lines: Annotated[
		list[dict],
		"Only what arrived, if not everything still to come: each {item: code, qty: how many}.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, why this receipt."] | None = None,
) -> dict:
	"""Suggest a draft receipt for what has arrived on a purchase order, as a
	card the reader approves. ERPNext's own mapping fills it, with what is still
	to come on each line unless told less. Nothing is received until the draft
	is submitted on its form."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	from onedesk.one_ai import proposals

	if not frappe.db.exists("Purchase Order", order) or not frappe.has_permission("Purchase Order", "read", doc=order):
		return {"error": f"No purchase order the reader may see is {order}."}
	if not frappe.has_permission("Purchase Receipt", "create"):
		return {"error": "The reader may not make receipts."}
	mapped = make_purchase_receipt(order)
	if not mapped.items:
		return {"error": "Everything on this order has been received. Say so."}
	wanted = {str(one.get("item")): flt(one.get("qty")) for one in lines or [] if one.get("item")}
	rows = []
	for row in mapped.items:
		qty = min(wanted[row.item_code], flt(row.qty)) if wanted and row.item_code in wanted else flt(row.qty)
		if (wanted and row.item_code not in wanted) or qty <= 0:
			continue
		rows.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": qty,
				"received_qty": qty,
				"stock_uom": row.stock_uom,
				"rate": row.rate,
				"uom": row.uom,
				"conversion_factor": row.conversion_factor,
				"warehouse": row.warehouse,
				"purchase_order": row.purchase_order,
				"purchase_order_item": row.purchase_order_item,
				"schedule_date": str(row.schedule_date) if row.schedule_date else None,
			}
		)
	if not rows:
		return {"error": "None of those items is still to come on this order. Ask which they meant."}
	changes = {
		"supplier": mapped.supplier,
		"currency": mapped.currency,
		"conversion_rate": mapped.conversion_rate,
		"buying_price_list": mapped.buying_price_list,
		"price_list_currency": mapped.price_list_currency,
		"plc_conversion_rate": mapped.plc_conversion_rate,
		"project": mapped.project,
		"items": rows,
	}
	return {
		"proposal": proposals.propose(
			"Create", "Purchase Receipt", changes={k: v for k, v in changes.items() if v not in (None, "")}, why=why
		),
		"state": "Proposed",
	}


def delivery_facts(delivery: Annotated[str, "The delivery's number, such as MAT-DN-2026-00006."]) -> dict:
	"""What went out on a delivery, as its form shows it to the reader: to
	whom and on what order, each line and the warehouse it left, what it was
	worth, how it was packed, the trip that takes it and who drives, and what
	of it is billed. Read before answering about a delivery."""
	if not frappe.db.exists("Delivery Note", delivery) or not frappe.has_permission(
		"Delivery Note", "read", doc=delivery
	):
		return {"error": f"No delivery the reader may see is {delivery}."}
	doc = frappe.get_doc("Delivery Note", delivery)
	slips = frappe.get_all(
		"Packing Slip",
		filters={"delivery_note": doc.name, "docstatus": 1},
		fields=["name", "from_case_no", "to_case_no", "gross_weight_pkg", "gross_weight_uom"],
	)
	stop = frappe.db.get_value(
		"Delivery Stop", {"delivery_note": doc.name, "parenttype": "Delivery Trip", "docstatus": ["<", 2]}, "parent"
	)
	trip = (
		frappe.db.get_value("Delivery Trip", stop, ["name", "status", "departure_time", "driver_name", "vehicle"], as_dict=True)
		if stop
		else None
	)
	out = {
		"delivery": doc.name,
		"customer": doc.customer_name or doc.customer,
		"on": str(doc.posting_date),
		"status": doc.status,
		"returned": bool(doc.is_return),
		"project": doc.project,
		"currency": doc.currency,
		"orders": list(dict.fromkeys(row.against_sales_order for row in doc.items if row.against_sales_order)),
		"lines": [
			{
				"item": row.item_code,
				"name": row.item_name,
				"qty": flt(row.qty),
				"unit": row.uom,
				"from": row.warehouse,
				"price": flt(row.rate),
			}
			for row in doc.items
		],
		"total": flt(doc.grand_total),
		"total_in_company_currency": flt(doc.base_grand_total),
		"packed": [
			{
				"slip": one.name,
				"cases": f"{one.from_case_no}–{one.to_case_no}",
				"gross_weight": f"{flt(one.gross_weight_pkg)} {one.gross_weight_uom or ''}".strip(),
			}
			for one in slips
		],
		"trip": {
			"trip": trip.name,
			"status": trip.status,
			"leaves": str(trip.departure_time) if trip.departure_time else None,
			"driver": trip.driver_name,
			"vehicle": trip.vehicle,
		}
		if trip
		else None,
		"billed_percent": flt(doc.per_billed),
	}
	return {key: value for key, value in out.items() if value not in (None, [], "")}


def still_to_deliver(
	customer: Annotated[str, "Only to this customer."] | None = None,
	project: Annotated[str, "Only for this project, by its ID such as PROJ-0001."] | None = None,
) -> dict:
	"""What customers have ordered and not yet had, as the reader's sales
	orders say it: each line still to go out, when it was promised, which are
	late, how much of it is on hand and free, and how much is held for it."""
	from onedesk.one_inventory import item as stock

	if not frappe.has_permission("Sales Order", "read"):
		return {"error": "The reader may not see sales orders."}
	filters = {"docstatus": 1, "per_delivered": ["<", 100], "status": ["not in", ("Closed", "On Hold", "Completed")]}
	if customer:
		filters["customer"] = customer
	if project:
		filters["project"] = project
	orders = {
		one.name: one
		for one in frappe.get_list(
			"Sales Order",
			filters=filters,
			fields=["name", "customer", "customer_name", "project"],
			limit_page_length=0,
		)
	}
	if not orders:
		return {"lines": [], "count": 0}
	rows = frappe.get_all(
		"Sales Order Item",
		filters={"parent": ["in", list(orders)]},
		fields=["parent", "item_code", "item_name", "qty", "delivered_qty", "uom", "delivery_date", "stock_reserved_qty"],
	)
	day = frappe.utils.getdate(frappe.utils.today())
	free = {}
	lines = []
	for row in rows:
		left = flt(row.qty) - flt(row.delivered_qty)
		if left <= 0 or not frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
			continue
		if row.item_code not in free:
			bins = frappe.get_all(
				"Bin", filters={"item_code": row.item_code}, fields=["actual_qty", "reserved_qty", "reserved_stock", "projected_qty", "warehouse"]
			)
			said = stock.summary(bins, [])
			free[row.item_code] = (said["on_hand"], said["free"])
		order = orders[row.parent]
		due = frappe.utils.getdate(row.delivery_date) if row.delivery_date else None
		lines.append(
			{
				"order": row.parent,
				"customer": order.customer_name or order.customer,
				"project": order.project,
				"item": row.item_code,
				"name": row.item_name,
				"still_to_go": left,
				"unit": row.uom,
				"held_for_it": flt(row.stock_reserved_qty),
				"on_hand": free[row.item_code][0],
				"free_to_sell": free[row.item_code][1],
				"due": str(due) if due else None,
				"late_by_days": (day - due).days if due and due < day else 0,
			}
		)
	lines.sort(key=lambda one: (-one["late_by_days"], one["due"] or ""))
	return {"lines": lines[:60], "count": len(lines), "late": sum(1 for one in lines if one["late_by_days"])}


def plan_delivery(
	order: Annotated[str, "The sales order the goods go out on, such as SAL-ORD-2026-00002."],
	lines: Annotated[
		list[dict],
		"Only what goes out now, if not everything still to go: each {item: code, qty: how many}.",
	]
	| None = None,
	why: Annotated[str, "In a sentence, why this delivery."] | None = None,
) -> dict:
	"""Suggest a draft delivery for what goes out on a sales order, as a card
	the reader approves. ERPNext's own mapping fills it, with what is still to
	go on each line unless told less. Nothing leaves the stores until the
	draft is submitted on its form."""
	from erpnext.selling.doctype.sales_order.mapper import make_delivery_note

	from onedesk.one_ai import proposals

	if not frappe.db.exists("Sales Order", order) or not frappe.has_permission("Sales Order", "read", doc=order):
		return {"error": f"No sales order the reader may see is {order}."}
	if not frappe.has_permission("Delivery Note", "create"):
		return {"error": "The reader may not make deliveries."}
	mapped = make_delivery_note(order)
	wanted = {str(one.get("item")): flt(one.get("qty")) for one in lines or [] if one.get("item")}
	rows = []
	for row in mapped.items:
		if wanted and row.item_code not in wanted:
			continue
		qty = min(wanted[row.item_code], flt(row.qty)) if wanted else flt(row.qty)
		if qty <= 0 or not frappe.get_cached_value("Item", row.item_code, "is_stock_item"):
			continue
		rows.append(
			{
				"item_code": row.item_code,
				"item_name": row.item_name,
				"qty": qty,
				"stock_uom": row.stock_uom,
				"rate": row.rate,
				"uom": row.uom,
				"conversion_factor": row.conversion_factor,
				"warehouse": row.warehouse,
				"against_sales_order": row.against_sales_order,
				"so_detail": row.so_detail,
			}
		)
	if not rows:
		return {"error": "Nothing of those is still to go out on this order. Say so."}
	changes = {
		"customer": mapped.customer,
		"currency": mapped.currency,
		"conversion_rate": mapped.conversion_rate,
		"selling_price_list": mapped.selling_price_list,
		"price_list_currency": mapped.price_list_currency,
		"plc_conversion_rate": mapped.plc_conversion_rate,
		"project": mapped.project,
		"items": rows,
	}
	return {
		"proposal": proposals.propose(
			"Create", "Delivery Note", changes={k: v for k, v in changes.items() if v not in (None, "")}, why=why
		),
		"state": "Proposed",
	}


def movement_facts(entry: Annotated[str, "The movement's number, such as MAT-STE-2026-00016."]) -> dict:
	"""What a stock movement did, as its form shows it to the reader: what
	kind it was, from where to where, for which project, each line and what
	it was worth, who made it, and how much of goods sent through transit has
	arrived. Read before answering about a transfer, an issue or a receipt of
	stock."""
	if not frappe.db.exists("Stock Entry", entry) or not frappe.has_permission("Stock Entry", "read", doc=entry):
		return {"error": f"No stock movement the reader may see is {entry}."}
	doc = frappe.get_doc("Stock Entry", entry)
	return {
		"movement": doc.name,
		"type": doc.stock_entry_type,
		"purpose": doc.purpose,
		"on": str(doc.posting_date),
		"by": get_fullname(doc.owner),
		"state": {0: "Draft", 1: "Submitted", 2: "Cancelled"}[doc.docstatus],
		"project": doc.project,
		"work_order": doc.work_order,
		"value_out": flt(doc.total_outgoing_value),
		"value_in": flt(doc.total_incoming_value),
		"currency": frappe.get_cached_value("Company", doc.company, "default_currency"),
		"in_transit": bool(doc.add_to_transit),
		"arrived_percent": flt(doc.per_transferred) if doc.add_to_transit else None,
		"lines": [
			{
				"item": row.item_code,
				"name": row.item_name,
				"qty": flt(row.qty),
				"unit": row.uom,
				"from": row.s_warehouse,
				"to": row.t_warehouse,
				"value": flt(row.amount),
			}
			for row in doc.items
		],
		"printed_as": "One Stock Entry",
	}


def count_facts(count: Annotated[str, "The count's number, such as MAT-RECO-2026-00002."]) -> dict:
	"""What a stock count found, as its form shows it to the reader: what it
	was for, where and when, each line with what the books held and what was
	counted, and the difference it made in the books and to which account.
	ERPNext keeps only the lines a count changed."""
	if not frappe.db.exists("Stock Reconciliation", count) or not frappe.has_permission(
		"Stock Reconciliation", "read", doc=count
	):
		return {"error": f"No stock count the reader may see is {count}."}
	doc = frappe.get_doc("Stock Reconciliation", count)
	return {
		"count": doc.name,
		"purpose": doc.purpose,
		"on": str(doc.posting_date),
		"by": get_fullname(doc.owner),
		"state": {0: "Draft", 1: "Submitted", 2: "Cancelled"}[doc.docstatus],
		"difference": flt(doc.difference_amount),
		"currency": frappe.get_cached_value("Company", doc.company, "default_currency"),
		"posted_to": doc.expense_account,
		"lines": [
			{
				"item": row.item_code,
				"name": row.item_name,
				"warehouse": row.warehouse,
				"books_held": flt(row.current_qty),
				"counted": flt(row.qty),
				"rate": flt(row.valuation_rate),
				"difference": flt(row.amount_difference),
			}
			for row in doc.items
		],
	}


def plan_transfer(
	to: Annotated[str, "The warehouse the goods go to, such as Mansour Villa Site - SGA."],
	lines: Annotated[list[dict], "What goes: each {item: code, qty: how many}."],
	source: Annotated[str, "The warehouse they come from. The company's default one when not said."] | None = None,
	project: Annotated[str, "The project they are for, when they are for one."] | None = None,
	why: Annotated[str, "In a sentence, why this transfer."] | None = None,
) -> dict:
	"""Suggest a draft transfer of stock from one warehouse to another, a
	site's among them, as a card the reader approves. It prints as a transfer
	note that travels with the goods. Nothing moves until the draft is
	submitted on its form."""
	from onedesk.one_ai import proposals
	from onedesk.one_inventory import ready

	if not frappe.has_permission("Stock Entry", "create"):
		return {"error": "The reader may not move stock."}
	source = source or ready.company().default_warehouse
	for warehouse in (source, to):
		if not warehouse or not frappe.db.exists("Warehouse", {"name": warehouse, "is_group": 0}):
			return {"error": f"{warehouse or 'Where from'} is not a warehouse stock can be kept in."}
	if source == to:
		return {"error": "The goods would go nowhere: both warehouses are the same."}
	if project and not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	rows = []
	for one in lines or []:
		code, qty = str(one.get("item") or ""), flt(one.get("qty"))
		item = frappe.db.get_value("Item", code, ["item_name", "stock_uom", "is_stock_item"], as_dict=True)
		if not item or not item.is_stock_item or qty <= 0:
			return {"error": f"{code} is not a stock item with a quantity to move."}
		rows.append(
			{
				"item_code": code,
				"item_name": item.item_name,
				"qty": qty,
				"transfer_qty": qty,
				"uom": item.stock_uom,
				"stock_uom": item.stock_uom,
				"conversion_factor": 1,
				"s_warehouse": source,
				"t_warehouse": to,
				"project": project,
			}
		)
	if not rows:
		return {"error": "Say what goes, item by item."}
	changes = {
		"stock_entry_type": "Material Transfer",
		"purpose": "Material Transfer",
		"from_warehouse": source,
		"to_warehouse": to,
		"project": project,
		"items": [{k: v for k, v in row.items() if v not in (None, "")} for row in rows],
	}
	return {
		"proposal": proposals.propose(
			"Create", "Stock Entry", changes={k: v for k, v in changes.items() if v not in (None, "")}, why=why
		),
		"state": "Proposed",
	}


def quote_comparison(
	request: Annotated[str, "The request for quotation, or the material request it was made from, such as PUR-RFQ-2026-00005."],
) -> dict:
	"""The quotes suppliers sent for a request, line by line: each supplier's
	rate in the company's money so a quote in euros compares, how long it
	holds, and who is cheapest on each line. An expired quote is said as
	expired and never counted cheapest."""
	if not frappe.has_permission("Supplier Quotation", "read"):
		return {"error": "The reader may not see supplier quotations."}
	asked = [request] if frappe.db.exists("Request for Quotation", request) else frappe.get_all(
		"Request for Quotation Item", filters={"material_request": request, "docstatus": 1}, pluck="parent", distinct=True
	)
	if not asked:
		return {"error": f"No request for quotation is {request}, and none was made from it."}
	quotes = {
		one.name: one
		for one in frappe.get_list(
			"Supplier Quotation",
			filters={"name": ["in", frappe.get_all(
				"Supplier Quotation Item", filters={"request_for_quotation": ["in", asked]}, pluck="parent", distinct=True
			) or [""]], "docstatus": ["<", 2]},
			fields=["name", "supplier", "supplier_name", "currency", "status", "valid_till", "docstatus", "grand_total"],
		)
	}
	rows = frappe.get_all(
		"Supplier Quotation Item",
		filters={"parent": ["in", list(quotes) or [""]]},
		fields=["parent", "item_code", "item_name", "qty", "uom", "rate", "base_rate", "lead_time_days"],
		order_by="idx",
	)
	lines: dict = {}
	for row in rows:
		quote = quotes[row.parent]
		lines.setdefault(row.item_code, {"item": row.item_code, "name": row.item_name, "offers": []})["offers"].append(
			{
				"supplier": quote.supplier_name or quote.supplier,
				"quote": quote.name,
				"rate": flt(row.rate),
				"currency": quote.currency,
				"rate_in_company_money": flt(row.base_rate),
				"qty": flt(row.qty),
				"unit": row.uom,
				"days_to_deliver": row.lead_time_days or None,
				"expired": quote.status == "Expired",
				"draft": quote.docstatus == 0,
			}
		)
	for line in lines.values():
		live = [one for one in line["offers"] if not one["expired"]]
		if live:
			line["cheapest"] = min(live, key=lambda one: one["rate_in_company_money"])["supplier"]
	asked_of = frappe.get_all("Request for Quotation Supplier", filters={"parent": ["in", asked]}, pluck="supplier_name")
	return {
		"requests": asked,
		"asked": sorted(set(one for one in asked_of if one)),
		"quotes": [
			{
				"quote": one.name,
				"supplier": one.supplier_name or one.supplier,
				"total": flt(one.grand_total),
				"currency": one.currency,
				"valid_till": str(one.valid_till) if one.valid_till else None,
				"status": one.status,
			}
			for one in quotes.values()
		],
		"lines": list(lines.values()),
	}


def late_orders() -> dict:
	"""The reader's purchase orders with goods past the date they were wanted
	and not all here, the oldest first: from whom, what, since when and who
	ordered it. Services and closed orders are left out."""
	from onedesk.one_inventory import tell

	if not frappe.has_permission("Purchase Order", "read"):
		return {"error": "The reader may not see purchase orders."}
	day = frappe.utils.getdate(frappe.utils.today())
	out = []
	for one in tell.late():
		if not frappe.has_permission("Purchase Order", "read", doc=one.name):
			continue
		out.append(
			{
				"order": one.name,
				"supplier": one.supplier_name or one.supplier,
				"items": one["items"],
				"wanted_by": str(one.due),
				"late_by_days": (day - frappe.utils.getdate(one.due)).days,
				"ordered_by": get_fullname(one.owner),
			}
		)
	return {"orders": out, "count": len(out)}


def plan_quote_request(
	request: Annotated[str, "The material request to ask prices for, such as MAT-MR-2026-00006."],
	suppliers: Annotated[list[str], "The suppliers to ask, by name, such as Al Noor Aluminium."],
	message: Annotated[str, "What the suppliers are told, in a sentence or two."] | None = None,
	why: Annotated[str, "In a sentence, why this request."] | None = None,
) -> dict:
	"""Suggest a draft request for quotation for what a material request still
	needs, asking each supplier named, as a card the reader approves. ERPNext
	makes its lines from the request, so each quote can be ordered against
	it. Nothing is sent until the draft is submitted and mailed from its form."""
	from erpnext.stock.doctype.material_request.mapper import make_request_for_quotation

	from onedesk.one_ai import proposals

	if not frappe.has_permission("Request for Quotation", "create"):
		return {"error": "The reader may not ask suppliers for prices."}
	if not frappe.db.exists("Material Request", request) or not frappe.has_permission("Material Request", "read", doc=request):
		return {"error": f"No material request the reader may see is {request}."}
	if frappe.db.get_value("Material Request", request, "docstatus") != 1:
		return {"error": f"{request} is not submitted, so prices cannot be asked for it yet."}
	named = []
	for one in suppliers or []:
		found = frappe.db.get_value("Supplier", {"name": one}) or frappe.db.get_value("Supplier", {"supplier_name": one})
		if not found:
			return {"error": f"No supplier is called {one}."}
		named.append(found)
	if not named:
		return {"error": "Say which suppliers to ask."}
	drafted = make_request_for_quotation(request)
	if not drafted.items:
		return {"error": f"Everything on {request} is ordered already."}
	keep = ("item_code", "item_name", "description", "qty", "uom", "stock_uom", "conversion_factor", "warehouse", "schedule_date", "material_request", "material_request_item", "project_name")
	changes = {
		"transaction_date": frappe.utils.today(),
		"message_for_supplier": message or drafted.get("message_for_supplier"),
		"suppliers": [{"supplier": one, "send_email": 1} for one in dict.fromkeys(named)],
		"items": [
			{key: str(row.get(key)) if key == "schedule_date" and row.get(key) else row.get(key) for key in keep if row.get(key) not in (None, "")}
			for row in drafted.items
		],
	}
	return {
		"proposal": proposals.propose(
			"Create", "Request for Quotation", changes={k: v for k, v in changes.items() if v not in (None, "")}, why=why
		),
		"state": "Proposed",
	}


def running_low() -> dict:
	"""The items the reader may see at or below their reorder level in a
	warehouse, by what is there and on its way less what is promised (as
	ERPNext's own reordering reads it), with what is already on order."""
	if not frappe.has_permission("Bin", "read"):
		return {"error": "The reader may not see stock levels."}
	levels = frappe.get_all(
		"Item Reorder",
		filters={"parenttype": "Item", "warehouse_reorder_level": [">", 0]},
		fields=["parent", "warehouse", "warehouse_reorder_level", "warehouse_reorder_qty"],
	)
	readable = (
		set(
			frappe.get_list(
				"Item",
				filters={"name": ["in", list({one.parent for one in levels})], "disabled": 0},
				pluck="name",
			)
		)
		if levels
		else set()
	)
	low = []
	for one in levels:
		if one.parent not in readable:
			continue
		row = (
			frappe.db.get_value(
				"Bin",
				{"item_code": one.parent, "warehouse": one.warehouse},
				["actual_qty", "projected_qty", "ordered_qty"],
				as_dict=True,
			)
			or frappe._dict()
		)
		if flt(row.projected_qty) <= flt(one.warehouse_reorder_level):
			low.append(
				{
					"item": one.parent,
					"name": frappe.db.get_value("Item", one.parent, "item_name"),
					"warehouse": one.warehouse,
					"on_hand": flt(row.actual_qty),
					"on_its_way_less_promised": flt(row.projected_qty),
					"reorder_level": flt(one.warehouse_reorder_level),
					"orders": flt(one.warehouse_reorder_qty),
					"on_order": flt(row.ordered_qty),
				}
			)
	return {
		"low": low,
		"count": len(low),
		"next": "To Order in OneInventory's Buying lists them and makes the orders.",
	}


def plan_item_change(
	item: Annotated[str, "The item's code, as the page names it."],
	item_name: Annotated[str, "Its new name."] | None = None,
	item_group: Annotated[str, "The item group it goes in."] | None = None,
	disabled: Annotated[bool, "True to stop it being used on new documents, False to use it again."]
	| None = None,
	warehouse: Annotated[str, "The warehouse a reorder level is for."] | None = None,
	reorder_level: Annotated[float, "Order more once what is there and coming falls to this."] | None = None,
	reorder_qty: Annotated[float, "How many to order each time."] | None = None,
	lead_time_days: Annotated[int, "How many days it takes to arrive once ordered."] | None = None,
	why: Annotated[str, "In a sentence, why this change."] | None = None,
) -> dict:
	"""Suggest a change to an item as its page makes it, as a card the reader
	approves: its name, its group, whether it is disabled, its lead time, or
	the reorder level and quantity for a warehouse. Approving saves the item,
	so ERPNext's own checks hold."""
	from onedesk.one_ai import proposals

	if not frappe.db.exists("Item", item) or not frappe.has_permission("Item", "write", doc=item):
		return {"error": "There is no such item the reader may change."}
	held = frappe.get_doc("Item", item)
	changes = {}
	if item_name and item_name != held.item_name:
		changes["item_name"] = item_name
	if item_group and item_group != held.item_group:
		if not frappe.db.exists("Item Group", item_group):
			return {"error": f"There is no item group called {item_group}. Ask which one they meant."}
		changes["item_group"] = item_group
	if disabled is not None and int(bool(disabled)) != held.disabled:
		changes["disabled"] = int(bool(disabled))
	if lead_time_days is not None and int(lead_time_days) != held.lead_time_days:
		changes["lead_time_days"] = int(lead_time_days)
	if reorder_level is not None or reorder_qty is not None:
		if not warehouse or not frappe.db.exists("Warehouse", warehouse):
			return {"error": "A reorder level is for a warehouse. Ask which one."}
		rows = [
			{
				"warehouse": one.warehouse,
				"warehouse_reorder_level": one.warehouse_reorder_level,
				"warehouse_reorder_qty": one.warehouse_reorder_qty,
				"material_request_type": one.material_request_type,
			}
			for one in held.get("reorder_levels") or []
		]
		row = next((one for one in rows if one["warehouse"] == warehouse), None)
		if not row:
			row = {
				"warehouse": warehouse,
				"warehouse_reorder_level": 0,
				"warehouse_reorder_qty": 0,
				"material_request_type": held.default_material_request_type or "Purchase",
			}
			rows.append(row)
		if reorder_level is not None:
			row["warehouse_reorder_level"] = flt(reorder_level)
		if reorder_qty is not None:
			row["warehouse_reorder_qty"] = flt(reorder_qty)
		changes["reorder_levels"] = rows
	if not changes:
		return {"error": "The item already is as asked. Say so."}
	return {
		"proposal": proposals.propose("Edit", "Item", changes=changes, record=item, why=why),
		"state": "Proposed",
	}


def _last(last) -> dict | None:
	return {"rate": last.rate, "supplier": last.supplier, "on": str(last.on_date), "kind": last.kind} if last else None


def _order(one) -> dict:
	return {
		"order": one.name,
		"with": one.party,
		"due": str(one.due) if one.due else None,
		"still_to_come": one.left,
		"late": one.late,
	}


# ------------------------------------------------------------------ making


def _steps(order) -> list[dict]:
	return [
		{
			"step": row.operation,
			"workstation": row.workstation,
			"done": flt(row.completed_qty),
			"of": flt(order.qty),
			"minutes_planned": flt(row.time_in_mins),
			"minutes_taken": flt(row.actual_operation_time),
		}
		for row in order.operations
	]


def work_in_hand(
	project: Annotated[str, "Only the work orders for this project, by name or title."] | None = None,
) -> dict:
	"""The work orders not finished yet that the reader may see: what each
	makes, for which project, how many are made, each step's progress, when it
	is wanted and whether that has passed."""
	if not frappe.has_permission("Work Order", "read"):
		return {"error": "The reader may not see work orders."}
	filters = {"docstatus": 1, "status": ["in", ("Not Started", "In Process")]}
	if project:
		filters["project"] = frappe.db.get_value("Project", {"name": project}) or frappe.db.get_value("Project", {"project_name": project})
		if not filters["project"]:
			return {"error": f"No project is called {project}."}
	day = frappe.utils.getdate(frappe.utils.today())
	out = []
	for name in frappe.get_all("Work Order", filters=filters, order_by="expected_delivery_date asc", pluck="name"):
		if not frappe.has_permission("Work Order", "read", doc=name):
			continue
		order = frappe.get_doc("Work Order", name)
		wanted = frappe.utils.getdate(order.expected_delivery_date) if order.expected_delivery_date else None
		out.append(
			{
				"order": order.name,
				"makes": order.item_name,
				"qty": flt(order.qty),
				"made": flt(order.produced_qty),
				"unit": order.stock_uom,
				"status": order.status,
				"project": frappe.db.get_value("Project", order.project, "project_name") if order.project else None,
				"wanted_by": str(wanted) if wanted else None,
				"late": bool(wanted and wanted < day),
				"steps": _steps(order),
			}
		)
	return {"orders": out, "count": len(out)}


def on_the_floor(
	workstation: Annotated[str, "Only the steps at this workstation, by name."] | None = None,
) -> dict:
	"""What the Shop Floor shows now: how many work orders are open, each step
	someone is on and for how long, the paused ones, those waiting to start, and
	the steps short of materials."""
	from onedesk.one_inventory import floor

	if not frappe.has_permission("Job Card", "read"):
		return {"error": "The reader may not see job cards."}
	filters = {"docstatus": 0, "is_subcontracted": 0}
	if workstation:
		filters["workstation"] = frappe.db.get_value("Workstation", {"name": workstation}) or frappe.db.get_value(
			"Workstation", {"workstation_name": workstation}
		)
		if not filters["workstation"]:
			return {"error": f"No workstation is called {workstation}."}
	steps = []
	for card in frappe.get_list(
		"Job Card",
		filters=filters,
		fields=["name", "operation", "workstation", "work_order", "item_name", "status", "is_paused", "for_quantity", "total_completed_qty"],
		order_by="expected_start_date asc, name asc",
	):
		logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": card.name},
			fields=["employee", "from_time", "to_time", "time_in_mins"],
		)
		open_log = next((log for log in logs if not log.to_time), None)
		minutes = sum(flt(log.time_in_mins) for log in logs if log.to_time)
		if open_log and not card.is_paused:
			minutes += (frappe.utils.now_datetime() - frappe.utils.get_datetime(open_log.from_time)).total_seconds() / 60
		people = sorted({log.employee for log in logs if log.employee})
		short = [
			row.get("item_name")
			for row in floor.shop_floor.get_job_card_materials(card.name)
			if row.get("status") == "short"
		]
		steps.append(
			{
				"job_card": card.name,
				"step": card.operation,
				"workstation": card.workstation,
				"work_order": card.work_order,
				"makes": card.item_name,
				"state": "running" if floor.running_now(card) else "paused" if card.is_paused else "waiting" if card.status == "Open" else card.status,
				"done": flt(card.total_completed_qty),
				"of": flt(card.for_quantity),
				"minutes": round(minutes),
				"people": [frappe.db.get_value("Employee", who, "employee_name") or who for who in people],
				"short_of": short,
			}
		)
	return {"figures": floor.figures(), "steps": steps}


def work_order_facts(work_order: Annotated[str, "The work order's number, such as MFG-WO-2026-00006."]) -> dict:
	"""One work order as the floor sees it: what it makes and for whom, each
	material needed against what went to the floor and what the stores still
	hold, each step's job cards, and what making it has cost so far."""
	if not frappe.db.exists("Work Order", work_order) or not frappe.has_permission("Work Order", "read", doc=work_order):
		return {"error": f"No work order the reader may see is {work_order}."}
	order = frappe.get_doc("Work Order", work_order)
	materials = []
	for row in order.required_items:
		needed = flt(row.required_qty)
		sent = flt(row.transferred_qty)
		held = flt(frappe.db.get_value("Bin", {"item_code": row.item_code, "warehouse": row.source_warehouse}, "actual_qty")) if row.source_warehouse else 0
		materials.append(
			{
				"item": row.item_name or row.item_code,
				"needed": needed,
				"sent_to_the_floor": sent,
				"used": flt(row.consumed_qty),
				"in_the_stores": held,
				"short": max(needed - sent - held, 0),
				"unit": row.stock_uom,
			}
		)
	cards = frappe.get_all(
		"Job Card",
		filters={"work_order": order.name, "docstatus": ["<", 2]},
		fields=["name", "operation", "status", "total_completed_qty", "for_quantity"],
	)
	made = frappe.get_all(
		"Stock Entry",
		filters={"work_order": order.name, "purpose": "Manufacture", "docstatus": 1},
		fields=[{"SUM": "total_outgoing_value", "as": "used"}, {"SUM": "total_additional_costs", "as": "time"}],
	)[0]
	return {
		"order": order.name,
		"makes": order.item_name,
		"qty": flt(order.qty),
		"made": flt(order.produced_qty),
		"status": order.status,
		"project": frappe.db.get_value("Project", order.project, "project_name") if order.project else None,
		"asked_by": get_fullname(frappe.db.get_value("Material Request", order.material_request, "owner")) if order.material_request else None,
		"wanted_by": str(order.expected_delivery_date) if order.expected_delivery_date else None,
		"materials": materials,
		"steps": _steps(order),
		"job_cards": [dict(one) for one in cards],
		"cost_so_far": {"materials": flt(made.used), "workshop_time": flt(made.time)},
	}


def plan_work_order(
	item: Annotated[str, "The item to make, by code or name, such as WIN-CS12."],
	qty: Annotated[float, "How many to make, in the item's own unit."],
	project: Annotated[str, "The project it is made for, by name or title."] | None = None,
	wanted_by: Annotated[str, "When it is wanted, as YYYY-MM-DD."] | None = None,
	why: Annotated[str, "In a sentence, why it is made."] | None = None,
) -> dict:
	"""Suggest a draft work order to make an item with its default bill of
	materials, as a card the reader approves. Its materials and steps come from
	the bill, and it takes them from the company's stores to its work in
	progress. Nothing is made until it is submitted."""
	from erpnext import get_default_company

	from onedesk.one_ai import proposals

	if not frappe.has_permission("Work Order", "create"):
		return {"error": "The reader may not make work orders."}
	code = frappe.db.get_value("Item", {"name": item}) or frappe.db.get_value("Item", {"item_name": item})
	if not code:
		return {"error": f"No item is called {item}."}
	bom = frappe.db.get_value("BOM", {"item": code, "is_default": 1, "is_active": 1, "docstatus": 1})
	if not bom:
		return {"error": f"{code} has no bill of materials to make it from."}
	if flt(qty) <= 0:
		return {"error": "Say how many to make."}
	changes = {"production_item": code, "bom_no": bom, "qty": flt(qty), "company": get_default_company()}
	if project:
		found = frappe.db.get_value("Project", {"name": project}) or frappe.db.get_value("Project", {"project_name": project})
		if not found:
			return {"error": f"No project is called {project}."}
		changes["project"] = found
	if wanted_by:
		changes["expected_delivery_date"] = str(frappe.utils.getdate(wanted_by))
	return {
		"proposal": proposals.propose("Create", "Work Order", changes={k: v for k, v in changes.items() if v}, why=why),
		"state": "Proposed",
	}



def _asset_named(asset: str) -> str | None:
	return frappe.db.get_value("Asset", {"name": asset}) or frappe.db.get_value("Asset", {"asset_name": asset})


def asset_facts(asset: Annotated[str, "The asset, by its number or its name, such as Pickup Truck 1."]) -> dict:
	"""One piece of equipment as its page says it: who has it and where it is
	kept, what it cost and is worth now, its next service and whether it is
	late, its repairs and what they cost, and changes to its value."""
	from onedesk.one_inventory import assets
	from onedesk.one_inventory.maintenance import next_service

	name = _asset_named(asset)
	if not name or not frappe.has_permission("Asset", "read", doc=name):
		return {"error": f"No asset the reader may see is {asset}."}
	doc = frappe.get_doc("Asset", name)
	said = assets.said(name)
	service = next_service(name) if doc.maintenance_required else None
	repairs = frappe.get_all(
		"Asset Repair",
		filters={"asset": name, "docstatus": ["<", 2]},
		fields=["name", "repair_status", "failure_date", "completion_date", "total_repair_cost", "description"],
		order_by="failure_date desc",
	)
	return {
		"asset": doc.name,
		"name": doc.asset_name,
		"item": doc.item_name or doc.item_code,
		"status": doc.status,
		"held_by": said["custodian_name"],
		"kept_at": doc.location,
		"cost": flt(said["cost"]),
		"worth_now": flt(said["worth"]),
		"next_service": {
			"task": service.task_name,
			"due": str(service.due_date),
			"late": frappe.utils.getdate(service.due_date) < frappe.utils.getdate(frappe.utils.today()),
		}
		if service
		else None,
		"repairs": [
			{
				"status": one.repair_status,
				"failed_on": str(one.failure_date),
				"mended_on": str(one.completion_date) if one.completion_date else None,
				"cost": flt(one.total_repair_cost),
				"what": one.description,
			}
			for one in repairs
		],
		"value_changes": [
			dict(one)
			for one in frappe.get_all(
				"Asset Value Adjustment",
				filters={"asset": name, "docstatus": 1},
				fields=["date", "current_asset_value as was", "new_asset_value as now"],
			)
		],
	}


def equipment_held(
	employee: Annotated[str, "Whose equipment, by employee number or name. The reader's own when left out."] | None = None,
) -> dict:
	"""The company's equipment a person holds: what each is and where it is
	kept. Read as the reader may see assets."""
	if not frappe.has_permission("Asset", "read"):
		return {"error": "The reader may not see the company's equipment."}
	if employee:
		found = frappe.db.get_value("Employee", {"name": employee}) or frappe.db.get_value("Employee", {"employee_name": employee})
	else:
		found = frappe.db.get_value("Employee", {"user_id": frappe.session.user})
	if not found:
		return {"error": f"No employee is called {employee}." if employee else "The reader has no employee record."}
	held = frappe.get_list(
		"Asset",
		filters={"custodian": found, "docstatus": 1},
		fields=["name", "asset_name", "item_name", "location", "status"],
		order_by="asset_name",
	)
	return {
		"employee": frappe.db.get_value("Employee", found, "employee_name"),
		"held": [dict(one) for one in held],
		"count": len(held),
	}


def services_due() -> dict:
	"""Services on the company's equipment that are late or due within a
	month, soonest first, with who does each. Read as the reader may see the
	services."""
	from frappe.utils import add_days, getdate, today

	if not frappe.has_permission("Asset Maintenance Log", "read"):
		return {"error": "The reader may not see services."}
	day = getdate(today())
	out = []
	for one in frappe.get_list(
		"Asset Maintenance Log",
		filters={"docstatus": 0, "maintenance_status": ["in", ["Planned", "Overdue"]], "due_date": ["<=", add_days(day, 30)]},
		fields=["name", "asset_maintenance", "task_name", "due_date", "assign_to_name"],
		order_by="due_date asc",
	):
		out.append(
			{
				"service": one.name,
				"asset": frappe.db.get_value("Asset", one.asset_maintenance, "asset_name") or one.asset_maintenance,
				"task": one.task_name,
				"due": str(one.due_date),
				"late": getdate(one.due_date) < day,
				"done_by": one.assign_to_name,
			}
		)
	return {"services": out, "late": sum(1 for one in out if one["late"])}


def plan_handover(
	asset: Annotated[str, "The asset, by its number or its name, such as Laptop Mariam."],
	employee: Annotated[str, "Who is given it, by employee number or name."],
	why: Annotated[str, "In a sentence, why it is handed over."] | None = None,
) -> dict:
	"""Suggest handing a piece of equipment to a person, from whoever has it
	now, as a card the reader approves. It is a draft handover until it is
	submitted, which tells the person and makes the sheet they sign."""
	from erpnext import get_default_company

	from onedesk.one_ai import proposals

	if not frappe.has_permission("Asset Movement", "create"):
		return {"error": "The reader may not hand equipment over."}
	name = _asset_named(asset)
	if not name:
		return {"error": f"No asset is called {asset}."}
	to = frappe.db.get_value("Employee", {"name": employee, "status": "Active"}) or frappe.db.get_value(
		"Employee", {"employee_name": employee, "status": "Active"}
	)
	if not to:
		return {"error": f"Nobody working here is called {employee}."}
	holder = frappe.db.get_value("Asset", name, "custodian")
	if holder == to:
		return {"error": f"{employee} already has it."}
	row = {"asset": name, "to_employee": to}
	if holder:
		row["from_employee"] = holder
	changes = {
		"purpose": "Issue",
		"company": get_default_company(),
		"transaction_date": str(frappe.utils.now_datetime()),
		"assets": [row],
	}
	return {"proposal": proposals.propose("Create", "Asset Movement", changes=changes, why=why), "state": "Proposed"}
