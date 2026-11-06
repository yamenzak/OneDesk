"""Stock on Hand (page/stock_on_hand, frontend/src/inventory/stock): what the company
holds now, item by item, in every warehouse or one, read as the reader may see
it. ERPNext's Stock Balance answers the same over a period and is a report
prepared in the background, so the rail's first look at the stores was an empty
page with a Generate button. This reads the Bins, which ERPNext keeps current
with every move."""

from typing import Annotated

import erpnext
import frappe
from frappe import _
from frappe.utils import flt

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
				"unit": item.get("unit") or item["stock_uom"],
				"image": item.get("image"),
				"on_hand": 0.0,
				"committed": 0.0,
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
		row["committed"] += flt(one.get("reserved_qty"))
		row["free"] += actual - flt(one.get("reserved_qty"))
		row["held"] += flt(one.get("reserved_stock"))
		row["on_order"] += flt(one.get("ordered_qty"))
		row["worth"] += flt(one.get("stock_value"))
		row["places"] += 1 if actual else 0
		reorder = level.get((one["item_code"], one["warehouse"]))
		if reorder and flt(one.get("projected_qty")) <= reorder:
			row["low_in"].append(one["warehouse"])
	for row in out.values():
		row["state"] = (
			"short" if row["free"] < 0 else "out" if row["on_hand"] <= 0 else "low" if row["low_in"] else "in"
		)
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
			fields=["name", "item_name", "item_group", "stock_uom", "image"],
			limit=0,
		)
	}
	symbols = dict(
		frappe.get_all(
			"UOM",
			filters={
				"name": ["in", list({one.stock_uom for one in named.values()}) or [""]],
				"symbol": ["is", "set"],
			},
			fields=["name", "symbol"],
			as_list=True,
		)
	)
	for one in named.values():
		one.unit = symbols.get(one.stock_uom)
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
		"out": sum(1 for one in listed if one["state"] == "out"),
		"can": {
			one: bool(frappe.has_permission(one, "create"))
			for one in ("Stock Entry", "Stock Reconciliation", "Warehouse")
		},
	}


@frappe.whitelist(methods=["POST"])
def transfer(
	source: Annotated[str, "The warehouse the stock leaves."],
	target: Annotated[str, "The warehouse it goes to."],
	lines: Annotated[list | str, "Each item and how many: [{item, qty}]."],
	project: Annotated[str, "The project the stock is moved for."] | None = None,
	remarks: Annotated[str, "A note kept on the movement."] | None = None,
) -> str:
	"""Stock moved from one warehouse to another, as Shopify's Transfer asks it:
	where from, where to, and which items and how many, with the project it is
	for and a note when there is one. ERPNext's own Material
	Transfer is made and submitted, as the reader, so its permissions, stock
	checks and books all hold; the name of the entry comes back."""
	return _moved("Material Transfer", source, target, lines, project, remarks)


@frappe.whitelist(methods=["POST"])
def issue(
	source: Annotated[str, "The warehouse the stock is taken from."],
	lines: Annotated[list | str, "Each item, how many, and in what unit when not its own: [{item, qty, uom}]."],
	project: Annotated[str, "The project it is used on."] | None = None,
	remarks: Annotated[str, "A note kept on the issue."] | None = None,
) -> str:
	"""Stock taken off the shelf and used, on a project when one is named, so
	its cost is the project's: ERPNext's own Material Issue, made and
	submitted as the reader, asked as a transfer is."""
	return _moved("Material Issue", source, None, lines, project, remarks)


def _moved(purpose: str, source: str, target: str | None, lines, project, remarks) -> str:
	lines = frappe.parse_json(lines) if isinstance(lines, str) else lines
	wanted = [one for one in lines or [] if one.get("item") and flt(one.get("qty")) > 0]
	if not wanted:
		frappe.throw(_("Add an item and how many to move."))
	entry = frappe.new_doc("Stock Entry")
	entry.purpose = purpose
	entry.company = frappe.db.get_value("Warehouse", source, "company")
	entry.from_warehouse, entry.to_warehouse = source, target
	entry.project, entry.remarks = project or None, remarks or None
	for one in wanted:
		row = {
			"item_code": one["item"],
			"qty": flt(one["qty"]),
			"s_warehouse": source,
			"t_warehouse": target,
			"project": project or None,
		}
		if one.get("uom"):
			from erpnext.stock.get_item_details import get_conversion_factor

			row["uom"] = one["uom"]
			row["conversion_factor"] = flt(get_conversion_factor(one["item"], one["uom"]).get("conversion_factor")) or 1
		entry.append("items", row)
	entry.set_stock_entry_type()
	entry.insert()
	entry.submit()
	return entry.name
