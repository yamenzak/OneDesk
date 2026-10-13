"""Stock on Hand (page/stock_on_hand, frontend/src/stock): what the company
holds now, item by item, in every warehouse or one, read as the reader may see
it. ERPNext's Stock Balance answers the same over a period and is a report
prepared in the background, so the rail's first look at the stores was an empty
page with a Generate button. This reads the Bins, which ERPNext keeps current
with every move."""

from typing import Annotated

import erpnext
import frappe
from frappe.utils import flt

#: The most items the page lists at once; the rest are a search away.
MOST = 500


def rows(bins: list, levels: list, items: dict) -> list[dict]:
	"""Each item's stock across the warehouses given, with where it is low by
	ERPNext's own test, projected quantity at or below the warehouse's reorder
	level. Pure over rows of Bin, Item Reorder and Item."""
	level = {(one["parent"], one["warehouse"]): flt(one["warehouse_reorder_level"]) for one in levels}
	out = {}
	for one in bins:
		item = items.get(one["item_code"])
		if not item:
			continue
		row = out.setdefault(
			one["item_code"],
			{
				"item": one["item_code"],
				"item_name": item["item_name"],
				"group": item["item_group"],
				"uom": item["stock_uom"],
				"on_hand": 0.0,
				"free": 0.0,
				"on_order": 0.0,
				"held": 0.0,
				"worth": 0.0,
				"low_in": [],
				"places": 0,
			},
		)
		actual = flt(one.get("actual_qty"))
		row["on_hand"] += actual
		# Stock held for an order is part of what orders want already.
		row["free"] += actual - flt(one.get("reserved_qty"))
		row["held"] += flt(one.get("reserved_stock"))
		row["on_order"] += flt(one.get("ordered_qty"))
		row["worth"] += flt(one.get("stock_value"))
		row["places"] += 1 if actual else 0
		reorder = level.get((one["item_code"], one["warehouse"]))
		if reorder and flt(one.get("projected_qty")) <= reorder:
			row["low_in"].append(one["warehouse"])
	return sorted(
		(one for one in out.values() if one["on_hand"] or one["on_order"] or one["low_in"]),
		key=lambda one: (not one["low_in"], one["free"] >= 0, one["item_name"].lower()),
	)


@frappe.whitelist()
@frappe.read_only()
def on_hand(
	warehouse: Annotated[str, "Only this warehouse, or every one."] | None = None,
	search: Annotated[str, "Only items whose name or code has this in it."] | None = None,
) -> dict:
	"""What is on hand, item by item, with what each warehouse holds and is
	worth, as the reader may see it."""
	frappe.has_permission("Bin", "read", throw=True)
	# The reader's company's warehouses only, so the worth is one currency's.
	company = erpnext.get_default_company()
	currency = erpnext.get_company_currency(company) if company else None
	warehouses = frappe.get_list(
		"Warehouse",
		filters={"is_group": 0, "disabled": 0, **({"company": company} if company else {})},
		fields=["name", "warehouse_name", "warehouse_type", "parent_warehouse"],
		order_by="lft asc",
	)
	shown = [warehouse] if warehouse else [one.name for one in warehouses]
	bins = frappe.get_list(
		"Bin",
		filters={"warehouse": ["in", shown or [""]]},
		fields=[
			"item_code",
			"warehouse",
			"actual_qty",
			"reserved_qty",
			"reserved_stock",
			"ordered_qty",
			"projected_qty",
			"stock_value",
		],
		limit=0,
	)
	named = {
		one.name: one
		for one in frappe.get_list(
			"Item",
			filters={"name": ["in", list({one.item_code for one in bins}) or [""]]},
			fields=["name", "item_name", "item_group", "stock_uom"],
			limit=0,
		)
	}
	if search:
		said = search.strip().lower()
		named = {
			name: one
			for name, one in named.items()
			if said in name.lower() or said in (one.item_name or "").lower()
		}
	levels = frappe.get_all(
		"Item Reorder",
		filters={
			"parenttype": "Item",
			"parent": ["in", list(named) or [""]],
			"warehouse_reorder_level": [">", 0],
		},
		fields=["parent", "warehouse", "warehouse_reorder_level"],
	)
	listed = rows([dict(one) for one in bins], levels, {name: dict(one) for name, one in named.items()})
	held = {}
	for one in frappe.get_list(
		"Bin",
		filters={"warehouse": ["in", [w.name for w in warehouses] or [""]]},
		fields=["warehouse", "actual_qty", "stock_value"],
		limit=0,
	):
		place = held.setdefault(one.warehouse, {"worth": 0.0, "items": 0})
		place["worth"] += flt(one.stock_value)
		place["items"] += 1 if flt(one.actual_qty) > 0 else 0
	return {
		"currency": currency,
		"warehouse": warehouse,
		"warehouses": [
			{
				"name": one.name,
				"label": one.warehouse_name,
				"type": one.warehouse_type,
				**held.get(one.name, {"worth": 0.0, "items": 0}),
			}
			for one in warehouses
		],
		"items": listed[:MOST],
		"count": len(listed),
		"worth": sum(one["worth"] for one in listed),
		"low": sum(1 for one in listed if one["low_in"]),
		"short": sum(1 for one in listed if one["free"] < 0),
		"can": {
			one: bool(frappe.has_permission(one, "create"))
			for one in ("Stock Entry", "Stock Reconciliation", "Warehouse")
		},
	}
