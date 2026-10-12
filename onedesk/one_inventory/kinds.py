"""New Item, by kind: what a person picks first, and the ERPNext fields each
kind sets so nobody has to know them (public/js/item_new.js)."""

import re

import frappe
from frappe.utils import flt

from onedesk.one_inventory.measure import BASE

#: Each kind and the Item fields it sets. A product in sizes or colours is a
#: template its versions are made from, kept in stock one version at a time.
KINDS = {
	"Stock": {"is_stock_item": 1, "is_fixed_asset": 0, "has_variants": 0},
	"Service": {"is_stock_item": 0, "is_fixed_asset": 0, "has_variants": 0, "include_item_in_manufacturing": 0},
	"Equipment": {
		"is_stock_item": 0,
		"is_fixed_asset": 1,
		"has_variants": 0,
		"auto_create_assets": 1,
		"is_sales_item": 0,
		"include_item_in_manufacturing": 0,
	},
	"Versions": {"is_stock_item": 1, "is_fixed_asset": 0, "has_variants": 1, "variant_based_on": "Item Attribute"},
}

#: The group a kind starts in, when the workspace has it.
GROUPS = {"Stock": "Products", "Service": "Services", "Equipment": "Fixed Assets", "Versions": "Products"}


def code_from(name: str) -> str:
	"""An item code from its name: capitals, words joined by a dash, at most
	three words. Pure."""
	words = re.findall(r"[A-Za-z0-9]+", name or "")
	return "-".join(word.upper() for word in words[:3])


@frappe.whitelist()
def defaults() -> dict:
	"""What the New Item steps start from: how items are named, the stores
	warehouse, and which of the kinds' groups the workspace has."""
	stores = frappe.get_all(
		"Warehouse",
		filters={"is_group": 0, "disabled": 0, "warehouse_name": ["like", "%Stores%"]},
		pluck="name",
		limit=1,
	)
	return {
		"by_code": frappe.db.get_single_value("Stock Settings", "item_naming_by") == "Item Code",
		"unit": frappe.db.get_single_value("Stock Settings", "stock_uom") or "Nos",
		"warehouse": stores[0] if stores else None,
		"groups": {kind: group for kind, group in GROUPS.items() if frappe.db.exists("Item Group", group)},
		"currency": frappe.defaults.get_global_default("currency"),
		# What a product in sizes or colours can come in, by attribute.
		"attributes": {
			attribute: frappe.get_all(
				"Item Attribute Value", filters={"parent": attribute}, pluck="attribute_value", order_by="idx asc"
			)
			for attribute in frappe.get_all("Item Attribute", filters={"numeric_values": 0}, pluck="name")
		},
	}


@frappe.whitelist(methods=["POST"])
def make(values: dict | str) -> str:
	"""The item, as ERPNext's form would save it, from the steps' answers.
	Its prices go on the workspace's buying and selling price lists, and its
	opening stock in by ERPNext's own count."""
	values = frappe._dict(frappe.parse_json(values))
	kind = values.kind if values.kind in KINDS else "Stock"
	company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")
	item = frappe.new_doc("Item")
	item.update(KINDS[kind])
	item.update(
		{
			"item_code": values.code or code_from(values.title),
			"item_name": values.title,
			"item_group": values.group,
			"stock_uom": values.unit,
			"description": values.description or values.title,
			"image": values.image,
			"is_sales_item": int(bool(values.sold)) if kind != "Equipment" else 0,
			"is_purchase_item": int(bool(values.bought)),
			# ERPNext prices a product in sizes or colours on each version, not on the product.
			"standard_rate": flt(values.selling_price) if values.sold and kind != "Versions" else 0,
			"asset_category": values.asset_category if kind == "Equipment" else None,
		}
	)
	# Sold by size (one_inventory/measure.py). A sheet kept by the piece says
	# how many square metres it is, as one of ERPNext's own unit conversions.
	if kind != "Equipment" and values.measured_by in BASE:
		item.one_measured_by = values.measured_by
		per_unit = flt(values.per_unit if values.measured_by == "Length" else values.per_unit_area)
		if values.unit != BASE[values.measured_by] and per_unit:
			item.append("uoms", {"uom": BASE[values.measured_by], "conversion_factor": 1 / per_unit})
	# Made here is ERPNext's own: what more of it is asked for by default, which
	# production planning reads too.
	made_here = kind in ("Stock", "Versions") and bool(values.made_here)
	if made_here:
		item.default_material_request_type = "Manufacture"
	if values.warehouse or values.supplier:
		item.append(
			"item_defaults",
			{"company": company, "default_warehouse": values.warehouse, "default_supplier": values.supplier},
		)
	if kind == "Stock" and values.reorder and values.warehouse and flt(values.reorder_level):
		item.append(
			"reorder_levels",
			{
				"warehouse": values.warehouse,
				"warehouse_reorder_level": flt(values.reorder_level),
				"warehouse_reorder_qty": flt(values.reorder_qty) or flt(values.reorder_level),
				"material_request_type": "Manufacture" if made_here else "Purchase",
			},
		)
	if kind == "Stock" and flt(values.opening_stock) and values.warehouse:
		# ERPNext counts it in after the item is saved (Item.after_insert).
		item.opening_stock = flt(values.opening_stock)
		item.valuation_rate = flt(values.buying_price) or flt(values.selling_price)
	if kind == "Versions":
		for attribute in [one for one, chosen in (values.versions or {}).items() if chosen]:
			item.append("attributes", {"attribute": attribute})
	# What goes into one of it, its first bill of materials (`_recipe`).
	materials = [
		one
		for one in (values.materials or [] if made_here else [])
		if isinstance(one, dict) and one.get("item_code") and flt(one.get("qty")) > 0
	]
	if materials:
		frappe.has_permission("BOM", "create", throw=True)
	item.insert()
	if materials:
		_recipe(item, company, materials)
	if kind == "Versions" and values.versions:
		# Every combination of the values picked, as ERPNext's Make Variants
		# makes them: at once for a few, in the background for more.
		from erpnext.controllers.item_variant import enqueue_multiple_variant_creation

		picked = {attribute: chosen for attribute, chosen in values.versions.items() if chosen}
		if picked:
			enqueue_multiple_variant_creation(item.name, picked)
		if values.sold and flt(values.selling_price):
			for version in frappe.get_all("Item", filters={"variant_of": item.name}, pluck="name"):
				_price(frappe.get_doc("Item", version), "Selling Settings", "selling_price_list", flt(values.selling_price))
	if values.bought and flt(values.buying_price) and kind != "Versions":
		_price(item, "Buying Settings", "buying_price_list", flt(values.buying_price), values.supplier)
	return item.name


def _recipe(item, company: str, materials: list[dict]) -> str:
	"""The item's first bill of materials, for one of it, submitted so a work
	order can be started from it when the person may submit one."""
	bom = frappe.get_doc(
		{
			"doctype": "BOM",
			"item": item.name,
			"company": company,
			"quantity": 1,
			"items": [{"item_code": one["item_code"], "qty": flt(one["qty"])} for one in materials],
		}
	).insert()
	if frappe.has_permission("BOM", "submit"):
		bom.submit()
	return bom.name


def _price(item, settings: str, field: str, rate: float, supplier: str | None = None) -> None:
	price_list = frappe.db.get_single_value(settings, field)
	if not price_list:
		return
	frappe.get_doc(
		{
			"doctype": "Item Price",
			"item_code": item.name,
			"price_list": price_list,
			"price_list_rate": rate,
			"uom": item.stock_uom,
			"supplier": supplier,
		}
	).insert()


#: The Items list's tabs and the filters each one is.
TABS = {
	"Stock": [["is_stock_item", "=", 1], ["has_variants", "=", 0]],
	"Made Here": [["default_bom", "is", "set"]],
	"Services": [["is_stock_item", "=", 0], ["is_fixed_asset", "=", 0]],
	"Equipment": [["is_fixed_asset", "=", 1]],
	"Sizes or Colours": [["has_variants", "=", 1]],
}


@frappe.whitelist()
def stocked(items: list | str) -> dict:
	"""For the Items list: each stock item's quantity on hand and whether it is
	low in a warehouse it is reordered in, summed as its page sums them
	(one_inventory/item.py `summary`)."""
	from onedesk.one_inventory.item import summary

	items = [one for one in frappe.parse_json(items) or [] if isinstance(one, str)][:500]
	if not items or not frappe.has_permission("Bin", "read"):
		return {}
	bins, levels = {}, {}
	for row in frappe.get_list(
		"Bin",
		filters={"item_code": ["in", items]},
		fields=["item_code", "warehouse", "actual_qty", "projected_qty", "reserved_qty", "reserved_stock", "ordered_qty", "stock_value"],
		limit_page_length=0,
	):
		bins.setdefault(row.item_code, []).append(row)
	for row in frappe.get_all(
		"Item Reorder",
		filters={"parent": ["in", items], "parenttype": "Item"},
		fields=["parent", "warehouse", "warehouse_reorder_level"],
	):
		levels.setdefault(row.parent, []).append(row)
	said = {item: summary(bins.get(item, []), levels.get(item, [])) for item in set(bins) | set(levels)}
	return {item: {"on_hand": one["on_hand"], "low": bool(one["below"])} for item, one in said.items()}
