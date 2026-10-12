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

from onedesk.one import figures
from onedesk.one_inventory import barcodes, batches, heads
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
	"one_measured_by",
	"shelf_life_in_days",
	"weight_per_unit",
	"weight_uom",
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
			"trends": _trends(doc),
			"buying": _buying(doc),
			"selling": _selling(doc),
			"making": _making(doc),
			"assets": _assets(item) if doc.is_fixed_asset else None,
			"files": files(item),
			"barcodes": barcodes.listed(doc),
			"brand_logo": frappe.db.get_value("Brand", doc.brand, "image") if doc.brand else None,
			# Batches and serial numbers are fixed once it has moved, as its form has them.
			"stock_exists": bool(doc.is_stock_item and doc.stock_ledger_created()),
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


def _trends(doc) -> dict:
	"""What the head's cards draw under their numbers: how much was on hand and
	what it was worth at the end of each of the last twelve months, how much
	was ordered each month, and what it cost the last times it was bought.
	Read as the reader's own lists would give them."""
	said = {"prices": stock.rates(doc.name) if not doc.is_fixed_asset else []}
	if not doc.is_stock_item or doc.is_fixed_asset:
		return said
	day = getdate(nowdate())
	starts = figures.months(day)
	if frappe.has_permission("Stock Ledger Entry", "read"):
		# Each warehouse's balance after its last move of the month, as the
		# ledger keeps it: a stock count sets a balance without moving any.
		moves = frappe.get_list(
			"Stock Ledger Entry",
			filters={"item_code": doc.name, "is_cancelled": 0, "posting_date": ["<=", day]},
			fields=["warehouse", "posting_date", "qty_after_transaction", "stock_value"],
			order_by="posting_datetime asc, creation asc",
			limit_page_length=0,
		)
		said["held"], said["worth"] = _month_ends(moves, starts)
	if frappe.has_permission("Purchase Order", "read"):
		rows = frappe.get_list(
			"Purchase Order",
			filters=[
				["Purchase Order Item", "item_code", "=", doc.name],
				["docstatus", "=", 1],
				["transaction_date", ">=", starts[0]],
			],
			fields=["transaction_date", "items.item_code", "items.stock_qty as qty"],
			limit_page_length=0,
		)
		said["ordered"] = figures.by_month(
			((getdate(row.transaction_date), row.qty) for row in rows if row.item_code == doc.name), day
		)
	return said


def _month_ends(moves, starts) -> tuple[list[float], list[float]]:
	"""How much was held, and its worth, at the end of each month from
	`starts`, from ledger rows in the order they were posted."""
	balance, held, worth = {}, [], []
	moves = iter(moves)
	row = next(moves, None)
	for end in [*starts[1:], None]:
		while row and (end is None or getdate(row.posting_date) < end):
			balance[row.warehouse] = (flt(row.qty_after_transaction), flt(row.stock_value))
			row = next(moves, None)
		held.append(sum(qty for qty, _ in balance.values()))
		worth.append(sum(value for _, value in balance.values()))
	return held, worth


def _called(warehouse: str | None) -> str | None:
	"""A warehouse by its own name, without the company's letters."""
	if not warehouse:
		return None
	return frappe.get_cached_value("Warehouse", warehouse, "warehouse_name") or warehouse


def _place(row, level) -> dict:
	reorder = flt(level.warehouse_reorder_level) if level else 0
	return {
		"warehouse": row.warehouse,
		"called": _called(row.warehouse),
		# The item's own reorder row for it, which the page changes in place.
		"row": level.name if level else None,
		"free": flt(row.get("actual_qty")) - flt(row.get("reserved_qty")),
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
	found = frappe.get_list(
		"Batch",
		filters={"item": item, "disabled": 0, "batch_qty": [">", 0]},
		fields=["name", "batch_id", "batch_qty", "expiry_date", "manufacturing_date"],
		order_by="expiry_date asc",
		limit=MOST,
	)
	# Expired or Expiring Soon, for Needs You (one_inventory/batches.py).
	for one in found:
		one["state"] = batches.state(one.expiry_date, one.batch_qty)
	return found


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
			"owner",
		],
		order_by="posting_datetime desc, creation desc",
		limit=MOST,
	)
	# A stock entry says what kind of move it was, and what for: issued,
	# moved, made.
	entries = {one.voucher_no for one in moves if one.voucher_type == "Stock Entry"}
	kinds = {
		entry.name: entry
		for entry in (
			frappe.get_all(
				"Stock Entry",
				filters={"name": ["in", list(entries)]},
				fields=["name", "stock_entry_type", "purpose"],
			)
			if entries
			else []
		)
	}
	for one in moves:
		entry = kinds.get(one.voucher_no)
		one["kind"] = entry.stock_entry_type if entry else one.voucher_type
		one["purpose"] = entry.purpose if entry else None
		one["called"] = _called(one.warehouse)
		one["project_name"] = (
			frappe.get_cached_value("Project", one.project, "project_name") if one.project else None
		)
		one["by"] = frappe.utils.get_fullname(one.owner) if one.owner else None
	return merged(moves)


def merged(moves: list) -> list:
	"""A move out of one warehouse and into another on the same document is
	one move, from the one to the other. Pure over the ledger's rows."""
	out, seen = [], {}
	for one in moves:
		key = (one["voucher_type"], one["voucher_no"])
		twin = seen.get(key)
		if (
			twin
			and "from" not in twin
			and flt(twin["actual_qty"]) == -flt(one["actual_qty"])
			and twin["warehouse"] != one["warehouse"]
		):
			out_, in_ = (twin, one) if flt(twin["actual_qty"]) < 0 else (one, twin)
			twin.update(
				{
					"from": out_["called"],
					"to": in_["called"],
					"actual_qty": abs(flt(one["actual_qty"])),
					"left": [
						{"called": out_["called"], "qty": out_["qty_after_transaction"]},
						{"called": in_["called"], "qty": in_["qty_after_transaction"]},
					],
				}
			)
			continue
		seen[key] = one
		out.append(one)
	return out


def _buying(doc) -> dict | None:
	"""Who it is bought from and at what, in their own currency, what is on
	order and asked for, the quotes still open, and its buying prices."""
	if not (doc.is_purchase_item or doc.is_fixed_asset):
		return None
	suppliers = {}
	lines = []
	if _readable("Purchase Order"):
		lines = frappe.get_list(
			"Purchase Order",
			filters=[["Purchase Order Item", "item_code", "=", doc.name], ["docstatus", "=", 1]],
			fields=[
				"supplier",
				"currency",
				"transaction_date",
				"`tabPurchase Order Item`.rate as rate",
				"`tabPurchase Order Item`.base_rate as base_rate",
				"`tabPurchase Order Item`.uom as uom",
				"`tabPurchase Order Item`.qty as qty",
			],
			order_by="transaction_date desc, creation desc",
			limit=200,
		)
		for row in lines:
			one = suppliers.setdefault(row.supplier, _supplier(row.supplier))
			if one["last"] is None:
				one.update(
					last=row.transaction_date, rate=row.rate, base_rate=row.base_rate, currency=row.currency
				)
			elif one["before"] is None and row.rate != one["rate"]:
				one["before"] = row.rate
			one["qty"] += flt(row.qty)
			one["orders"] += 1
	# The item's own list of who supplies it, each with their part number.
	for row in doc.get("supplier_items") or []:
		one = suppliers.setdefault(row.supplier, _supplier(row.supplier))
		one.update(part_no=row.supplier_part_no, row=row.name)
	company = erpnext.get_default_company()
	defaults = next((row for row in doc.get("item_defaults") or [] if row.company == company), None)
	default = defaults.default_supplier if defaults else None
	if default and default not in suppliers:
		suppliers[default] = _supplier(default)
	agreed = _agreed(doc.name)
	images = _images("Supplier", suppliers)
	for one in suppliers.values():
		one["default"] = one["supplier"] == default
		one["image"] = images.get(one["supplier"])
		one["agreed"] = agreed.get(one["supplier"])
	orders = _open(
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
	)
	requests = _open(
		"Material Request",
		"Material Request Item",
		[
			"material_request_type as kind",
			"schedule_date as due",
			"status",
			"owner",
			"`tabMaterial Request Item`.project as project",
			"`tabMaterial Request Item`.qty as qty",
			"`tabMaterial Request Item`.ordered_qty as done",
		],
		doc.name,
		status=(
			"not in",
			("Ordered", "Transferred", "Issued", "Received", "Stopped", "Cancelled", "Manufactured"),
		),
	)
	for row in requests:
		row["by"] = frappe.utils.get_fullname(row.owner)
		row["project_name"] = _project_name(row.project)
	party_images = _images("Supplier", {row.party for row in orders})
	for row in orders:
		row["image"] = party_images.get(row.party)
	return {
		"suppliers": sorted(suppliers.values(), key=lambda one: (not one["default"], -one["orders"]))[:MOST],
		"default_row": defaults.name if defaults else None,
		"company": company,
		"orders": orders,
		"requests": requests,
		"quotes": _quotes(doc.name),
		"prices": _prices(doc.name, "buying"),
		# The last price paid, which a buying price is held against.
		"last_paid": (
			{
				"rate": lines[0].rate,
				"currency": lines[0].currency,
				"uom": lines[0].uom,
				"on": lines[0].transaction_date,
			}
			if lines
			else None
		),
		"can": {
			one: bool(frappe.has_permission(one, "create"))
			for one in ("Purchase Receipt", "Request for Quotation", "Supplier Quotation")
		},
	}


def _supplier(name: str) -> dict:
	return {
		"supplier": name,
		"last": None,
		"rate": None,
		"base_rate": None,
		"currency": None,
		"before": None,
		"qty": 0,
		"orders": 0,
		"part_no": None,
		"row": None,
	}


def _images(doctype: str, names) -> dict:
	"""Each party's picture (one_mail/faces.py dresses a party without one)."""
	names = [one for one in names if one]
	if not names:
		return {}
	return dict(
		frappe.get_all(doctype, filters={"name": ["in", names]}, fields=["name", "image"], as_list=True)
	)


def _project_name(project: str | None) -> str | None:
	return frappe.get_cached_value("Project", project, "project_name") if project else None


def _agreed(item: str) -> dict:
	"""What each supplier has agreed for it on a blanket order still running:
	the rate, how much is left of it, and until when."""
	if not _readable("Blanket Order"):
		return {}
	found = {}
	for row in frappe.get_list(
		"Blanket Order",
		filters=[
			["Blanket Order Item", "item_code", "=", item],
			["docstatus", "=", 1],
			["blanket_order_type", "=", "Purchasing"],
			["to_date", ">=", nowdate()],
		],
		fields=[
			"supplier",
			"to_date",
			"`tabBlanket Order Item`.rate as rate",
			"`tabBlanket Order Item`.qty as qty",
			"`tabBlanket Order Item`.ordered_qty as ordered",
		],
		order_by="to_date asc",
	):
		found.setdefault(
			row.supplier,
			{"rate": row.rate, "left": max(flt(row.qty) - flt(row.ordered), 0), "until": row.to_date},
		)
	return found


def _quotes(item: str) -> list:
	"""Supplier quotes for it still open, cheapest first by what one stock
	unit costs in the company's currency."""
	if not _readable("Supplier Quotation"):
		return []
	rows = frappe.get_list(
		"Supplier Quotation",
		filters=[
			["Supplier Quotation Item", "item_code", "=", item],
			["docstatus", "=", 1],
			["status", "not in", ("Ordered", "Expired", "Stopped", "Cancelled")],
		],
		fields=[
			"name",
			"supplier",
			"currency",
			"valid_till",
			"transaction_date",
			"`tabSupplier Quotation Item`.rate as rate",
			"`tabSupplier Quotation Item`.base_rate as base_rate",
			"`tabSupplier Quotation Item`.uom as uom",
			"`tabSupplier Quotation Item`.conversion_factor as conversion_factor",
			"`tabSupplier Quotation Item`.qty as qty",
		],
		limit=MOST,
	)
	today = getdate(nowdate())
	rows = [row for row in rows if not row.valid_till or getdate(row.valid_till) >= today]
	for row in rows:
		row["per_unit"] = flt(row.base_rate) / (flt(row.conversion_factor) or 1)
	rows.sort(key=lambda row: row["per_unit"])
	images = _images("Supplier", {row.supplier for row in rows})
	for i, row in enumerate(rows):
		row["image"] = images.get(row.supplier)
		row["cheapest"] = i == 0 and len(rows) > 1
	return rows


def _selling(doc) -> dict | None:
	"""What it sells for, what customers have ordered and not yet had and
	what of it can go now, the quotes still open, and who buys it, returns
	taken off."""
	if not doc.is_sales_item:
		return None
	customers = {}
	sales = []
	if _readable("Sales Invoice"):
		for row in frappe.get_list(
			"Sales Invoice",
			filters=[
				["Sales Invoice Item", "item_code", "=", doc.name],
				["docstatus", "=", 1],
				["posting_date", ">=", frappe.utils.add_months(nowdate(), -12)],
			],
			fields=[
				"customer",
				"currency",
				"posting_date",
				"is_return",
				"`tabSales Invoice Item`.stock_qty as qty",
				"`tabSales Invoice Item`.net_amount as their_amount",
				"`tabSales Invoice Item`.base_net_amount as amount",
				"`tabSales Invoice Item`.rate as rate",
				"`tabSales Invoice Item`.uom as uom",
			],
			order_by="posting_date desc, creation desc",
			limit=0,
		):
			one = customers.setdefault(row.customer, _customer(row.customer))
			# A return's quantity and amount are less than nothing, so it comes off.
			one["qty"] += flt(row.qty)
			one["amount"] += flt(row.amount)
			one["theirs"][row.currency] = one["theirs"].get(row.currency, 0) + flt(row.their_amount)
			if row.is_return:
				one["returned"] -= flt(row.qty)
				continue
			if one["last"] is None:
				one.update(last=row.posting_date, rate=row.rate, currency=row.currency)
			sales.append(
				{
					"rate": row.rate,
					"currency": row.currency,
					"uom": row.uom,
					"customer": row.customer,
					"on": row.posting_date,
				}
			)
	# Each customer's own code for it, the item's own customer row.
	for row in doc.get("customer_items") or []:
		if row.customer_name:
			customers.setdefault(row.customer_name, _customer(row.customer_name)).update(
				code=row.ref_code, row=row.name
			)
	images = _images("Customer", customers)
	for one in customers.values():
		one["image"] = images.get(one["customer"])
		# What they paid in their own currency, when they paid in one only.
		theirs = one.pop("theirs")
		one["their_amount"] = (
			theirs[one["currency"]] if len(theirs) == 1 and one["currency"] in theirs else None
		)
	orders = _open(
		"Sales Order",
		"Sales Order Item",
		[
			"customer as party",
			"delivery_date as due",
			"status",
			"project",
			"`tabSales Order Item`.qty as qty",
			"`tabSales Order Item`.delivered_qty as done",
			"`tabSales Order Item`.amount as amount",
			"`tabSales Order Item`.billed_amt as billed",
		],
		doc.name,
	)
	party_images = _images("Customer", {row.party for row in orders})
	for row in orders:
		row["image"] = party_images.get(row.party)
		row["project_name"] = _project_name(row.project)
		row["to_bill"] = flt(row.billed) < flt(row.amount)
	if doc.is_stock_item:
		ready(
			orders,
			sum(
				flt(one) for one in frappe.get_all("Bin", filters={"item_code": doc.name}, pluck="actual_qty")
			),
		)
	return {
		"orders": orders,
		"quotes": _quotations(doc.name),
		"customers": sorted(customers.values(), key=lambda one: -one["amount"])[:MOST],
		"prices": _prices(doc.name, "selling"),
		# Its sales in the last year, newest first, which a selling price is held against.
		"sales": sales[:MOST],
		"can": {
			one: bool(frappe.has_permission(one, "create"))
			for one in ("Delivery Note", "Sales Invoice", "Quotation", "Sales Order")
		},
	}


def ready(orders: list, on_hand: float) -> list:
	"""What is on hand goes to the orders soonest due first: each says how
	much of what is left can go now and how much is short. Pure."""
	free = max(flt(on_hand), 0)
	for row in sorted(orders, key=lambda one: str(one.get("due") or "9999")):
		goes = min(flt(row["left"]), free)
		free -= goes
		row["can_go"] = goes
		row["short"] = flt(row["left"]) - goes
	return orders


def _customer(name: str) -> dict:
	return {
		"customer": name,
		"qty": 0.0,
		"amount": 0.0,
		"theirs": {},
		"returned": 0.0,
		"last": None,
		"rate": None,
		"currency": None,
		"code": None,
		"row": None,
	}


def _quotations(item: str) -> list:
	"""Quotes for it still open, soonest to run out first, each with the
	customer or lead it is for."""
	if not _readable("Quotation"):
		return []
	rows = frappe.get_list(
		"Quotation",
		filters=[
			["Quotation Item", "item_code", "=", item],
			["docstatus", "=", 1],
			["status", "not in", ("Ordered", "Lost", "Expired", "Cancelled")],
		],
		fields=[
			"name",
			"quotation_to",
			"party_name",
			"customer_name",
			"currency",
			"valid_till",
			"`tabQuotation Item`.rate as rate",
			"`tabQuotation Item`.base_rate as base_rate",
			"`tabQuotation Item`.qty as qty",
			"`tabQuotation Item`.uom as uom",
		],
		order_by="`tabQuotation`.valid_till asc, `tabQuotation`.name asc",
		limit=MOST,
	)
	today = getdate(nowdate())
	rows = [row for row in rows if not row.valid_till or getdate(row.valid_till) >= today]
	images = {
		**_images("Customer", {row.party_name for row in rows if row.quotation_to == "Customer"}),
		**_images("Lead", {row.party_name for row in rows if row.quotation_to == "Lead"}),
	}
	for row in rows:
		row["image"] = images.get(row.party_name)
		row["soon"] = bool(row.valid_till and (getdate(row.valid_till) - today).days <= 7)
	return rows


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
	"""What it is made from and how many the stock on hand would make, the
	steps that make it, the work orders making it step by step, what was made
	in the last year, and, for a material, what it goes into and what the open
	work orders still need of it."""
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
			"raw_material_cost",
			"operating_cost",
			"currency",
			"project",
		],
		order_by="is_default desc, modified desc",
		limit=MOST,
	)
	materials, steps = [], []
	default = next((one for one in boms if one.is_default and one.is_active), None)
	if default:
		materials = frappe.get_all(
			"BOM Item",
			filters={"parent": default.name, "parenttype": "BOM"},
			fields=["item_code", "item_name", "qty", "uom", "stock_qty", "amount"],
			order_by="idx asc",
		)
		free = _free({one.item_code for one in materials})
		for one in materials:
			# What the free stock of it would make, at what one of the item takes.
			per_one = flt(one.stock_qty) / (flt(default.quantity) or 1)
			one["free"] = free.get(one.item_code, 0)
			one["covers"] = int(one["free"] // per_one) if per_one else None
		steps = frappe.get_all(
			"BOM Operation",
			filters={"parent": default.name, "parenttype": "BOM"},
			fields=["operation", "workstation", "time_in_mins", "operating_cost"],
			order_by="idx asc",
		)
	used_in = frappe.get_list(
		"BOM",
		filters=[["BOM Item", "item_code", "=", doc.name], ["is_active", "=", 1], ["docstatus", "=", 1]],
		fields=["name", "item", "item_name", "is_default", "`tabBOM Item`.qty as qty"],
		limit=MOST,
	)
	orders, made, needed = [], [], []
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
				"material_transferred_for_manufacturing as transferred",
				"process_loss_qty",
				"skip_transfer",
				"status",
				"project",
				"planned_start_date",
				"expected_delivery_date",
			],
			order_by="planned_start_date asc",
			limit=MOST,
		)
		today = getdate(nowdate())
		for row in orders:
			row["project_name"] = _project_name(row.project)
			row["late"] = bool(row.expected_delivery_date and getdate(row.expected_delivery_date) < today)
			row["steps"] = frappe.get_all(
				"Work Order Operation",
				filters={"parent": row.name, "parenttype": "Work Order"},
				fields=["operation", "workstation", "completed_qty", "status"],
				order_by="idx asc",
			)
			# What Finish would take, as the work order's own Finish button reckons it.
			ready = flt(row.qty if row.skip_transfer else row.transferred) - flt(row.produced_qty)
			row["can_finish"] = max(ready - flt(row.process_loss_qty), 0)
		made = frappe.get_list(
			"Work Order",
			filters={
				"production_item": doc.name,
				"docstatus": 1,
				"status": "Completed",
				"actual_end_date": [">=", frappe.utils.add_months(nowdate(), -12)],
			},
			fields=["name", "produced_qty", "project", "actual_end_date"],
			order_by="actual_end_date desc",
			limit=MOST,
		)
		for row in made:
			row["project_name"] = _project_name(row.project)
			row["actual_end_date"] = getdate(row.actual_end_date) if row.actual_end_date else None
		needed = frappe.get_list(
			"Work Order",
			filters=[
				["Work Order Item", "item_code", "=", doc.name],
				["docstatus", "=", 1],
				["status", "not in", ("Completed", "Closed", "Cancelled", "Stopped")],
			],
			fields=[
				"name",
				"production_item",
				"item_name",
				"project",
				"`tabWork Order Item`.required_qty as required",
				"`tabWork Order Item`.transferred_qty as transferred",
			],
			limit=MOST,
		)
		needed = [row for row in needed if flt(row.required) > flt(row.transferred)]
		for row in needed:
			row["left"] = flt(row.required) - flt(row.transferred)
			row["project_name"] = _project_name(row.project)
	# Something made here has its Making tab before its first bill of materials.
	made_here = doc.default_material_request_type == "Manufacture" and not doc.is_fixed_asset
	if not (boms or used_in or orders or made_here):
		return None
	return {
		"made_here": bool(made_here or boms or orders),
		"boms": boms,
		"materials": materials,
		"can_make": can_make(materials),
		"steps": steps,
		"used_in": used_in,
		"orders": orders,
		"made": made,
		"needed": needed,
		"can": {
			"Stock Entry": bool(frappe.has_permission("Stock Entry", "create")),
			# ERPNext's own page for the people on the floor, opened at a work order.
			"shop_floor": bool(
				frappe.db.exists("Page", "shop-floor") and frappe.get_cached_doc("Page", "shop-floor").is_permitted()
			),
		},
	}


def can_make(materials: list) -> dict | None:
	"""How many the free stock of its materials would make, and which runs
	out first. Pure."""
	counted = [one for one in materials if one.get("covers") is not None]
	if not counted:
		return None
	first = min(counted, key=lambda one: one["covers"])
	return {"qty": first["covers"], "limit": first["item_name"] or first["item_code"]}


def _free(items) -> dict:
	"""What of each item is on hand and not held for work orders already."""
	free = {}
	for row in frappe.get_all(
		"Bin",
		filters={"item_code": ["in", list(items)]},
		fields=["item_code", "actual_qty", "reserved_qty_for_production"],
	):
		free[row.item_code] = free.get(row.item_code, 0) + flt(row.actual_qty) - flt(row.reserved_qty_for_production)
	return {item: max(qty, 0) for item, qty in free.items()}


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
