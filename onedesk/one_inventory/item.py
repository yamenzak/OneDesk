"""What an item's page says first: how many there are, how many are free to
sell, how many are on order, what they are worth, whether it is time to order
more, and what it last cost and from whom.

ERPNext has all of it, in four places: the Bins behind the Stock Levels
panel at the foot of the form, the reorder table on the Inventory tab, the
item's *Last Purchase Rate* (with no supplier or date beside it), and the
Stock Balance report. `said` reads them into one answer for the band
(public/js/item.js). An item marked Is Fixed Asset says how many assets it
has become instead.
"""

import frappe
from frappe.utils import flt


def summary(bins: list, levels: list) -> dict:
	"""Totals across warehouses, and the warehouses at or below their reorder
	level by projected quantity — what is there plus what is coming, less what
	is promised — which is what ERPNext's own reordering reads. Pure over rows
	of Bin and Item Reorder."""
	projected = {row.get("warehouse"): flt(row.get("projected_qty")) for row in bins}
	on_hand = sum(flt(row.get("actual_qty")) for row in bins)
	reserved = sum(flt(row.get("reserved_qty")) + flt(row.get("reserved_stock")) for row in bins)
	return {
		"on_hand": on_hand,
		"free": on_hand - reserved,
		"ordered": sum(flt(row.get("ordered_qty")) for row in bins),
		"value": sum(flt(row.get("stock_value")) for row in bins),
		"levels": len(levels),
		"below": [
			row.get("warehouse")
			for row in levels
			if flt(row.get("warehouse_reorder_level")) > 0
			and projected.get(row.get("warehouse"), 0) <= flt(row.get("warehouse_reorder_level"))
		],
	}


def last_bought(item: str) -> dict | None:
	"""The last receipt or order it was on: the rate, from whom, and when."""
	for child, parent, date in (
		("Purchase Receipt Item", "Purchase Receipt", "posting_date"),
		("Purchase Order Item", "Purchase Order", "transaction_date"),
	):
		found = frappe.db.sql(
			f"""select item.base_rate as rate, doc.supplier, doc.{date} as on_date
			from `tab{child}` item join `tab{parent}` doc on doc.name = item.parent
			where item.item_code = %s and doc.docstatus = 1
			order by doc.{date} desc, doc.creation desc limit 1""",
			item,
			as_dict=True,
		)
		if found:
			return found[0]
	return None


@frappe.whitelist()
@frappe.read_only()
def said(item: str) -> dict:
	frappe.has_permission("Item", "read", item, throw=True)
	doc = frappe.get_cached_doc("Item", item)
	if doc.is_fixed_asset:
		return {
			"assets": frappe.db.count("Asset", {"item_code": item, "docstatus": ["<", 2]}),
			"drafts": frappe.db.count("Asset", {"item_code": item, "docstatus": 0}),
		}
	if not doc.is_stock_item:
		return {"last": last_bought(item)}
	bins = frappe.get_all(
		"Bin",
		filters={"item_code": item},
		fields=["warehouse", "actual_qty", "reserved_qty", "reserved_stock", "ordered_qty", "projected_qty", "stock_value"],
	)
	return {
		**summary(bins, [row.as_dict() for row in doc.get("reorder_levels")]),
		"uom": doc.stock_uom,
		"last": last_bought(item),
	}
