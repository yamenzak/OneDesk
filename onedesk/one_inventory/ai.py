"""What OneAI does in OneInventory: reads an item as its page shows it, says
what is running low, and suggests a change to an item as its page makes it,
as a card the reader approves.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import flt

#: An item's page (page/item_view), by its open view, from `?view=`.
PAGE = "item-view"

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

SUGGESTIONS = {
	f"page:{PAGE}": [_HOW, _ORDER, _CHANGE],
	f"page:{PAGE}/stock": [_HOW, _ORDER],
	f"page:{PAGE}/buying": [_ORDER, _HOW],
	"Item": [_LOW, _HOW],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on an item's page."""
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
