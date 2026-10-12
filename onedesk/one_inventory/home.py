"""OneInventory's Home (page/inventory, frontend/src/home): what needs
somebody today, and everything in OneInventory, each with what it is for.
How it works is in the module's README, Under the hood.
"""

import frappe
from frappe import _lt
from frappe.utils import add_days, flt, getdate, today

#: How many rows of each kind Needs You shows before it says how many more.
FEW = 5

#: The directory: (group, label, kind, target, what it is for). A kind is
#: DocType, Report or Page; a Masters kind opens One's Masters at it.
GROUPS = (
	("stock", _lt("Stock")),
	("buying", _lt("Buying")),
	("making", _lt("Making")),
	("equipment", _lt("Equipment")),
	("reports", _lt("Reports")),
	("setup", _lt("Setup")),
)
EVERYTHING = (
	("stock", _lt("Items"), "DocType", "Item", _lt("Everything you keep, buy, sell or make.")),
	("stock", _lt("Stock on Hand"), "Page", "stock-on-hand", _lt("What each warehouse holds now, and what it is worth.")),
	("stock", _lt("Receipts"), "DocType", "Purchase Receipt", _lt("Goods taken in from suppliers.")),
	("stock", _lt("Deliveries"), "DocType", "Delivery Note", _lt("Goods sent out to customers.")),
	("stock", _lt("Moves"), "DocType", "Stock Entry", _lt("Stock moved between warehouses, used up or added.")),
	("stock", _lt("Counts"), "DocType", "Stock Reconciliation", _lt("Stock counted, and set right where it was wrong.")),
	("stock", _lt("Lots"), "Page", "lots", _lt("Batches and serial numbers: what each lot holds, where, and what goes off soon.")),
	("stock", _lt("Batches"), "DocType", "Batch", _lt("Lots of goods that go off, with their dates.")),
	("stock", _lt("Serial Numbers"), "DocType", "Serial No", _lt("Single pieces kept track of by their number.")),
	("stock", _lt("Pick Lists"), "DocType", "Pick List", _lt("What to fetch from where, for an order.")),
	("stock", _lt("Packing Slips"), "DocType", "Packing Slip", _lt("What went in each box of a delivery.")),
	("stock", _lt("Delivery Trips"), "DocType", "Delivery Trip", _lt("A van's round of deliveries.")),
	("stock", _lt("Landed Costs"), "DocType", "Landed Cost Voucher", _lt("Freight and duty added to what goods cost.")),
	("stock", _lt("Item Prices"), "DocType", "Item Price", _lt("What each item is bought and sold for.")),
	("stock", _lt("Quality Inspections"), "DocType", "Quality Inspection", _lt("Goods checked on the way in, out or while made.")),
	("buying", _lt("To Order"), "Report", "To Order", _lt("What runs low, and orders for it.")),
	("buying", _lt("Material Requests"), "DocType", "Material Request", _lt("Goods asked for by the stores, the workshop or a project.")),
	("buying", _lt("Quotes"), "Page", "quotes", _lt("Ask suppliers for prices, see their answers side by side and order the cheapest.")),
	("buying", _lt("Requests for Quotation"), "DocType", "Request for Quotation", _lt("Suppliers asked for their prices.")),
	("buying", _lt("Supplier Quotations"), "DocType", "Supplier Quotation", _lt("The prices suppliers gave.")),
	("buying", _lt("Quote Comparison"), "Report", "Supplier Quotation Comparison", _lt("Suppliers' prices side by side.")),
	("buying", _lt("Purchase Orders"), "DocType", "Purchase Order", _lt("What was ordered, and what is still to come.")),
	("buying", _lt("Blanket Orders"), "DocType", "Blanket Order", _lt("A price agreed with a supplier for a year.")),
	("buying", _lt("Suppliers"), "DocType", "Supplier", _lt("Who you buy from.")),
	("buying", _lt("Supplier Scorecards"), "DocType", "Supplier Scorecard", _lt("How each supplier delivers, scored.")),
	("making", _lt("Shop Floor"), "Page", "floor", _lt("The work on the floor, step by step.")),
	("making", _lt("Plant Floor"), "Page", "plant", _lt("Each workstation, and what is running on it.")),
	("making", _lt("Work Orders"), "DocType", "Work Order", _lt("What to make, how many, and for whom.")),
	("making", _lt("Job Cards"), "DocType", "Job Card", _lt("Each step of a work order, with who did it and how long it took.")),
	("making", _lt("Bills of Materials"), "DocType", "BOM", _lt("What a product is made from, and its steps.")),
	("making", _lt("Production Plans"), "DocType", "Production Plan", _lt("Work orders and requests planned from sales orders.")),
	("making", _lt("Sent Out"), "Page", "sent-out", _lt("Work a supplier does on your materials: what went, what came back and when it is due.")),
	("making", _lt("Subcontracting Orders"), "DocType", "Subcontracting Order", _lt("Work a supplier does with your materials.")),
	("making", _lt("Subcontracting Receipts"), "DocType", "Subcontracting Receipt", _lt("What a supplier made, taken back in.")),
	("equipment", _lt("Assets"), "DocType", "Asset", _lt("The company's equipment, who has it and what it is worth.")),
	("equipment", _lt("Asset Movements"), "DocType", "Asset Movement", _lt("Equipment handed to someone or moved.")),
	("equipment", _lt("Maintenance"), "DocType", "Asset Maintenance", _lt("The services each piece of equipment needs.")),
	("equipment", _lt("Maintenance Log"), "DocType", "Asset Maintenance Log", _lt("Each service, due and done.")),
	("equipment", _lt("Repairs"), "DocType", "Asset Repair", _lt("Equipment mended, and what it cost.")),
	("equipment", _lt("Asset Value Adjustments"), "DocType", "Asset Value Adjustment", _lt("An asset's worth set right.")),
	("equipment", _lt("Asset Capitalization"), "DocType", "Asset Capitalization", _lt("Parts and work made into an asset.")),
	("reports", _lt("Stock Ledger"), "Report", "Stock Ledger", _lt("Every move of stock, one line each.")),
	("reports", _lt("Projected Stock"), "Report", "Stock Projected Qty", _lt("What you will have once orders come and go.")),
	("reports", _lt("Stock Ageing"), "Report", "Stock Ageing", _lt("How long stock has been sitting.")),
	("reports", _lt("Batch Expiry"), "Report", "Batch Item Expiry Status", _lt("Lots and when they go off.")),
	("reports", _lt("Stock by Batch"), "Report", "Batch-Wise Balance History", _lt("What each lot holds over time.")),
	("reports", _lt("Order Progress"), "Report", "Purchase Order Analysis", _lt("How far each purchase order has come.")),
	("reports", _lt("Request to Bill"), "Report", "Procurement Tracker", _lt("From the request to the supplier's bill.")),
	("reports", _lt("Buying by Month"), "Report", "Purchase Analytics", _lt("What was bought, month by month.")),
	("reports", _lt("Delivery Dates"), "Report", "Delayed Order Report", _lt("Customer orders that went out late.")),
	("reports", _lt("Stock against the Books"), "Report", "Stock and Account Value Comparison", _lt("Stock's worth against the accounts.")),
	("reports", _lt("Making Progress"), "Report", "Work Order Summary", _lt("How far each work order has come.")),
	("reports", _lt("Sent Out to Be Made"), "Report", "Subcontract Order Summary", _lt("What suppliers are making for you.")),
	("reports", _lt("Asset Register"), "Report", "Fixed Asset Register", _lt("Every asset with its cost and worth.")),
	("reports", _lt("Asset Balances"), "Report", "Asset Depreciations and Balances", _lt("What the equipment was worth and is worth now.")),
	("reports", _lt("Depreciation"), "Report", "Asset Depreciation Ledger", _lt("Each month's depreciation.")),
	("setup", _lt("Inventory Check"), "Report", "Inventory Check", _lt("What is not set up yet, with the fix.")),
	("setup", _lt("Warehouses"), "DocType", "Warehouse", _lt("Where stock is kept.")),
	("setup", _lt("Item Groups"), "Masters", "Item Group", _lt("The groups items are sorted into.")),
	("setup", _lt("Brands"), "Masters", "Brand", _lt("The makes items are sold under.")),
	("setup", _lt("Units"), "Masters", "UOM", _lt("What things are counted in.")),
	("setup", _lt("Attributes"), "Masters", "Item Attribute", _lt("Sizes, colours and the like, for an item's versions.")),
	("setup", _lt("Supplier Groups"), "Masters", "Supplier Group", _lt("The groups suppliers are sorted into.")),
	("setup", _lt("Price Lists"), "DocType", "Price List", _lt("The lists prices are kept in, for buying and selling.")),
	("setup", _lt("Workstations"), "DocType", "Workstation", _lt("Where work is done, and what an hour there costs.")),
	("setup", _lt("Plant Floors"), "DocType", "Plant Floor", _lt("The workshop's floors and their workstations.")),
	("setup", _lt("Operations"), "DocType", "Operation", _lt("The steps products are made in.")),
	("setup", _lt("Routings"), "DocType", "Routing", _lt("A set of steps used by more than one product.")),
	("setup", _lt("Subcontracted Items"), "DocType", "Subcontracting BOM", _lt("Which service a supplier charges for making what.")),
	("setup", _lt("Asset Categories"), "DocType", "Asset Category", _lt("Kinds of equipment, and how each loses worth.")),
	("setup", _lt("Locations"), "DocType", "Location", _lt("Where equipment is kept.")),
	("setup", _lt("Maintenance Teams"), "DocType", "Asset Maintenance Team", _lt("Who services the equipment.")),
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
		"everything": directory(),
	}


def _currency() -> str | None:
	import erpnext

	company = erpnext.get_default_company()
	return erpnext.get_company_currency(company) if company else None


def _worth() -> float | None:
	if not frappe.has_permission("Bin", "read"):
		return None
	got = frappe.get_list("Bin", fields=[{"SUM": "stock_value", "as": "worth"}])
	return flt(got[0].worth) if got else 0


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
			},
			fields=["name", "item_name", "qty", "produced_qty", "expected_delivery_date"],
			order_by="expected_delivery_date asc",
		)
		if frappe.has_permission("Work Order", "read")
		else []
	)
	return {
		"late": _kept(late.get("orders") or []),
		"low": _kept(low.get("low") or []),
		"lots": _kept(lots),
		"services": _kept([one for one in services.get("services") or [] if getdate(one["due"]) <= add_days(day, 7)]),
		"work": _kept([{**one, "expected_delivery_date": str(one.expected_delivery_date)} for one in work]),
		"drafts": drafts(),
	}


#: The papers a draft of which is work left half done.
DRAFTS = (
	("Purchase Receipt", _lt("Receipts")),
	("Delivery Note", _lt("Deliveries")),
	("Stock Entry", _lt("Moves")),
	("Stock Reconciliation", _lt("Counts")),
)


def drafts() -> list[dict]:
	"""For each kind of paper, how many drafts were left more than a day ago."""
	out = []
	for doctype, label in DRAFTS:
		if not frappe.has_permission(doctype, "read"):
			continue
		count = len(
			frappe.get_list(
				doctype,
				filters={"docstatus": 0, "modified": ["<", add_days(today(), -1)]},
				pluck="name",
			)
		)
		if count:
			out.append({"doctype": doctype, "label": str(label), "count": count})
	return out


def _may(kind: str, target: str) -> bool:
	if kind in ("DocType", "Masters"):
		return bool(frappe.has_permission(target, "read"))
	if not frappe.db.exists(kind, target):
		return False
	return bool(frappe.get_cached_doc(kind, target).is_permitted())


def directory() -> list[dict]:
	"""Everything in OneInventory the reader may open, with what it is for."""
	return [
		{"group": group, "label": str(label), "kind": kind, "target": target, "about": str(about)}
		for group, label, kind, target, about in EVERYTHING
		if _may(kind, target)
	]
