"""What OneAI does in OneInventory: reads an item as its page shows it, says
what the stores hold, what is running low, what came in on a receipt and what
is still to arrive, drafts a receipt for an order, and suggests a change to an item as its page makes it,
as a card the reader approves.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import flt

#: An item's page (page/item_view), by its open view, from `?view=`.
PAGE = "item-view"
#: Stock on Hand (page/stock_on_hand).
STOCK = "stock-on-hand"

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

SUGGESTIONS = {
	f"page:{PAGE}": [_HOW, _ORDER, _CHANGE],
	f"page:{PAGE}/stock": [_HOW, _ORDER],
	f"page:{PAGE}/buying": [_ORDER, _HOW],
	"Item": [_LOW, _HOW],
	f"page:{STOCK}": [_LOW, _HELD],
	"Warehouse": [_WORTH, _LOW],
	"Purchase Receipt": [_RECEIVED, _ARRIVING],
	"Purchase Order": [_RECEIVE, _ARRIVING],
	"Delivery Note": [_SENT, _TO_DELIVER],
	"Sales Order": [_DELIVER, _TO_DELIVER],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on an item's page or Stock on Hand."""
	if said.get("page") == STOCK:
		return (
			"The reader is on Stock on Hand, which lists what each item has on hand, free to sell, on order and "
			"its worth, in every warehouse or one. stock_on_hand reads it as the page shows it. How the page works "
			"is in OneInventory's documentation (how_to)."
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
				"last_ordered": str(one["last"]) if one["last"] else None,
				"default": one["default"],
			}
			for one in buying.get("suppliers") or []
		],
		"purchase_orders": [_order(one) for one in buying.get("orders") or []],
		"sales_orders": [_order(one) for one in selling.get("orders") or []],
		"made_from": [
			{"item": one.item_name, "qty": one.qty, "unit": one.uom} for one in making.get("materials") or []
		],
		"being_made": [
			{"work_order": one.name, "qty": one.qty, "made": one.produced_qty, "project": one.project}
			for one in making.get("orders") or []
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
	return {"rate": last.rate, "supplier": last.supplier, "on": str(last.on_date)} if last else None


def _order(one) -> dict:
	return {
		"order": one.name,
		"with": one.party,
		"due": str(one.due) if one.due else None,
		"still_to_come": one.left,
		"late": one.late,
	}
