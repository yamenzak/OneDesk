"""OneInventory's Home (page/inventory, frontend/src/home): what needs
somebody today, and everything in OneInventory, each with what it is for.
How it works is in the module's AGENTS.md.
"""

import erpnext
import frappe
from frappe import _lt
from frappe.utils import add_days, add_months, flt, getdate, today

FEW = 5

GROUPS = (
	("stock", _lt("Stock")),
	("buying", _lt("Buying")),
	("making", _lt("Manufacturing")),
	("quality", _lt("Quality")),
	("equipment", _lt("Assets")),
	("reports", _lt("Reports")),
	("setup", _lt("Setup")),
)
REPORT_SECTIONS = (
	("stock", _lt("Stock")),
	("lots", _lt("Batch and Serial No")),
	("buying", _lt("Buying and Selling")),
	("making", _lt("Manufacturing")),
	("quality", _lt("Quality")),
	("equipment", _lt("Assets")),
	("books", _lt("Accounting")),
)
REPORT_TOPICS = {
	"Stock Ledger": "stock",
	"Stock Projected Qty": "stock",
	"Stock Ageing": "stock",
	"Warehouse Wise Stock Balance": "stock",
	"Warehouse wise Item Balance Age and Value": "stock",
	"warehouse-capacity-summary": "stock",
	"Item Shortage Report": "stock",
	"Item Wise Consumption": "stock",
	"Product Bundle Balance": "stock",
	"Batch Item Expiry Status": "lots",
	"Available Batch Report": "lots",
	"Serial and Batch Wise Stock Balance": "lots",
	"Available Serial No": "lots",
	"Serial No Ledger": "lots",
	"Batch-Wise Balance History": "lots",
	"Purchase Order Analysis": "buying",
	"Procurement Tracker": "buying",
	"Purchase Analytics": "buying",
	"Item Prices": "buying",
	"Delayed Order Report": "buying",
	"Work Order Summary": "making",
	"Material Requirements Planning Report": "making",
	"Downtime Analysis": "making",
	"bom-comparison-tool": "making",
	"Subcontract Order Summary": "making",
	"Review": "quality",
	"Fixed Asset Register": "equipment",
	"Asset Depreciations and Balances": "equipment",
	"Asset Depreciation Ledger": "equipment",
	"Asset Activity": "equipment",
	"COGS By Item Group": "books",
	"Stock and Account Value Comparison": "books",
}
SETUP_SECTIONS = (
	("settings", _lt("Settings")),
	("stock", _lt("Stock")),
	("items", _lt("Items")),
	("buying", _lt("Buying")),
	("making", _lt("Manufacturing")),
	("quality", _lt("Quality")),
	("equipment", _lt("Assets")),
)
SETUP_TOPICS = {
	"Inventory Check": "settings",
	"Stock Settings": "settings",
	"Buying Settings": "settings",
	"Manufacturing Settings": "settings",
	"Delivery Settings": "settings",
	"Item Variant Settings": "settings",
	"Warehouse": "stock",
	"Putaway Rule": "stock",
	"Inventory Dimension": "stock",
	"Stock Closing Entry": "stock",
	"UOM": "stock",
	"UOM Conversion Factor": "stock",
	"Item Group": "items",
	"Brand": "items",
	"Item Attribute": "items",
	"Price List": "items",
	"Supplier Group": "buying",
	"Supplier Scorecard Variable": "buying",
	"Workstation": "making",
	"Plant Floor": "making",
	"Operation": "making",
	"Routing": "making",
	"BOM Update Tool": "making",
	"Subcontracting BOM": "making",
	"Quality Feedback Template": "quality",
	"Asset Category": "equipment",
	"Location": "equipment",
	"Asset Maintenance Team": "equipment",
	"Asset Shift Factor": "equipment",
}

EVERYTHING = (
	("stock", _lt("Item"), "DocType", "Item", _lt("Everything you keep, buy, sell or make.")),
	("stock", _lt("Stock Summary"), "Page", "stock-on-hand", _lt("What each warehouse holds now, and what it is worth.")),
	("stock", _lt("Purchase Receipt"), "DocType", "Purchase Receipt", _lt("Goods taken in from suppliers.")),
	("stock", _lt("Delivery Note"), "DocType", "Delivery Note", _lt("Goods sent out to customers.")),
	("stock", _lt("Stock Entry"), "DocType", "Stock Entry", _lt("Stock moved between warehouses, used up or added.")),
	("stock", _lt("Stock Reconciliation"), "DocType", "Stock Reconciliation", _lt("Stock counted, and set right where it was wrong.")),
	("stock", _lt("Batch"), "DocType", "Batch", _lt("Lots of goods that go off, with their dates.")),
	("stock", _lt("Serial No"), "DocType", "Serial No", _lt("Single pieces kept track of by their number.")),
	("stock", _lt("Pick List"), "DocType", "Pick List", _lt("What to fetch from where, for an order.")),
	("stock", _lt("Packing Slip"), "DocType", "Packing Slip", _lt("What went in each box of a delivery.")),
	("stock", _lt("Delivery Trip"), "DocType", "Delivery Trip", _lt("A van's round of deliveries.")),
	("stock", _lt("Landed Cost Voucher"), "DocType", "Landed Cost Voucher", _lt("Freight and duty added to what goods cost.")),
	("stock", _lt("Item Price"), "DocType", "Item Price", _lt("What each item is bought and sold for.")),
	("stock", _lt("Item Alternative"), "DocType", "Item Alternative", _lt("What may be used in place of an item when it runs out.")),
	("stock", _lt("Item Lead Time"), "DocType", "Item Lead Time", _lt("How many days each item takes to buy or make.")),
	("stock", _lt("Item Standard Cost"), "DocType", "Item Standard Cost", _lt("What an item is valued at when it is kept at a standard cost.")),
	("buying", _lt("Reorder"), "Page", "to-order", _lt("What runs low, and orders for it.")),
	("buying", _lt("Material Request"), "DocType", "Material Request", _lt("Goods asked for by the stores, the workshop or a project.")),
	("buying", _lt("Request for Quotation"), "DocType", "Request for Quotation", _lt("Ask suppliers for prices, see their answers side by side and order the cheapest.")),
	("buying", _lt("Supplier Quotation"), "DocType", "Supplier Quotation", _lt("The prices suppliers gave.")),
	("buying", _lt("Supplier Quotation Comparison"), "Report", "Supplier Quotation Comparison", _lt("Suppliers' prices side by side.")),
	("buying", _lt("Purchase Order"), "DocType", "Purchase Order", _lt("What was ordered, and what is still to come.")),
	("buying", _lt("Blanket Order"), "DocType", "Blanket Order", _lt("A price agreed with a supplier for a year.")),
	("buying", _lt("Supplier"), "DocType", "Supplier", _lt("Who you buy from.")),
	("buying", _lt("Supplier Scorecard"), "DocType", "Supplier Scorecard", _lt("How each supplier delivers, scored.")),
	("making", _lt("Shop Floor"), "Page", "floor", _lt("The work on the floor, step by step.")),
	("making", _lt("Plant Floor"), "DocType", "Plant Floor", _lt("Each workstation, and what is running on it.")),
	("making", _lt("Work Order"), "DocType", "Work Order", _lt("What to make, how many, and for whom.")),
	("making", _lt("Job Card"), "DocType", "Job Card", _lt("Each step of a work order, with who did it and how long it took.")),
	("making", _lt("BOM"), "DocType", "BOM", _lt("What a product is made from, and its steps.")),
	("making", _lt("Production Plan"), "DocType", "Production Plan", _lt("Work orders and requests planned from sales orders.")),
	("making", _lt("Production Plan Visualizer"), "Page", "production-plan-visualizer", _lt("Production plans laid out over time.")),
	("making", _lt("Master Production Schedule"), "DocType", "Master Production Schedule", _lt("What to make each period, from forecasts and orders.")),
	("making", _lt("Sales Forecast"), "DocType", "Sales Forecast", _lt("What is expected to sell, to plan making by.")),
	("making", _lt("BOM Creator"), "DocType", "BOM Creator", _lt("Lay out a product's whole tree of parts at once.")),
	("making", _lt("Downtime Entry"), "DocType", "Downtime Entry", _lt("When a workstation stood still, and why.")),
	("making", _lt("Subcontracting Order"), "DocType", "Subcontracting Order", _lt("Work a supplier does on your materials: what went, what came back and when it is due.")),
	("making", _lt("Subcontracting Receipt"), "DocType", "Subcontracting Receipt", _lt("What a supplier made, taken back in.")),
	("quality", _lt("Quality Inspection"), "DocType", "Quality Inspection", _lt("Goods checked on the way in, out or while made.")),
	("quality", _lt("Quality Goal"), "DocType", "Quality Goal", _lt("What the business means to achieve, and how often it is checked.")),
	("quality", _lt("Quality Procedure"), "DocType", "Quality Procedure", _lt("How a piece of work is done, step by step.")),
	("quality", _lt("Quality Review"), "DocType", "Quality Review", _lt("A goal checked against its targets.")),
	("quality", _lt("Quality Action"), "DocType", "Quality Action", _lt("What is done to fix a problem, or stop one.")),
	("quality", _lt("Non Conformance"), "DocType", "Non Conformance", _lt("Work that did not follow its procedure.")),
	("quality", _lt("Quality Meeting"), "DocType", "Quality Meeting", _lt("A meeting on quality, its agenda and its minutes.")),
	("quality", _lt("Quality Feedback"), "DocType", "Quality Feedback", _lt("What a customer or a colleague thought of the work.")),
	("equipment", _lt("Asset"), "DocType", "Asset", _lt("The company's equipment, who has it and what it is worth.")),
	("equipment", _lt("Asset Movement"), "DocType", "Asset Movement", _lt("Equipment handed to someone or moved.")),
	("equipment", _lt("Asset Maintenance Log"), "DocType", "Asset Maintenance Log", _lt("Services due and what was done on each asset.")),
	("equipment", _lt("Asset Maintenance Log"), "DocType", "Asset Maintenance Log", _lt("Each service, due and done.")),
	("equipment", _lt("Asset Repair"), "DocType", "Asset Repair", _lt("Equipment mended, and what it cost.")),
	("equipment", _lt("Asset Value Adjustment"), "DocType", "Asset Value Adjustment", _lt("An asset's worth set right.")),
	("equipment", _lt("Asset Capitalization"), "DocType", "Asset Capitalization", _lt("Parts and work made into an asset.")),
	("equipment", _lt("Asset Shift Allocation"), "DocType", "Asset Shift Allocation", _lt("Which shifts an asset worked, for its depreciation.")),
	("reports", _lt("Stock Ledger"), "Report", "Stock Ledger", _lt("Every move of stock, one line each.")),
	("reports", _lt("Stock Projected Qty"), "Report", "Stock Projected Qty", _lt("What you will have once orders come and go.")),
	("reports", _lt("Stock Ageing"), "Report", "Stock Ageing", _lt("How long stock has been sitting.")),
	("reports", _lt("Batch Item Expiry Status"), "Report", "Batch Item Expiry Status", _lt("Lots and when they go off.")),
	("reports", _lt("Warehouse Wise Stock Balance"), "Report", "Warehouse Wise Stock Balance", _lt("What each warehouse holds, and its worth.")),
	("reports", _lt("Warehouse wise Item Balance Age and Value"), "Report", "Warehouse wise Item Balance Age and Value", _lt("How old and how much each warehouse's stock is.")),
	("reports", _lt("Warehouse Capacity Summary"), "Page", "warehouse-capacity-summary", _lt("How full each warehouse is against its putaway rules.")),
	("reports", _lt("Item Shortage Report"), "Report", "Item Shortage Report", _lt("Items wanted beyond what is on hand.")),
	("reports", _lt("Item Wise Consumption"), "Report", "Item Wise Consumption", _lt("How much of each item was used up.")),
	("reports", _lt("COGS By Item Group"), "Report", "COGS By Item Group", _lt("What sold goods cost, by item group.")),
	("reports", _lt("Item Prices"), "Report", "Item Prices", _lt("Each item's buying and selling prices, side by side.")),
	("reports", _lt("Product Bundle Balance"), "Report", "Product Bundle Balance", _lt("How many of each bundle the stock can make up.")),
	("reports", _lt("Available Batch Report"), "Report", "Available Batch Report", _lt("What each lot holds now.")),
	("reports", _lt("Serial and Batch Wise Stock Balance"), "Report", "Serial and Batch Wise Stock Balance", _lt("Stock by batch and serial number, in each warehouse.")),
	("reports", _lt("Available Serial No"), "Report", "Available Serial No", _lt("Every serial number in stock, and where.")),
	("reports", _lt("Serial No Ledger"), "Report", "Serial No Ledger", _lt("Where each serial number has been.")),
	("reports", _lt("Batch-Wise Balance History"), "Report", "Batch-Wise Balance History", _lt("What each lot holds over time.")),
	("reports", _lt("Purchase Order Analysis"), "Report", "Purchase Order Analysis", _lt("How far each purchase order has come.")),
	("reports", _lt("Procurement Tracker"), "Report", "Procurement Tracker", _lt("From the request to the supplier's bill.")),
	("reports", _lt("Purchase Analytics"), "Report", "Purchase Analytics", _lt("What was bought, month by month.")),
	("reports", _lt("Delayed Order Report"), "Report", "Delayed Order Report", _lt("When each customer order went out against the day it was promised; below nought is early.")),
	("reports", _lt("Stock and Account Value Comparison"), "Report", "Stock and Account Value Comparison", _lt("Stock's worth against the accounts.")),
	("reports", _lt("Work Order Summary"), "Report", "Work Order Summary", _lt("How far each work order has come.")),
	("reports", _lt("Material Requirements Planning Report"), "Report", "Material Requirements Planning Report", _lt("What the production schedule needs, against what is on hand and coming.")),
	("reports", _lt("Downtime Analysis"), "Report", "Downtime Analysis", _lt("How long workstations stood still, and why.")),
	("reports", _lt("BOM Comparison Tool"), "Page", "bom-comparison-tool", _lt("Two bills of materials side by side.")),
	("reports", _lt("Subcontract Order Summary"), "Report", "Subcontract Order Summary", _lt("What suppliers are making for you.")),
	("reports", _lt("Review"), "Report", "Review", _lt("Every quality action, with the review it came from.")),
	("reports", _lt("Fixed Asset Register"), "Report", "Fixed Asset Register", _lt("Every asset with its cost and worth.")),
	("reports", _lt("Asset Depreciations and Balances"), "Report", "Asset Depreciations and Balances", _lt("What the equipment was worth and is worth now.")),
	("reports", _lt("Asset Depreciation Ledger"), "Report", "Asset Depreciation Ledger", _lt("Each month's depreciation.")),
	("reports", _lt("Asset Activity"), "Report", "Asset Activity", _lt("What happened to each asset, and when.")),
	("setup", _lt("Inventory Check"), "Report", "Inventory Check", _lt("What is not set up yet, with the fix.")),
	("setup", _lt("Warehouse"), "DocType", "Warehouse", _lt("Where stock is kept.")),
	("setup", _lt("Putaway Rule"), "DocType", "Putaway Rule", _lt("Where arriving stock is put away, and how much each warehouse holds.")),
	("setup", _lt("Inventory Dimension"), "DocType", "Inventory Dimension", _lt("More ways to split stock, such as a shelf or a project.")),
	("setup", _lt("Stock Closing Entry"), "DocType", "Stock Closing Entry", _lt("Stock's balances kept at a date, so older moves need not be read again.")),
	("setup", _lt("Item Group"), "List", "Item Group", _lt("The groups items are sorted into.")),
	("setup", _lt("Brand"), "List", "Brand", _lt("The makes items are sold under.")),
	("setup", _lt("UOM"), "List", "UOM", _lt("What things are counted in.")),
	("setup", _lt("UOM Conversion Factor"), "DocType", "UOM Conversion Factor", _lt("How many of one unit make another.")),
	("setup", _lt("Item Attribute"), "List", "Item Attribute", _lt("Sizes, colours and the like, for an item's versions.")),
	("setup", _lt("Item Variant Settings"), "DocType", "Item Variant Settings", _lt("What a new version of an item copies from its template.")),
	("setup", _lt("Supplier Group"), "List", "Supplier Group", _lt("The groups suppliers are sorted into.")),
	("setup", _lt("Supplier Scorecard Variable"), "DocType", "Supplier Scorecard Variable", _lt("The figures a supplier's score is worked out from.")),
	("setup", _lt("Price List"), "DocType", "Price List", _lt("The lists prices are kept in, for buying and selling.")),
	("setup", _lt("Workstation"), "DocType", "Workstation", _lt("Where work is done, and what an hour there costs.")),
	("setup", _lt("Plant Floor"), "DocType", "Plant Floor", _lt("The workshop's floors and their workstations.")),
	("setup", _lt("Operation"), "DocType", "Operation", _lt("The steps products are made in.")),
	("setup", _lt("Routing"), "DocType", "Routing", _lt("A set of steps used by more than one product.")),
	("setup", _lt("BOM Update Tool"), "DocType", "BOM Update Tool", _lt("Swap a part for another in every bill of materials, or bring their costs up to date.")),
	("setup", _lt("Subcontracting BOM"), "DocType", "Subcontracting BOM", _lt("Which service a supplier charges for making what.")),
	("setup", _lt("Quality Feedback Template"), "DocType", "Quality Feedback Template", _lt("The questions feedback asks.")),
	("setup", _lt("Asset Category"), "DocType", "Asset Category", _lt("Kinds of equipment, and how each loses worth.")),
	("setup", _lt("Location"), "DocType", "Location", _lt("Where equipment is kept.")),
	("setup", _lt("Asset Maintenance Team"), "DocType", "Asset Maintenance Team", _lt("Who services the equipment.")),
	("setup", _lt("Asset Shift Factor"), "DocType", "Asset Shift Factor", _lt("How much more an asset wears on a longer shift.")),
	("setup", _lt("Delivery Settings"), "DocType", "Delivery Settings", _lt("What a customer is told when their delivery leaves.")),
	("setup", _lt("Stock Settings"), "DocType", "Stock Settings", _lt("How stock is valued and moved.")),
	("setup", _lt("Buying Settings"), "DocType", "Buying Settings", _lt("How buying works.")),
	("setup", _lt("Manufacturing Settings"), "DocType", "Manufacturing Settings", _lt("How making works.")),
)


@frappe.whitelist()
def read() -> dict:
	"""The figures, what needs somebody, and the directory, as the reader may
	see them."""
	needs = needs_you()
	return {
		"figures": {
			"worth": _worth(),
			"low": needs["low"]["count"],
			"late": needs["late"]["count"],
			"going_off": needs["lots"]["count"],
		},
		"currency": _currency(),
		"needs": needs,
		"groups": [{"key": key, "label": str(label)} for key, label in GROUPS],
		"sections": {
			"reports": [{"key": key, "label": str(label)} for key, label in REPORT_SECTIONS],
			"setup": [{"key": key, "label": str(label)} for key, label in SETUP_SECTIONS],
		},
		"everything": directory(),
		"may_make": [
			doctype
			for doctype in ("Item", "Purchase Receipt", "Stock Entry", "Material Request")
			if frappe.has_permission(doctype, "create")
		],
	}


def _currency() -> str | None:
	company = erpnext.get_default_company()
	return erpnext.get_company_currency(company) if company else None


def _worth() -> float | None:
	"""Stock Value, the reader's company's, as the Number Card counts it."""
	from onedesk.one_inventory import story

	return story._worth_now()


def _kept(rows: list) -> dict:
	return {"rows": rows[:FEW], "count": len(rows)}


def needs_you() -> dict:
	"""Purchase orders late, items running low, lots going off, services
	late or due this week, work orders past their date, and drafts left
	more than a day, each as the reader may see them."""
	from onedesk.one_inventory import ai, batches

	day = getdate(today())
	low = ai.running_low()
	late = ai.late_orders()
	services = ai.services_due()
	lots = (
		[
			{
				"name": one.name,
				"batch_id": one.batch_id,
				"item": one.item,
				"item_name": one.item_name,
				"qty": flt(one.batch_qty),
				"uom": one.stock_uom,
				"expiry_date": str(one.expiry_date),
				"gone": getdate(one.expiry_date) < day,
			}
			for one in batches.dated()
		]
		if frappe.has_permission("Batch", "read")
		else []
	)
	work = (
		frappe.get_list(
			"Work Order",
			filters={
				"docstatus": 1,
				"status": ["in", ("Not Started", "In Process")],
				"expected_delivery_date": ["<", day],
				"company": erpnext.get_default_company(),
			},
			fields=["name", "item_name", "qty", "produced_qty", "expected_delivery_date"],
			order_by="expected_delivery_date asc",
		)
		if frappe.has_permission("Work Order", "read")
		else []
	)
	return {
		"late": _kept(late.get("orders") or []),
		"low": _kept([{**one, "place": _place(one.get("warehouse"))} for one in low.get("low") or []]),
		"lots": {**_kept(lots), "until": str(add_days(today(), batches.SOON))},
		"services": _kept([one for one in services.get("services") or [] if getdate(one["due"]) <= add_days(day, 7)]),
		"work": _kept([{**one, "expected_delivery_date": str(one.expected_delivery_date)} for one in work]),
		"drafts": drafts(),
	}


def _place(warehouse: str | None) -> str | None:
	"""A warehouse by its own name, Stores rather than Stores - SGA."""
	return warehouse and (frappe.get_cached_value("Warehouse", warehouse, "warehouse_name") or warehouse)


DRAFTS = (
	("Purchase Receipt", _lt("Purchase Receipt")),
	("Delivery Note", _lt("Delivery Note")),
	("Stock Entry", _lt("Stock Entry")),
	("Stock Reconciliation", _lt("Stock Reconciliation")),
)


def drafts() -> list[dict]:
	"""For each kind of paper, how many drafts were left more than a day ago."""
	out = []
	company = erpnext.get_default_company()
	for doctype, label in DRAFTS:
		if not frappe.has_permission(doctype, "read"):
			continue
		count = len(
			frappe.get_list(
				doctype,
				filters={"docstatus": 0, "modified": ["<", add_days(today(), -1)], "company": company},
				pluck="name",
			)
		)
		if count:
			out.append({"doctype": doctype, "label": str(label), "count": count})
	return out


def _may(kind: str, target: str) -> bool:
	if kind in ("DocType", "List"):
		return bool(frappe.has_permission(target, "read"))
	if not frappe.db.exists(kind, target):
		return False
	return bool(frappe.get_cached_doc(kind, target).is_permitted())


def directory() -> list[dict]:
	"""Everything in OneInventory the reader may open, with what it is for."""
	return [
		{
			"group": group,
			"label": str(label),
			"kind": kind,
			"target": target,
			"about": str(about),
			"topic": {"reports": REPORT_TOPICS, "setup": SETUP_TOPICS}.get(group, {}).get(target),
			"filters": _filters(target) if kind == "Report" else None,
			"builder": _builder(target) if kind == "Report" else None,
		}
		for group, label, kind, target, about in EVERYTHING
		if _may(kind, target)
	]


def _builder(report: str) -> str | None:
	"""The record type a Report Builder report is read over, which opens as
	that list's report view rather than as a query report."""
	kind, doctype = frappe.get_cached_value("Report", report, ["report_type", "ref_doctype"]) or (None, None)
	return doctype if kind == "Report Builder" else None


def _filters(report: str) -> dict | None:
	"""What a report opens on where its own defaults show nothing: a year of
	serial numbers rather than a month, a serial number's item, and the
	schedule and warehouse that planning asks for before it shows a row."""
	if report == "Available Serial No":
		return {"from_date": add_months(today(), -12), "to_date": today()}
	if report == "Serial No Ledger":
		item = frappe.db.get_value("Serial No", {}, "item_code", order_by="creation desc")
		return {"item_code": item} if item else None
	if report == "Material Requirements Planning Report":
		said = {
			"warehouse": frappe.db.get_value("Warehouse", {"is_group": 0, "disabled": 0, "warehouse_name": "Stores"}),
			"mps": frappe.db.get_value("Master Production Schedule", {"docstatus": ["<", 2]}, "name", order_by="creation desc"),
		}
		return {key: value for key, value in said.items() if value} or None
	return None
