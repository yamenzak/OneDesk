"""What an item's page says first: how many there are, how many are free to
sell, how many are on order, what they are worth, whether it is time to order
more, and what it last cost and from whom.
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
	reserved = sum(flt(row.get("reserved_qty")) for row in bins)
	return {
		"on_hand": on_hand,
		"free": on_hand - reserved,
		"held": sum(flt(row.get("reserved_stock")) for row in bins),
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
	"""The last receipt or order of the reader's company it was on: the rate,
	the rate of one stock unit, from whom, when, and whether it was received
	or only ordered."""
	from onedesk.one.company import reader_company

	for child, parent, date, kind in (
		("Purchase Receipt Item", "Purchase Receipt", "posting_date", "received"),
		("Purchase Order Item", "Purchase Order", "transaction_date", "ordered"),
	):
		if not frappe.has_permission(parent, "read"):
			continue
		found = frappe.db.sql(
			f"""select item.base_rate as rate, doc.supplier, doc.{date} as on_date,
				item.base_rate / coalesce(nullif(item.conversion_factor, 0), 1) as unit_rate
			from `tab{child}` item join `tab{parent}` doc on doc.name = item.parent
			where item.item_code = %s and doc.docstatus = 1 and doc.company = %s
			order by doc.{date} desc, doc.creation desc limit 1""",
			(item, reader_company()),
			as_dict=True,
		)
		if found:
			return frappe._dict(found[0], kind=kind)
	return None


def rates(item: str, count: int = 12) -> list[float]:
	"""What it cost the reader's company each of the last `count` times it was
	received, oldest first, or ordered when it has not been received yet."""
	from onedesk.one.company import reader_company

	for child, parent, date in (
		("Purchase Receipt Item", "Purchase Receipt", "posting_date"),
		("Purchase Order Item", "Purchase Order", "transaction_date"),
	):
		if not frappe.has_permission(parent, "read"):
			continue
		found = frappe.db.sql(
			f"""select item.base_rate from `tab{child}` item join `tab{parent}` doc on doc.name = item.parent
			where item.item_code = %s and doc.docstatus = 1 and doc.company = %s
			order by doc.{date} desc, doc.creation desc limit %s""",
			(item, reader_company(), count),
		)
		if found:
			return [flt(row[0]) for row in reversed(found)]
	return []


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
	from onedesk.one.company import reader_company

	bins = frappe.get_all(
		"Bin",
		filters={
			"item_code": item,
			"company": reader_company(),
		},
		fields=["warehouse", "actual_qty", "reserved_qty", "reserved_stock", "ordered_qty", "projected_qty", "stock_value"],
	)
	return {
		**summary(bins, [row.as_dict() for row in doc.get("reorder_levels")]),
		"uom": doc.stock_uom,
		"last": last_bought(item),
	}
