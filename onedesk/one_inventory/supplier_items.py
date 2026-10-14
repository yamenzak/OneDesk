"""A supplier's Items tab (public/js/supplier_items.js, frontend/src/supplier):
what is bought from them, item by item, the way an item's Buying tab says who
it is bought from (view.py `_buying`), turned round. Each item with their own
code for it, whether they are its default supplier, the last price paid in
their money, how much was bought in a year, what is on order, what they agreed
on a blanket order and the item's lead time; then what they quoted for and
were never ordered from.
"""

import erpnext
import frappe
from frappe import _lt
from frappe.utils import add_days, flt, nowdate

TABS = [{"name": "items", "label": _lt("Items"), "order": 20, "doctypes": ("Supplier",)}]

#: How many items the tab lists.
MOST = 100
#: Statuses of an order with goods still to come.
COMING = ("To Receive and Bill", "To Receive")


def _readable(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


@frappe.whitelist()
@frappe.read_only()
def read(supplier: str) -> dict:
	"""What is bought from `supplier`, item by item, in the reader's company."""
	frappe.has_permission("Supplier", "read", doc=supplier, throw=True)
	company = erpnext.get_default_company()
	items: dict = {}

	def one(code: str) -> dict:
		return items.setdefault(
			code,
			{
				"item": code,
				"part_no": None,
				"default": False,
				"last": None,
				"before": None,
				"bought": 0.0,
				"orders": 0,
				"on_order": 0.0,
				"agreed": None,
				"quoted": None,
			},
		)

	if _readable("Purchase Order"):
		year_ago = add_days(nowdate(), -365)
		for row in frappe.get_list(
			"Purchase Order",
			filters=[["supplier", "=", supplier], ["company", "=", company], ["docstatus", "=", 1]],
			fields=[
				"name",
				"status",
				"currency",
				"transaction_date",
				"`tabPurchase Order Item`.item_code as item_code",
				"`tabPurchase Order Item`.rate as rate",
				"`tabPurchase Order Item`.uom as uom",
				"`tabPurchase Order Item`.stock_qty as stock_qty",
				"`tabPurchase Order Item`.received_qty as received_qty",
				"`tabPurchase Order Item`.conversion_factor as conversion_factor",
			],
			order_by="transaction_date desc, creation desc",
			limit=1000,
		):
			if not row.item_code:
				continue
			line = one(row.item_code)
			if line["last"] is None:
				line["last"] = {
					"rate": flt(row.rate),
					"currency": row.currency,
					"uom": row.uom,
					"on": str(row.transaction_date),
				}
			elif (
				line["before"] is None
				and flt(row.rate) != line["last"]["rate"]
				and row.uom == line["last"]["uom"]
			):
				line["before"] = flt(row.rate)
			line["orders"] += 1
			if str(row.transaction_date) >= str(year_ago):
				line["bought"] += flt(row.stock_qty)
			if row.status in COMING:
				line["on_order"] += max(
					flt(row.stock_qty) - flt(row.received_qty) * flt(row.conversion_factor or 1), 0
				)

	# Their own code for an item, and the items they are the default supplier of.
	for row in frappe.get_all(
		"Item Supplier",
		filters={"supplier": supplier, "parenttype": "Item"},
		fields=["parent", "supplier_part_no"],
	):
		one(row.parent)["part_no"] = row.supplier_part_no
	for code in frappe.get_all(
		"Item Default",
		filters={"default_supplier": supplier, "company": company, "parenttype": "Item"},
		pluck="parent",
	):
		one(code)["default"] = True

	if _readable("Blanket Order"):
		for row in frappe.get_list(
			"Blanket Order",
			filters=[
				["supplier", "=", supplier],
				["company", "=", company],
				["docstatus", "=", 1],
				["blanket_order_type", "=", "Purchasing"],
				["to_date", ">=", nowdate()],
			],
			fields=[
				"to_date",
				"`tabBlanket Order Item`.item_code as item_code",
				"`tabBlanket Order Item`.rate as rate",
				"`tabBlanket Order Item`.qty as qty",
				"`tabBlanket Order Item`.ordered_qty as ordered",
			],
			order_by="to_date asc",
		):
			line = one(row.item_code)
			line["agreed"] = line["agreed"] or {
				"rate": flt(row.rate),
				"left": max(flt(row.qty) - flt(row.ordered), 0),
				"until": str(row.to_date),
			}

	# What they quoted for, newest first, kept for items never ordered from them.
	if _readable("Supplier Quotation"):
		for row in frappe.get_list(
			"Supplier Quotation",
			filters=[["supplier", "=", supplier], ["company", "=", company], ["docstatus", "=", 1]],
			fields=[
				"name",
				"currency",
				"transaction_date",
				"valid_till",
				"status",
				"`tabSupplier Quotation Item`.item_code as item_code",
				"`tabSupplier Quotation Item`.rate as rate",
				"`tabSupplier Quotation Item`.uom as uom",
			],
			order_by="transaction_date desc, creation desc",
			limit=500,
		):
			if not row.item_code or (row.item_code in items and items[row.item_code]["orders"]):
				continue
			line = one(row.item_code)
			line["quoted"] = line["quoted"] or {
				"quote": row.name,
				"rate": flt(row.rate),
				"currency": row.currency,
				"uom": row.uom,
				"on": str(row.transaction_date),
				"until": str(row.valid_till) if row.valid_till else None,
				"expired": row.status == "Expired",
			}

	known = {
		row.name: row
		for row in frappe.get_all(
			"Item",
			filters={"name": ["in", list(items) or [""]]},
			fields=["name", "item_name", "image", "stock_uom", "lead_time_days", "disabled"],
		)
	}
	symbols = dict(
		frappe.get_all(
			"UOM",
			filters={
				"name": ["in", list({row.stock_uom for row in known.values()}) or [""]],
				"symbol": ["is", "set"],
			},
			fields=["name", "symbol"],
			as_list=True,
		)
	)
	listed = []
	for code, line in items.items():
		item = known.get(code)
		if not item:
			continue
		line.update(
			item_name=item.item_name or code,
			image=item.image,
			unit=symbols.get(item.stock_uom) or item.stock_uom,
			lead_days=int(item.lead_time_days or 0) or None,
			disabled=bool(item.disabled),
		)
		listed.append(line)
	# The default supplier's items first, then the latest bought, then quoted.
	listed.sort(key=lambda line: (line["last"] or line["quoted"] or {}).get("on") or "", reverse=True)
	listed.sort(key=lambda line: (not line["default"], not line["orders"]))
	return {
		"supplier": supplier,
		"items": listed[:MOST],
		"count": len(listed),
		"on_order": sum(1 for line in listed if line["on_order"]),
		"currency": erpnext.get_company_currency(company) if company else None,
		"can": {"order": bool(frappe.has_permission("Purchase Order", "create"))},
	}
