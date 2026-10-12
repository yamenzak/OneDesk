"""An item's page (page/item_view, frontend/src/item): the item as its reader
may see it, where it is kept, who it is bought from and sold to, what it is
made from and what it goes into. The page only reads here; it changes the item
as desk does (set_value, frappe.client.save) and starts documents from it in
desk's own forms."""

from datetime import date
from typing import Annotated

import erpnext
import frappe
from frappe.utils import flt, getdate, nowdate

from onedesk.one_inventory import heads
from onedesk.one_inventory import item as stock

#: What the page reads of the item itself.
FIELDS = (
	"name",
	"item_code",
	"item_name",
	"item_group",
	"brand",
	"stock_uom",
	"description",
	"image",
	"disabled",
	"is_stock_item",
	"is_fixed_asset",
	"is_purchase_item",
	"is_sales_item",
	"is_sub_contracted_item",
	"has_variants",
	"variant_of",
	"has_batch_no",
	"has_serial_no",
	"end_of_life",
	"valuation_method",
	"lead_time_days",
	"safety_stock",
	"min_order_qty",
	"asset_category",
	"modified",
)

#: The most rows a list on the page shows; the rest open in its own list.
MOST = 20

#: A purchase or sales order still to be received or delivered.
OPEN_ORDER = ("not in", ("Completed", "Closed", "Cancelled", "On Hold", "To Bill"))


def headline(doc: dict, said: dict, today: date) -> dict | None:
	"""The one thing worth saying above the item, if anything: it can't be
	used, more is promised than there is, or it has run low. Pure over the
	item and its summary."""
	if doc.get("disabled"):
		return {"key": "disabled", "tone": "gray"}
	if doc.get("end_of_life") and getdate(doc["end_of_life"]) <= today:
		return {"key": "ended", "date": str(doc["end_of_life"]), "tone": "orange"}
	if said.get("free") is not None and flt(said["free"]) < 0:
		return {"key": "short", "qty": -flt(said["free"]), "tone": "red"}
	if said.get("below"):
		return {"key": "low", "names": said["below"], "tone": "orange"}
	return None


def kind(doc: dict) -> str:
	"""What sort of thing it is, in the words the page shows. Pure."""
	if doc.get("is_fixed_asset"):
		return "Fixed Asset"
	if doc.get("has_variants"):
		return "Template"
	return "Stock" if doc.get("is_stock_item") else "Service"


@frappe.whitelist()
@frappe.read_only()
def read(item: Annotated[str, "The item code."]) -> dict:
	"""The item as its page shows it, read as the reader."""
	frappe.has_permission("Item", "read", doc=item, throw=True)
	doc = frappe.get_doc("Item", item)
	said = {field: doc.get(field) for field in FIELDS}
	currency = (
		erpnext.get_company_currency(erpnext.get_default_company()) if erpnext.get_default_company() else None
	)
	summary = stock.said(item) if doc.is_stock_item and not doc.is_fixed_asset else {}
	said.update(
		{
			"kind": kind(said),
			"currency": currency,
			"valuation": doc.valuation_method
			or frappe.db.get_single_value("Stock Settings", "valuation_method"),
			"group_title": doc.item_group,
			"summary": summary,
			"headline": headline(said, summary, getdate(nowdate())),
			"variant_of_title": frappe.db.get_value("Item", doc.variant_of, "item_name")
			if doc.variant_of
			else None,
			"attributes": [
				{"attribute": row.attribute, "value": row.attribute_value}
				for row in doc.get("attributes") or []
				if row.attribute_value
			],
			"variants": _variants(item) if doc.has_variants else [],
			"made": _made(item),
			"last_made": last_made(item) if doc.is_stock_item else None,
			"last_bought": stock.last_bought(item) if not doc.is_fixed_asset else None,
			"moved": heads.moved(doc),
			"stock": _stock(doc) if doc.is_stock_item and not doc.is_fixed_asset else None,
			"buying": _buying(doc),
			"selling": _selling(doc),
			"making": _making(doc),
			"assets": _assets(item) if doc.is_fixed_asset else None,
			"files": files(item),
			"can_write": bool(frappe.has_permission("Item", "write", doc=doc)),
			"can": {
				one: bool(frappe.has_permission(one, "create"))
				for one in (
					"Purchase Order",
					"Material Request",
					"Stock Entry",
					"Stock Reconciliation",
					"Sales Order",
					"BOM",
					"Work Order",
					"Item Price",
					"Item",
				)
			},
		}
	)
	return said


@frappe.whitelist()
@frappe.read_only()
def files(item: Annotated[str, "The item code."]) -> int:
	"""How many files are attached to the item, as the reader may see them."""
	frappe.has_permission("Item", "read", doc=item, throw=True)
	return len(
		frappe.get_list(
			"File",
			filters={"attached_to_doctype": "Item", "attached_to_name": item, "is_folder": 0},
			pluck="name",
		)
	)


def _readable(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def _variants(item: str) -> list:
	return frappe.get_list(
		"Item",
		filters={"variant_of": item},
		fields=["name", "item_name", "disabled"],
		order_by="item_name asc",
		limit=MOST,
	)


def _made(item: str) -> dict | None:
	"""Its default bill of materials, when it is made here."""
	if not _readable("BOM"):
		return None
	bom = frappe.get_list(
		"BOM",
		filters={"item": item, "is_default": 1, "is_active": 1, "docstatus": 1},
		fields=["name", "quantity", "total_cost"],
		limit=1,
	)
	return bom[0] if bom else None


def _stock(doc) -> dict:
	"""Where it is kept, how much each place holds and needs, its batches and
	the last moves in and out of it."""
	levels = {row.warehouse: row for row in doc.get("reorder_levels") or []}
	bins = frappe.get_list(
		"Bin",
		filters={"item_code": doc.name},
		fields=[
			"warehouse",
			"actual_qty",
			"reserved_qty",
			"reserved_stock",
			"ordered_qty",
			"projected_qty",
			"stock_value",
		],
		order_by="actual_qty desc",
	)
	places = []
	for row in bins:
		level = levels.pop(row.warehouse, None)
		places.append(_place(row, level))
	places += [_place(frappe._dict(warehouse=warehouse), level) for warehouse, level in levels.items()]
	return {
		"places": [
			one for one in places if one["on_hand"] or one["ordered"] or one["reserved"] or one["level"]
		],
		"batches": _batches(doc.name) if doc.has_batch_no else [],
		"serials": frappe.db.count("Serial No", {"item_code": doc.name, "status": "Active"})
		if doc.has_serial_no and _readable("Serial No")
		else None,
		"moves": _moves(doc.name),
	}


def _place(row, level) -> dict:
	reorder = flt(level.warehouse_reorder_level) if level else 0
	return {
		"warehouse": row.warehouse,
		"on_hand": flt(row.get("actual_qty")),
		"reserved": flt(row.get("reserved_qty")),
		"held": flt(row.get("reserved_stock")),
		"ordered": flt(row.get("ordered_qty")),
		"projected": flt(row.get("projected_qty")),
		"value": flt(row.get("stock_value")),
		"level": reorder,
		"order_qty": flt(level.warehouse_reorder_qty) if level else 0,
		"low": bool(reorder and flt(row.get("projected_qty")) <= reorder),
	}


def _batches(item: str) -> list:
	if not _readable("Batch"):
		return []
	return frappe.get_list(
		"Batch",
		filters={"item": item, "disabled": 0, "batch_qty": [">", 0]},
		fields=["name", "batch_qty", "expiry_date", "manufacturing_date"],
		order_by="expiry_date asc",
		limit=MOST,
	)


def _moves(item: str) -> list:
	"""The last moves of it, newest first, as the reader's stock ledger lists them."""
	if not _readable("Stock Ledger Entry"):
		return []
	moves = frappe.get_list(
		"Stock Ledger Entry",
		filters={"item_code": item, "is_cancelled": 0},
		fields=[
			"posting_date",
			"voucher_type",
			"voucher_no",
			"warehouse",
			"actual_qty",
			"qty_after_transaction",
			"stock_value_difference",
			"project",
		],
		order_by="posting_datetime desc, creation desc",
		limit=MOST,
	)
	# A stock entry says what kind of move it was: issued, moved, made.
	entries = {one.voucher_no for one in moves if one.voucher_type == "Stock Entry"}
	kinds = (
		dict(
			frappe.get_all(
				"Stock Entry",
				filters={"name": ["in", list(entries)]},
				fields=["name", "stock_entry_type"],
				as_list=True,
			)
		)
		if entries
		else {}
	)
	for one in moves:
		one["kind"] = kinds.get(one.voucher_no) or one.voucher_type
	return moves


def _buying(doc) -> dict | None:
	"""Who it is bought from and at what, what is on order and what has been asked for."""
	if not (doc.is_purchase_item or doc.is_fixed_asset):
		return None
	suppliers = {}
	if _readable("Purchase Order"):
		for row in frappe.get_list(
			"Purchase Order",
			filters=[["Purchase Order Item", "item_code", "=", doc.name], ["docstatus", "=", 1]],
			fields=[
				"supplier",
				"transaction_date",
				"`tabPurchase Order Item`.base_rate as rate",
				"`tabPurchase Order Item`.qty as qty",
			],
			order_by="transaction_date desc",
			limit=200,
		):
			one = suppliers.setdefault(
				row.supplier,
				{
					"supplier": row.supplier,
					"rate": row.rate,
					"last": row.transaction_date,
					"qty": 0,
					"orders": 0,
				},
			)
			one["qty"] += flt(row.qty)
			one["orders"] += 1
	for row in doc.get("supplier_items") or []:
		suppliers.setdefault(
			row.supplier, {"supplier": row.supplier, "rate": None, "last": None, "qty": 0, "orders": 0}
		)["part_no"] = row.supplier_part_no
	default = next(
		(row.default_supplier for row in doc.get("item_defaults") or [] if row.default_supplier), None
	)
	for one in suppliers.values():
		one["default"] = one["supplier"] == default
	return {
		"suppliers": sorted(suppliers.values(), key=lambda one: (not one["default"], -one["orders"]))[:MOST],
		"orders": _open(
			"Purchase Order",
			"Purchase Order Item",
			[
				"supplier as party",
				"schedule_date as due",
				"status",
				"`tabPurchase Order Item`.qty as qty",
				"`tabPurchase Order Item`.received_qty as done",
			],
			doc.name,
		),
		"requests": _open(
			"Material Request",
			"Material Request Item",
			[
				"material_request_type as kind",
				"schedule_date as due",
				"status",
				"`tabMaterial Request Item`.qty as qty",
				"`tabMaterial Request Item`.ordered_qty as done",
			],
			doc.name,
			status=(
				"not in",
				("Ordered", "Transferred", "Issued", "Received", "Stopped", "Cancelled", "Manufactured"),
			),
		),
		"prices": _prices(doc.name, "buying"),
	}


def _selling(doc) -> dict | None:
	"""What it sells for, what customers have ordered and not yet had, and who buys it."""
	if not doc.is_sales_item:
		return None
	customers = {}
	if _readable("Sales Invoice"):
		start = frappe.utils.add_months(nowdate(), -12)
		for row in frappe.get_list(
			"Sales Invoice",
			filters=[
				["Sales Invoice Item", "item_code", "=", doc.name],
				["docstatus", "=", 1],
				["posting_date", ">=", start],
				["is_return", "=", 0],
			],
			fields=[
				"customer",
				"`tabSales Invoice Item`.stock_qty as qty",
				"`tabSales Invoice Item`.base_net_amount as amount",
			],
			limit=0,
		):
			one = customers.setdefault(row.customer, {"customer": row.customer, "qty": 0, "amount": 0})
			one["qty"] += flt(row.qty)
			one["amount"] += flt(row.amount)
	return {
		"orders": _open(
			"Sales Order",
			"Sales Order Item",
			[
				"customer as party",
				"delivery_date as due",
				"status",
				"project",
				"`tabSales Order Item`.qty as qty",
				"`tabSales Order Item`.delivered_qty as done",
			],
			doc.name,
		),
		"customers": sorted(customers.values(), key=lambda one: -one["amount"])[:MOST],
		"prices": _prices(doc.name, "selling"),
	}


def _open(doctype: str, child: str, fields: list, item: str, status=OPEN_ORDER) -> list:
	"""Its lines on submitted documents still to be done, soonest first."""
	if not _readable(doctype):
		return []
	rows = frappe.get_list(
		doctype,
		filters=[[child, "item_code", "=", item], ["docstatus", "=", 1], ["status", *status]],
		fields=["name", *fields],
		order_by=f"`tab{doctype}`.{'delivery_date' if doctype == 'Sales Order' else 'schedule_date'} asc",
		limit=MOST,
	)
	today = getdate(nowdate())
	for row in rows:
		row["left"] = max(flt(row.qty) - flt(row.done), 0)
		row["late"] = bool(row.get("due") and getdate(row.due) < today and row["left"])
	return [row for row in rows if row["left"]]


def _prices(item: str, side: str) -> list:
	if not _readable("Item Price"):
		return []
	return frappe.get_list(
		"Item Price",
		filters={"item_code": item, side: 1},
		fields=[
			"name",
			"price_list",
			"price_list_rate",
			"currency",
			"uom",
			"supplier",
			"customer",
			"valid_from",
			"valid_upto",
		],
		order_by="price_list asc",
		limit=MOST,
	)


def _making(doc) -> dict | None:
	"""What it is made from, what it goes into, and the work orders making it."""
	if not _readable("BOM"):
		return None
	boms = frappe.get_list(
		"BOM",
		filters={"item": doc.name, "docstatus": ["<", 2]},
		fields=[
			"name",
			"is_active",
			"is_default",
			"docstatus",
			"quantity",
			"total_cost",
			"currency",
			"project",
		],
		order_by="is_default desc, modified desc",
		limit=MOST,
	)
	materials = []
	default = next((one for one in boms if one.is_default and one.is_active), None)
	if default:
		materials = frappe.get_all(
			"BOM Item",
			filters={"parent": default.name, "parenttype": "BOM"},
			fields=["item_code", "item_name", "qty", "uom", "amount"],
			order_by="idx asc",
		)
	used_in = frappe.get_list(
		"BOM",
		filters=[["BOM Item", "item_code", "=", doc.name], ["is_active", "=", 1], ["docstatus", "=", 1]],
		fields=["name", "item", "item_name", "is_default", "`tabBOM Item`.qty as qty"],
		limit=MOST,
	)
	orders = []
	if _readable("Work Order"):
		orders = frappe.get_list(
			"Work Order",
			filters={
				"production_item": doc.name,
				"docstatus": 1,
				"status": ["not in", ("Completed", "Closed", "Cancelled", "Stopped")],
			},
			fields=[
				"name",
				"qty",
				"produced_qty",
				"status",
				"project",
				"planned_start_date",
				"expected_delivery_date",
			],
			order_by="planned_start_date asc",
			limit=MOST,
		)
	# Something made here has its Making tab before its first bill of materials.
	made_here = doc.default_material_request_type == "Manufacture" and not doc.is_fixed_asset
	if not (boms or used_in or orders or made_here):
		return None
	return {"boms": boms, "materials": materials, "used_in": used_in, "orders": orders}


def _assets(item: str) -> list:
	if not _readable("Asset"):
		return []
	assets = frappe.get_list(
		"Asset",
		filters={"item_code": item, "docstatus": ["<", 2]},
		fields=["name", "asset_name", "status", "location", "custodian", "docstatus", "purchase_date"],
		order_by="purchase_date desc",
		limit=MOST,
	)
	held = {one.custodian for one in assets if one.custodian}
	names = (
		dict(
			frappe.get_all(
				"Employee",
				filters={"name": ["in", list(held)]},
				fields=["name", "employee_name"],
				as_list=True,
			)
		)
		if held
		else {}
	)
	for one in assets:
		one["custodian_name"] = names.get(one.custodian) or one.custodian
	return assets


def last_made(item: str) -> dict | None:
	"""The last time some of it was made here: how many, and when."""
	if not _readable("Stock Entry"):
		return None
	rows = frappe.get_list(
		"Stock Entry",
		filters=[
			["purpose", "=", "Manufacture"],
			["docstatus", "=", 1],
			["Stock Entry Detail", "item_code", "=", item],
			["Stock Entry Detail", "is_finished_item", "=", 1],
		],
		fields=["posting_date", "`tabStock Entry Detail`.qty as qty"],
		order_by="posting_date desc",
		limit=1,
	)
	return rows[0] if rows else None
