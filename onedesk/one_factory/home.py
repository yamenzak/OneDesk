"""OneFactory's Home (page/onefactory, frontend/src/factory/home): what needs
somebody today in the workshop, and everything in OneFactory, each with what
it is for. How it works is in the module's AGENTS.md.
"""

import erpnext
import frappe
from frappe import _lt
from frappe.utils import add_days, date_diff, flt, get_first_day, getdate, today

FEW = 5
OPEN = ("Not Started", "In Process", "Stock Reserved", "Stock Partially Reserved")

GROUPS = (
	("making", _lt("Making")),
	("planning", _lt("Planning")),
	("suppliers", _lt("Sent to Suppliers")),
	("reports", _lt("Reports")),
	("setup", _lt("Setup")),
)

EVERYTHING = (
	("making", _lt("Shop Floor"), "Page", "floor", _lt("The open work orders, and each step to start, pause and finish.")),
	("making", _lt("Plant Floor"), "DocType", "Plant Floor", _lt("Each workstation on a floor, what runs on it and the stock beside it.")),
	("making", _lt("Work Order"), "DocType", "Work Order", _lt("What to make, how many, and from what.")),
	("making", _lt("Job Card"), "DocType", "Job Card", _lt("One step of a work order, with who worked it and for how long.")),
	("making", _lt("BOM"), "DocType", "BOM", _lt("What a product is made from, and its steps.")),
	("making", _lt("BOM Creator"), "DocType", "BOM Creator", _lt("A product and its parts drawn as a tree, made into bills at once.")),
	("making", _lt("Downtime Entry"), "DocType", "Downtime Entry", _lt("A workstation stopped, for how long and why.")),
	("planning", _lt("Production Plan"), "DocType", "Production Plan", _lt("Work orders and material requests made at once from sales orders.")),
	("planning", _lt("Production Plan Visualizer"), "Page", "production-plan-visualizer", _lt("A production plan as a tree of its work orders.")),
	("planning", _lt("Master Production Schedule"), "DocType", "Master Production Schedule", _lt("How much of each product to make, week by week.")),
	("planning", _lt("Sales Forecast"), "DocType", "Sales Forecast", _lt("What is expected to sell, for the schedule to plan from.")),
	("suppliers", _lt("Subcontracting Order"), "DocType", "Subcontracting Order", _lt("Work sent to a supplier, with the materials it takes.")),
	("suppliers", _lt("Subcontracting Receipt"), "DocType", "Subcontracting Receipt", _lt("The goods a supplier sent back, and what they used.")),
	("suppliers", _lt("Subcontracting BOM"), "DocType", "Subcontracting BOM", _lt("Which service a supplier is paid for each product they make.")),
	("reports", _lt("Work Order Summary"), "Report", "Work Order Summary", _lt("Every work order, how far along and how late.")),
	("reports", _lt("Material Requirements Planning Report"), "Report", "Material Requirements Planning Report", _lt("What the schedule needs, and what to buy or make for it.")),
	("reports", _lt("Downtime Analysis"), "Report", "Downtime Analysis", _lt("How long each workstation stood still, and why.")),
	("reports", _lt("BOM Comparison Tool"), "Page", "bom-comparison-tool", _lt("Two bills of materials side by side.")),
	("reports", _lt("Subcontract Order Summary"), "Report", "Subcontract Order Summary", _lt("What went to each supplier, and what came back.")),
	("reports", _lt("Production Planning Report"), "Report", "Production Planning Report", _lt("Whether the stores hold what the open orders need.")),
	("reports", _lt("Job Card Summary"), "Report", "Job Card Summary", _lt("Every job card, how long it took and how late.")),
	("reports", _lt("Production Analytics"), "Report", "Production Analytics", _lt("Work orders opened and finished, month by month.")),
	("reports", _lt("BOM Stock Analysis"), "Report", "BOM Stock Analysis", _lt("How many of a product the stores can make now.")),
	("reports", _lt("BOM Explorer"), "Report", "BOM Explorer", _lt("Every part of a product, however deep.")),
	("reports", _lt("Process Loss Report"), "Report", "Process Loss Report", _lt("What was lost in making, work order by work order.")),
	("reports", _lt("Work Order Consumed Materials"), "Report", "Work Order Consumed Materials", _lt("What each work order took from the stores.")),
	("reports", _lt("Cost of Poor Quality Report"), "Report", "Cost of Poor Quality Report", _lt("What scrapped and reworked goods cost.")),
	("setup", _lt("Workstation"), "DocType", "Workstation", _lt("Where a step is done, with what it costs an hour.")),
	("setup", _lt("Operation"), "DocType", "Operation", _lt("The steps products are made in.")),
	("setup", _lt("Routing"), "DocType", "Routing", _lt("A set of steps in order, for bills that share them.")),
	("setup", _lt("BOM Update Tool"), "DocType", "BOM Update Tool", _lt("A part replaced in every bill at once, and costs brought up to date.")),
	("setup", _lt("Manufacturing Settings"), "DocType", "Manufacturing Settings", _lt("How work orders take materials and count time.")),
)

DRAFTS = (
	("Work Order", _lt("Work Order")),
	("Job Card", _lt("Job Card")),
	("BOM", _lt("BOM")),
	("Production Plan", _lt("Production Plan")),
	("Subcontracting Order", _lt("Subcontracting Order")),
)


@frappe.whitelist()
def read() -> dict:
	"""The figures, what needs somebody, and the directory, as the reader may
	see them."""
	from onedesk.one_factory import floor, sent_out

	frappe.has_permission("Work Order", "read", throw=True)
	needs = needs_you()
	on_floor = floor.figures()
	return {
		"figures": {
			"open": on_floor["open"],
			"running": on_floor["running"],
			"late": needs["late"]["count"],
			"out": sent_out.figures()["out"],
			"made": _made(),
		},
		"currency": _currency(),
		"today": today(),
		"needs": needs,
		"groups": [{"key": key, "label": str(label)} for key, label in GROUPS],
		"everything": directory(),
		"may_make": [doctype for doctype in ("Work Order", "BOM", "Production Plan") if frappe.has_permission(doctype, "create")],
	}


def _currency() -> str | None:
	company = erpnext.get_default_company()
	return erpnext.get_company_currency(company) if company else None


def _made() -> float | None:
	"""What the goods made this month are worth, the reader's company's, in
	its currency: the finished goods of each submitted Manufacture entry."""
	if not frappe.has_permission("Stock Entry", "read"):
		return None
	rows = frappe.get_list(
		"Stock Entry",
		filters={
			"docstatus": 1,
			"purpose": "Manufacture",
			"company": erpnext.get_default_company(),
			"posting_date": [">=", get_first_day(today())],
		},
		fields=["total_incoming_value"],
	)
	return flt(sum(flt(one.total_incoming_value) for one in rows))


def _kept(rows: list) -> dict:
	return {"rows": rows[:FEW], "count": len(rows)}


def _orders(filters: dict, order_by: str) -> list:
	return frappe.get_list(
		"Work Order",
		filters={"docstatus": 1, "status": ["in", OPEN], "company": erpnext.get_default_company(), **filters},
		fields=["name", "production_item", "item_name", "qty", "produced_qty", "stock_uom", "status", "planned_start_date", "expected_delivery_date"],
		order_by=order_by,
	)


def needs_you() -> dict:
	"""Work orders past the day they were wanted, work orders due to have
	started that have not, work back late from suppliers, and drafts left
	more than a day, each as the reader may see them."""
	from onedesk.one_factory import sent_out

	day = getdate(today())
	late = [
		{**one, "late_by": date_diff(day, one.expected_delivery_date)}
		for one in _orders({"expected_delivery_date": ["<", day]}, "expected_delivery_date asc")
	]
	start = [
		{**one, "planned_start_date": str(getdate(one.planned_start_date))}
		for one in _orders({"status": "Not Started", "planned_start_date": ["<", add_days(day, 1)]}, "planned_start_date asc")
	]
	back = [one for one in sent_out.orders() if one["late"]]
	return {
		"late": _kept(late),
		"start": _kept(start),
		"back": _kept(back),
		"drafts": drafts(),
	}


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
	if kind == "DocType":
		return bool(frappe.has_permission(target, "read"))
	if not frappe.db.exists(kind, target):
		return False
	return bool(frappe.get_cached_doc(kind, target).is_permitted())


def directory() -> list[dict]:
	"""Everything in OneFactory the reader may open, with what it is for."""
	return [
		{"group": group, "label": str(label), "kind": kind, "target": target, "about": str(about)}
		for group, label, kind, target, about in EVERYTHING
		if _may(kind, target)
	]
