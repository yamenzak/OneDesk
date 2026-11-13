"""What OneAI does in OneInventory: reads items, the stores, receipts,
deliveries, movements, counts, buying and equipment as the reader sees
them, and drafts what it suggests there as a card the reader
approves. AGENTS.md lists each tool.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import flt, get_fullname

# What OneAI changes in OneInventory: every change it suggests is a card of
# its own kind (plan_*), so each call below is left to a person, and why.
REACH = {}

NOT_FOR_AI = {
	"custody.give": "OneAI hands equipment over its own way, as a card from plan_handover.",
	"custody.take_back": "Taking equipment back is done with the thing in hand, by whoever receives it.",
	"kinds.make": "OneAI suggests an item's changes with plan_item_change, and a new item's prices and opening stock are a person's to say.",
	"order.order": "OneAI asks for prices with plan_quote_request, and an order to a supplier is a person's to place.",
	"parts.add": "It adds the parts a person has checked in the list they gave.",
	"parts.read": "It reads a list of parts the person gives and changes nothing until they add them.",
	"portal.send_quote": "It is a supplier's own answer, given on the portal.",
	"quotes.ask": "OneAI asks suppliers for prices its own way, as a card from plan_quote_request.",
	"quotes.order_cheapest": "An order to a supplier is a person's to place, from the quotes OneAI compares.",
	"ready.fix": "What Inventory Check fixes changes how the whole workspace keeps stock, so a manager presses Fix.",
	"stock.issue": "Stock used is recorded by whoever took it off the shelf, and OneAI moves stock as a card from plan_transfer.",
	"stock.transfer": "OneAI moves stock its own way, as a card from plan_transfer.",
	"upkeep.done": "A service is recorded done by whoever did it.",
}

STOCK = "stock-on-hand"
HOME = "inventory"

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
	"expects": "about_record",
}
_TO_DELIVER = {
	"label": _lt("What is still to deliver?"),
	"ask": _lt("What is still to deliver to customers, what is late, and is the stock there for it?"),
	"expects": "still_to_deliver",
}
_DELIVER = {
	"label": _lt("Deliver this order"),
	"ask": _lt("Draft a delivery for what is still to go out on this order."),
	"can": "create",
	"doctype": "Delivery Note",
	"expects": "plan_delivery",
}

_MOVED = {
	"label": _lt("What did this movement do?"),
	"ask": _lt("What did this stock movement do? Say from where to where, for which project, what it was worth and who made it."),
	"can": "read",
	"doctype": "Stock Entry",
	"expects": "read_record",
}
_SEND = {
	"label": _lt("Send stock to a site"),
	"ask": _lt("Draft a transfer of stock from the stores to a site or another warehouse."),
	"can": "create",
	"doctype": "Stock Entry",
	"expects": "plan_transfer",
}
_COUNT = {
	"label": _lt("Record a count…"),
	"ask": _lt("Record a stock count of this warehouse. I will say what I counted of each item."),
	"can": "create",
	"doctype": "Stock Reconciliation",
	"expects": "plan_count",
}
_COUNTED = {
	"label": _lt("What did this count find?"),
	"ask": _lt("What did this stock count find? Say what the books held and what was counted, and what it did to the books."),
	"can": "read",
	"expects": "read_record",
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
	"expects": "quotes_now",
}
_BROKEN = {
	"label": _lt("What is out of order?"),
	"ask": _lt("Which equipment is out of order, since when and what is wrong, and what did repairs cost this year?"),
	"can": "read",
	"expects": "upkeep_now",
}
_UNANSWERED = {
	"label": _lt("Who has not answered?"),
	"ask": _lt("Which suppliers have not answered a request for prices yet, what were they asked for and since when?"),
	"can": "read",
	"expects": "quotes_now",
}
_CHEAPEST = {
	"label": _lt("Who is cheapest?"),
	"ask": _lt("For the newest request for prices, who is cheapest on each line, and which quotes run out soon?"),
	"can": "read",
	"expects": "quotes_now",
}
_COMPARE_HERE = {key: value for key, value in _COMPARE.items() if key != "doctype"}
_LATE = {
	"label": _lt("Which orders are late?"),
	"ask": _lt("Which purchase orders are late, from whom, since when, and what is still to come on each?"),
	"can": "read",
	"expects": "still_to_arrive",
}

_GOING_OFF = {
	"label": _lt("Which lots go off soon?"),
	"ask": _lt("Which lots go off within a month or have gone off, how much is left of each and where is it?"),
	"can": "read",
	"expects": "lots_and_numbers",
}
_WHERE_NUMBER = {
	"label": _lt("Where is each numbered piece?"),
	"ask": _lt("Which numbered pieces are in stock and where, which went to a customer, and whose warranty ends soon?"),
	"can": "read",
	"expects": "lots_and_numbers",
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
	"expects": "upkeep_now",
}
_HAND = {
	"label": _lt("Hand this to somebody…"),
	"ask": _lt("Hand this asset to "),
	"fill": True,
	"can": "write",
	"doctype": "Asset",
	"expects": "plan_handover",
}

SUGGESTIONS = {
	"Item": [_HOW, _ORDER, _CHANGE],
	f"page:{STOCK}": [_LOW, _HELD],
	f"page:{HOME}": [_LATE, _LOW, _DUE],
	"Asset Repair": [_BROKEN],
	"Batch": [_GOING_OFF],
	"Serial No": [_WHERE_NUMBER],
	"Warehouse": [_WORTH, _LOW, _COUNT],
	"Purchase Receipt": [_RECEIVED, _ARRIVING],
	"Purchase Order": [_RECEIVE, _LATE, _ARRIVING],
	"Material Request": [_ASK, _COMPARE],
	"Request for Quotation": [_COMPARE],
	"Supplier Quotation": [_COMPARE_HERE],
	"Delivery Note": [_SENT, _TO_DELIVER],
	"Sales Order": [_DELIVER, _TO_DELIVER],
	"Stock Entry": [_MOVED, _SEND],
	"Stock Reconciliation": [_COUNTED],
	"Asset": [_ASSET, _HAND, _DUE],
	"Asset Maintenance Log": [_DUE],
	"Asset Maintenance": [_DUE],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on Stock on Hand, Home or Reorder."""
	if said.get("page") == STOCK:
		return (
			"The reader is on Stock on Hand, which lists what each item has on hand, free to sell, on order and "
			"its worth, in every warehouse or one. stock_on_hand reads it as the page shows it. How the page works "
			"is in OneInventory's documentation (how_to)."
		)
	if said.get("page") == HOME:
		return (
			"The reader is on OneInventory's Home, which shows the orders late, the items running low, the lots "
			"going off, the services due and the drafts left, and everything in "
			"OneInventory with what it is for. still_to_arrive with late_only, running_low and upkeep_now read "
			"those; how each "
			"part works is in OneInventory's documentation (how_to)."
		)
	if said.get("page") == "to-order":
		return (
			"The reader is on Reorder, which lists the items at or below their reorder level in each warehouse, "
			"with what is on hand, already ordered and promised, and orders for them. running_low reads it as the "
			"page shows it. How the page works is in OneInventory's documentation (how_to)."
		)
	return None


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
	warehouse: Annotated[str, "Only this warehouse, by its name, such as Stores."] | None = None,
	search: Annotated[str, "Only items whose name or code has this in it."] | None = None,
) -> dict:
	"""What the stores hold now, as Stock on Hand shows it: each item's
	quantity on hand, free to sell (on hand less what is promised), on order
	and worth, where it is low and whether more is promised than is there,
	with what each warehouse holds and is worth. Read before answering what is
	in stock, short or worth what."""
	from onedesk.one_inventory import stock

	if warehouse:
		found = _warehouse(warehouse, groups=True)
		if not found:
			return {"error": f"There is no warehouse called {warehouse}. Ask which one they meant."}
		warehouse = found
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
	late_only: Annotated[
		bool, "Only what is late, as one entry per order with its late lines and who ordered it."
	] = False,
) -> dict:
	"""What is ordered from suppliers and not yet received, as the reader's
	purchase orders say it: each order's lines still to come, when they were
	due, and which are late, the latest first. With late_only, the late orders
	only, oldest first: from whom, what, since when and who ordered it."""
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
			fields=["name", "supplier", "supplier_name", "currency", "project", "owner"],
			limit_page_length=0,
		)
	}
	if not orders:
		return {"orders": [], "count": 0} if late_only else {"lines": [], "count": 0}
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
	if late_only:
		return _late_by_order([one for one in lines if one["late_by_days"]], orders)
	return {"lines": lines[:60], "count": len(lines), "late": sum(1 for one in lines if one["late_by_days"])}


def _late_by_order(lines: list[dict], orders: dict) -> dict:
	"""`still_to_arrive`'s late lines, one entry per order, the latest first."""
	grouped: dict = {}
	for one in lines:
		order = orders[one["order"]]
		held = grouped.setdefault(
			one["order"],
			{
				"order": one["order"],
				"supplier": one["supplier"],
				"project": one["project"],
				"ordered_by": get_fullname(order.owner),
				"late_by_days": one["late_by_days"],
				"lines": [],
			},
		)
		held["late_by_days"] = max(held["late_by_days"], one["late_by_days"])
		held["lines"].append(
			{key: one[key] for key in ("item", "name", "still_to_come", "unit", "due", "late_by_days")}
		)
	out = sorted(grouped.values(), key=lambda one: -one["late_by_days"])
	return {"orders": out[:30], "count": len(out)}


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
	card the reader approves. It is filled from the order as the order's own
	Make button fills it, with what is still to come on each line unless told less. Nothing is received until the draft
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
	the reader approves. It is filled from the order as the order's own Make
	button fills it, with what is still to go on each line unless told less. Nothing leaves the stores until the
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


def _warehouse(said: str | None, groups: bool = False) -> str | None:
	"""The warehouse the reader means: by its full name (Stores - ABC), or by
	its plain name (Stores) in their company; one stock is kept in, unless
	`groups`."""
	from erpnext import get_default_company

	if not said:
		return None
	kept = {} if groups else {"is_group": 0}
	return frappe.db.get_value("Warehouse", {"name": said, **kept}) or frappe.db.get_value(
		"Warehouse", {"warehouse_name": said, "company": get_default_company(), **kept}
	)


def _item(said: str | None) -> str | None:
	"""The item the reader means, by its code or by its name, said once or
	more than once (Concealed Hinges)."""
	if not said:
		return None
	for name in (said, said[:-1] if said.endswith("s") else None, said[:-2] if said.endswith("es") else None):
		found = name and (frappe.db.exists("Item", name) or frappe.db.get_value("Item", {"item_name": name, "disabled": 0}))
		if found:
			return found
	return None


def plan_transfer(
	to: Annotated[str, "The warehouse the goods go to, by its name, such as Branch Store."],
	lines: Annotated[list[dict], "What goes: each {item: its code or name, qty: how many}."],
	source: Annotated[str, "The warehouse they come from. The company's default one when not said."] | None = None,
	project: Annotated[str, "The project they are for, when they are for one."] | None = None,
	why: Annotated[str, "In a sentence, why this transfer."] | None = None,
) -> dict:
	"""When the reader wants stock moved ("send 20 hinges to the site"),
	suggest a draft transfer of stock from one warehouse to another, a
	site's among them, as a card the reader approves. It prints as a transfer
	note that travels with the goods. Nothing moves until the draft is
	submitted on its form."""
	from onedesk.one_ai import proposals
	from onedesk.one_inventory import ready

	if not frappe.has_permission("Stock Entry", "create"):
		return {"error": "The reader may not move stock."}
	asked = (source, to)
	source, to = _warehouse(source) or (None if source else ready.company().default_warehouse), _warehouse(to)
	for warehouse, said in zip((source, to), asked, strict=True):
		if not warehouse:
			return {"error": f"{said or 'Where from'} is not a warehouse stock can be kept in."}
	if source == to:
		return {"error": "The goods would go nowhere: both warehouses are the same."}
	if project and not frappe.has_permission("Project", "read", doc=project):
		return {"error": f"No project the reader may see is {project}."}
	rows = []
	for one in lines or []:
		code, qty = _item(str(one.get("item") or "")) or str(one.get("item") or ""), flt(one.get("qty"))
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


def plan_count(
	warehouse: Annotated[str, "The warehouse that was counted, by its name, such as Stores."],
	counted: Annotated[list[dict], "What was found: each {item: its code or name, qty: how many were counted, batch: the batch, for an item kept in several}."],
	why: Annotated[str, "In a sentence, why this count."] | None = None,
) -> dict:
	"""When the reader says what they counted ("I counted 40 of X in the
	Stores"), suggest a draft stock count of that warehouse, as a card they
	approve: a line for each item counted, beside
	what the books say is there. Nothing changes in the books until the count
	is submitted on its form."""
	from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import get_items

	from onedesk.one_ai import proposals

	if not frappe.has_permission("Stock Reconciliation", "create"):
		return {"error": "The reader may not count stock."}
	place = frappe.db.get_value("Warehouse", _warehouse(warehouse) or "", ["name", "company"], as_dict=True)
	if not place or not frappe.has_permission("Warehouse", "read", doc=place.name):
		return {"error": f"{warehouse} is not a warehouse stock can be kept in."}
	now = frappe.utils.now_datetime()
	fields = {df.fieldname for df in frappe.get_meta("Stock Reconciliation Item").fields}
	rows = []
	for one in counted or []:
		code, qty, batch = _item(str(one.get("item") or "")) or str(one.get("item") or ""), one.get("qty"), one.get("batch")
		if qty is None or flt(qty) < 0 or not frappe.db.get_value("Item", code, "is_stock_item"):
			return {"error": f"{code} is not a stock item with a count."}
		held = get_items(place.name, now.date(), now.time().strftime("%H:%M:%S"), place.company, item_code=code)
		if batch:
			held = [row for row in held if row.get("batch_no") in (batch, frappe.db.get_value("Batch", {"batch_id": batch}))]
		if len(held) > 1:
			return {"error": f"{code} is kept in batches here: say how many of each batch were counted."}
		row = {key: value for key, value in (held[0] if held else {"item_code": code, "warehouse": place.name}).items() if key in fields and value not in (None, "")}
		row["qty"] = flt(qty)
		if row.get("batch_no") or row.get("serial_no"):
			row["use_serial_batch_fields"] = 1
		rows.append(row)
	if not rows:
		return {"error": "Say what was counted, item by item."}
	changes = {"purpose": "Stock Reconciliation", "company": place.company, "set_warehouse": place.name, "items": rows}
	return {"proposal": proposals.propose("Create", "Stock Reconciliation", changes=changes, why=why), "state": "Proposed"}


def late_orders() -> dict:
	"""The reader's purchase orders with goods past the date they were wanted
	and not all here, the oldest first: from whom, what, since when and who
	ordered it. Services and closed orders are left out.

	Home's late orders (home.needs_you), not one of OneAI's tools: OneAI reads
	`still_to_arrive(late_only=True)`."""
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
	suppliers: Annotated[list[str], "The suppliers to ask, by name, such as Northwind Supplies."],
	message: Annotated[str, "What the suppliers are told, in a sentence or two."] | None = None,
	why: Annotated[str, "In a sentence, why this request."] | None = None,
) -> dict:
	"""Suggest a draft request for quotation for what a material request still
	needs, asking each supplier named, as a card the reader approves. Its
	lines are made from the request, so each quote can be ordered against
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
	the system's own reordering reads it), with what is already on order."""
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
	so the item's own checks hold."""
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


def lots_and_numbers(
	item: Annotated[str, "Only this item's lots and numbers, by its code. Left out, every item."] | None = None,
	soon: Annotated[bool, "Only the lots going off within a month or gone off."] = False,
) -> dict:
	"""What is kept in lots and by number: how many lots are in stock and
	how many go off soon or have, each lot with what is left and where, and
	each serial number with where it is or who has it and its warranty."""
	from onedesk.one_inventory import lots

	if not frappe.has_permission("Batch", "read") and not frappe.has_permission("Serial No", "read"):
		return {"error": "The reader may not see lots or serial numbers."}
	if item and not frappe.db.exists("Item", item):
		return {"error": f"No item has the code {item}."}
	return {
		"figures": lots.figures(),
		"lots": [
			{
				"lot": one["batch_id"] or one["name"],
				"item": one["item_name"],
				"left": one["batch_qty"],
				"unit": one["stock_uom"],
				"goes_off": one["expiry_date"],
				"state": one["state"] or "Fine",
				"where": [{"warehouse": place["warehouse"], "qty": place["qty"]} for place in one["where"]],
			}
			for one in lots.lots(item=item, soon=1 if soon else 0)
		],
		"numbers": [
			{
				"number": one["serial_no"] or one["name"],
				"item": one["item_name"],
				"status": one["status"],
				"where": one["warehouse"] or None,
				"with": one["customer"] or None,
				"warranty_until": one["warranty_expiry_date"],
			}
			for one in lots.serials(item=item)
		],
	}


def quotes_now(
	request: Annotated[
		str,
		"Only this request's quotes compared line by line: a request for quotation, or the material request "
		"it was made from, such as PUR-RFQ-2026-00005.",
	]
	| None = None,
) -> dict:
	"""What the Quotes page shows: suppliers still to answer, quotes waiting
	for a decision or still drafts, quotes running out within a week, each
	request with who answered and who has not, and the newest answered
	request compared line by line. With request, that request's quotes
	instead: each supplier's rate in the company's money so a quote in euros
	compares, how long it holds, and who is cheapest on each line. An expired
	quote is never cheapest."""
	from onedesk.one_inventory import quotes

	if not frappe.has_permission("Request for Quotation", "read") and not frappe.has_permission("Supplier Quotation", "read"):
		return {"error": "The reader may not see requests for prices or quotes."}
	if request:
		return _compared_request(request)
	asked = quotes.asked()
	newest = next((one["name"] for one in asked if one["answered"]), None)
	compared = quotes.compare(newest) if newest else None
	return {
		"figures": quotes.figures(),
		"requests": [
			{
				"request": one["name"],
				"asks_for": one["what"],
				"asked_on": one["date"],
				"answered_by": [row["name"] for row in one["suppliers"] if row["answered"]],
				"not_answered": [row["name"] for row in one["suppliers"] if not row["answered"]],
				"ordered": one["ordered"],
			}
			for one in asked[:10]
		],
		"newest_compared": compared and {
			"request": compared["name"],
			"lines": [
				{"item": line["name"], "qty": line["qty"], "cheapest": line["cheapest"], "rates_in_company_money": {k: v["base_rate"] for k, v in line["offers"].items()}}
				for line in compared["lines"]
			],
			"quotes": [
				{"supplier": one["name"], "total": one["total"], "currency": one["currency"], "holds_until": one["valid_till"], "status": one["status"]}
				for one in compared["suppliers"]
				if one["quote"]
			],
		},
		"running_out": [
			{"quote": one["name"], "supplier": one["supplier_name"], "holds_until": one["valid_till"]}
			for one in quotes.quotes()
			if one["expiring"]
		],
	}


def _compared_request(request: str) -> dict:
	"""`quotes_now` for one request: `quotes.compare` for the request for
	quotation named, or for each made from the material request named."""
	from onedesk.one_inventory import quotes

	asked = [request] if frappe.db.exists("Request for Quotation", request) else frappe.get_all(
		"Request for Quotation Item", filters={"material_request": request, "docstatus": 1}, pluck="parent", distinct=True
	)
	compared = [one for one in (quotes.compare(name) for name in asked) if one]
	if not compared:
		return {"error": f"No request for quotation the reader may see is {request}, and none was made from it."}
	out = []
	for one in compared:
		named = {row["supplier"]: row["name"] for row in one["suppliers"]}
		out.append(
			{
				"request": one["name"],
				"for_material_requests": one["requests"],
				"currency": one["currency"],
				"asked": [row["name"] for row in one["suppliers"]],
				"not_answered": [row["name"] for row in one["suppliers"] if not row["quote"]],
				"quotes": [
					{
						"quote": row["quote"],
						"supplier": row["name"],
						"total": row["total"],
						"currency": row["currency"],
						"holds_until": row["valid_till"],
						"status": row["status"],
						"expired": row["expired"],
						"draft": row["draft"],
						"cheapest_on": row["cheapest_on"],
					}
					for row in one["suppliers"]
					if row["quote"]
				],
				"lines": [
					{
						"item": line["item"],
						"name": line["name"],
						"qty": line["qty"],
						"unit": line["uom"],
						"cheapest": named.get(line["cheapest"]) if line["cheapest"] else None,
						"ordered": line["ordered"],
						"offers": {
							named.get(supplier, supplier): {
								"rate": offer["rate"],
								"rate_in_company_money": offer["base_rate"],
								"days_to_deliver": offer["days"],
							}
							for supplier, offer in line["offers"].items()
						},
					}
					for line in one["lines"]
				],
			}
		)
	return {"compared": out}


def upkeep_now(
	days: Annotated[int, "The services late or due within this many days. 30 if not said."] = 30,
) -> dict:
	"""What the Upkeep page shows: services due this week and late, the
	services not done yet that are late or due within the days asked, soonest
	first, with who does each, the equipment out of order and since when, and
	what repairs cost over the last twelve months."""
	from frappe.utils import add_days, getdate, today

	from onedesk.one_inventory import upkeep

	if not frappe.has_permission("Asset Maintenance Log", "read") and not frappe.has_permission("Asset Repair", "read"):
		return {"error": "The reader may not see services or repairs."}
	until = add_days(getdate(today()), max(0, int(days if days is not None else 30)))
	due = upkeep.due()
	soon = [one for one in due if one["due_date"] and getdate(one["due_date"]) <= until]
	return {
		"figures": upkeep.figures(),
		"services": [
			{"asset": one["asset_name"], "job": one["task_name"], "due": one["due_date"], "late": one["late"], "done_by": one["assign_to_name"]}
			for one in soon
		],
		"services_later": len(due) - len(soon),
		"out_of_order": [
			{"asset": one["asset_name"], "wrong": one["description"], "since": one["failure_date"], "days": one["days_out"]}
			for one in upkeep.repairs()
			if one["open"]
		],
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


def services_due() -> dict:
	"""Services on the company's equipment that are late or due within a
	month, soonest first, with who does each. Read as the reader may see the
	services.

	Home's services due (home.needs_you), not one of OneAI's tools: OneAI
	reads `upkeep_now(days=...)`."""
	from frappe.utils import add_days, getdate, today

	if not frappe.has_permission("Asset Maintenance Log", "read"):
		return {"error": "The reader may not see services."}
	day = getdate(today())
	out = []
	for one in frappe.get_list(
		"Asset Maintenance Log",
		filters=[["docstatus", "=", 0], ["maintenance_status", "in", ["Planned", "Overdue"]], ["due_date", "is", "set"], ["due_date", "<=", add_days(day, 30)]],
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


READS = (
	"item_facts",
	"stock_on_hand",
	"running_low",
	"receipt_facts",
	"still_to_arrive",
	"still_to_deliver",
	"lots_and_numbers",
	"quotes_now",
	"upkeep_now",
	"asset_facts",
)
"""The tools OneAI reads here (registry/hooks.py lists them in one_ai_reads)."""


SUGGESTS = (
	"plan_item_change",
	"plan_receipt",
	"plan_delivery",
	"plan_transfer",
	"plan_count",
	"plan_quote_request",
	"plan_handover",
)
"""The tools OneAI suggests, each as a card a person applies here (registry/hooks.py lists them in one_ai_suggests)."""
