"""What OneAI does in OneFactory: reads the work orders, the shop floor, the
plant floors and the work sent to suppliers as the reader sees them, and
drafts a work order as a card the reader approves. AGENTS.md lists each
tool.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import flt, get_fullname

# What OneAI changes in OneFactory: every change it suggests is a card of its
# own kind (plan_work_order), and nothing here is a call of OneFactory's own.
REACH = {}

NOT_FOR_AI = {
	"control.save_workshop": "The company's cost account and warehouses are set once, in Settings, by whoever keeps the books.",
}

FLOOR = "floor"
HOME = "onefactory"

_IN_HAND = {
	"label": _lt("What is the workshop making?"),
	"ask": _lt("Which work orders are open, for what, how far along, and which are late?"),
	"can": "read",
	"expects": "list_records",
}
_ON_FLOOR = {
	"label": _lt("What is running on the floor?"),
	"ask": _lt("Which steps is someone on now, for how long, which are paused, and which are short of materials?"),
	"can": "read",
	"expects": "on_the_floor",
}
_MACHINES = {
	"label": _lt("How are the workstations doing?"),
	"ask": _lt("Which workstations are making, which are stopped and why, and what is running on each?"),
	"can": "read",
	"expects": "plant_floor_now",
}
_HOW_FAR = {
	"label": _lt("How far along is it?"),
	"ask": _lt("How far along is this work order, step by step, and is everything it needs in the stores?"),
	"can": "read",
	"expects": "work_order_facts",
}
_MAKE = {
	"label": _lt("Make a work order"),
	"ask": _lt("Draft a work order to make ten of this, with its own bill of materials."),
	"can": "create",
	"doctype": "Work Order",
	"expects": "plan_work_order",
}
_OUT_NOW = {
	"label": _lt("What is out with suppliers?"),
	"ask": _lt("What is out with suppliers now, what went to each, what came back, and what is late?"),
	"can": "read",
	"expects": "sent_out_now",
}

SUGGESTIONS = {
	f"page:{HOME}": [_ON_FLOOR, _OUT_NOW],
	f"page:{FLOOR}": [_ON_FLOOR, _IN_HAND],
	"Work Order": [_HOW_FAR, _IN_HAND],
	"BOM": [_MAKE, _IN_HAND],
	"Job Card": [_ON_FLOOR, _IN_HAND],
	"Workstation": [_MACHINES, _ON_FLOOR],
	"Plant Floor": [_MACHINES, _ON_FLOOR],
	"Subcontracting Order": [_OUT_NOW],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on the Home, the Shop Floor and ERPNext's two making pages."""
	if said.get("page") == FLOOR:
		return (
			"The reader is on the Shop Floor, which shows the open work orders with how far their steps have got, "
			"and each step's job card to start, pause, record and close. on_the_floor reads what is running now; "
			"work_order_facts reads one work order; the open work orders are list_records on Work Order with "
			"docstatus 1 and status in Not Started or In Process, by expected_delivery_date. How the page works is in OneFactory's documentation (how_to)."
		)
	if said.get("page") == HOME:
		return (
			"The reader is on OneFactory's Home, which shows the open work orders, the steps running now, the work "
			"orders late or due to start, the work late back from suppliers and the drafts left, and everything in "
			"OneFactory with what it is for. on_the_floor reads the floor now and sent_out_now what is with suppliers; "
			"late work orders are list_records on Work Order with docstatus 1, status in Not Started or In Process and "
			"expected_delivery_date before today. How each part works is in OneFactory's documentation (how_to)."
		)
	if said.get("page") == "production-plan-visualizer":
		return (
			"The reader is on the Production Plan Visualizer, which draws one Production Plan as a tree: the items "
			"it makes, their work orders and the sub-assemblies under them. The plan itself is get_record on "
			"Production Plan; its work orders are list_records on Work Order with production_plan set to it."
		)
	if said.get("page") == "bom-comparison-tool":
		return (
			"The reader is on the BOM Comparison Tool, which sets two bills of materials side by side and shows "
			"which fields, materials and quantities differ. Each bill is get_record on BOM."
		)
	return None


def _steps(order) -> list[dict]:
	return [
		{
			"step": row.operation,
			"workstation": row.workstation,
			"done": flt(row.completed_qty),
			"of": flt(order.qty),
			"minutes_planned": flt(row.time_in_mins),
			"minutes_taken": flt(row.actual_operation_time),
		}
		for row in order.operations
	]


def on_the_floor(
	workstation: Annotated[str, "Only the steps at this workstation, by name."] | None = None,
) -> dict:
	"""What the Shop Floor shows now: how many work orders are open, each step
	someone is on and for how long, the paused ones, those waiting to start, and
	the steps short of materials."""
	from onedesk.one_factory import floor

	if not frappe.has_permission("Job Card", "read"):
		return {"error": "The reader may not see job cards."}
	filters = {"docstatus": 0, "is_subcontracted": 0}
	if workstation:
		filters["workstation"] = frappe.db.get_value("Workstation", {"name": workstation}) or frappe.db.get_value(
			"Workstation", {"workstation_name": workstation}
		)
		if not filters["workstation"]:
			return {"error": f"No workstation is called {workstation}."}
	steps = []
	for card in frappe.get_list(
		"Job Card",
		filters=filters,
		fields=["name", "operation", "workstation", "work_order", "item_name", "status", "is_paused", "for_quantity", "total_completed_qty"],
		order_by="expected_start_date asc, name asc",
	):
		logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": card.name},
			fields=["employee", "from_time", "to_time", "time_in_mins"],
		)
		open_log = next((log for log in logs if log.from_time and not log.to_time), None)
		minutes = sum(flt(log.time_in_mins) for log in logs if log.to_time)
		if open_log and not card.is_paused:
			minutes += (frappe.utils.now_datetime() - frappe.utils.get_datetime(open_log.from_time)).total_seconds() / 60
		people = sorted({log.employee for log in logs if log.employee})
		short = [
			row.get("item_name")
			for row in floor.shop_floor.get_job_card_materials(card.name)
			if row.get("status") == "short"
		]
		steps.append(
			{
				"job_card": card.name,
				"step": card.operation,
				"workstation": card.workstation,
				"work_order": card.work_order,
				"makes": card.item_name,
				"state": "running" if floor.running_now(card) else "paused" if card.is_paused else "waiting" if card.status == "Open" else card.status,
				"done": flt(card.total_completed_qty),
				"of": flt(card.for_quantity),
				"minutes": round(minutes),
				"people": [frappe.db.get_value("Employee", who, "employee_name") or who for who in people],
				"short_of": short,
			}
		)
	return {"figures": floor.figures(), "steps": steps}


def plant_floor_now(
	plant: Annotated[str, "The plant floor, by name. Left out, the first one."] | None = None,
) -> dict:
	"""What a plant floor holds now: each workstation's status, the steps
	running on it and who is on them, how many wait there, and what the
	floor's warehouse holds."""
	from onedesk.one_factory import plant as plants

	if not frappe.has_permission("Workstation", "read"):
		return {"error": "The reader may not see workstations."}
	if plant and not frappe.db.exists("Plant Floor", plant):
		return {"error": f"No plant floor is called {plant}."}
	said = plants.now(plant=plant)
	if not said["plant"]:
		return {"error": "There is no plant floor yet."}
	return {
		"plant": said["plant"].name,
		"floors": [one.name for one in said["floors"]],
		"figures": said["figures"],
		"workstations": [
			{
				"workstation": one["name"],
				"type": one["workstation_type"],
				"status": one["status"],
				"running": [
					{"step": step["operation"], "makes": step["item_name"], "work_order": step["work_order"], "people": step["people"]}
					for step in one["running"]
				],
				"waiting": one["waiting"],
			}
			for one in said["workstations"]
		],
		"stock": [
			{"item": one["item_name"], "here": one["actual_qty"], "kept_for_making": one["for_making"], "unit": one["uom"]}
			for one in said["stock"]
		],
	}


def sent_out_now() -> dict:
	"""What the Sent Out page shows: the orders still out with suppliers,
	each with what it makes and how much came back, the materials sent and
	used, when it is due back and whether it is late, and the figures."""
	from onedesk.one_factory import sent_out

	if not frappe.has_permission("Subcontracting Order", "read"):
		return {"error": "The reader may not see work sent out."}
	return {
		"figures": sent_out.figures(),
		"out": [
			{
				"order": one["name"],
				"supplier": one["supplier_name"] or one["supplier"],
				"status": one["status"],
				"project": one["project_name"],
				"makes": [{"item": row["name"], "qty": row["qty"], "back": row["back"], "unit": row["uom"]} for row in one["makes"]],
				"materials_sent": [{"item": row["name"], "sent": row["sent"], "used": row["used"], "unit": row["uom"]} for row in one["materials"]],
				"due_back": one["schedule_date"],
				"late": one["late"],
			}
			for one in sent_out.orders()
		],
		"not_ready": [{"purchase_order": one["name"], "supplier": one["supplier_name"]} for one in sent_out.to_order()],
	}


def work_order_facts(work_order: Annotated[str, "The work order's number, such as MFG-WO-2026-00006."]) -> dict:
	"""One work order as the floor sees it: what it makes and for whom, each
	material needed against what went to the floor and what the stores still
	hold, each step's job cards, and what making it has cost so far."""
	if not frappe.db.exists("Work Order", work_order) or not frappe.has_permission("Work Order", "read", doc=work_order):
		return {"error": f"No work order the reader may see is {work_order}."}
	order = frappe.get_doc("Work Order", work_order)
	materials = []
	for row in order.required_items:
		needed = flt(row.required_qty)
		sent = flt(row.transferred_qty)
		held = flt(frappe.db.get_value("Bin", {"item_code": row.item_code, "warehouse": row.source_warehouse}, "actual_qty")) if row.source_warehouse else 0
		materials.append(
			{
				"item": row.item_name or row.item_code,
				"needed": needed,
				"sent_to_the_floor": sent,
				"used": flt(row.consumed_qty),
				"in_the_stores": held,
				"short": max(needed - sent - held, 0),
				"unit": row.stock_uom,
			}
		)
	cards = frappe.get_all(
		"Job Card",
		filters={"work_order": order.name, "docstatus": ["<", 2]},
		fields=["name", "operation", "status", "total_completed_qty", "for_quantity"],
	)
	made = frappe.get_all(
		"Stock Entry",
		filters={"work_order": order.name, "purpose": "Manufacture", "docstatus": 1},
		fields=[{"SUM": "total_outgoing_value", "as": "used"}, {"SUM": "total_additional_costs", "as": "time"}],
	)[0]
	return {
		"order": order.name,
		"makes": order.item_name,
		"qty": flt(order.qty),
		"made": flt(order.produced_qty),
		"status": order.status,
		"project": frappe.db.get_value("Project", order.project, "project_name") if order.project else None,
		"asked_by": get_fullname(frappe.db.get_value("Material Request", order.material_request, "owner")) if order.material_request else None,
		"wanted_by": str(order.expected_delivery_date) if order.expected_delivery_date else None,
		"materials": materials,
		"steps": _steps(order),
		"job_cards": [dict(one) for one in cards],
		"cost_so_far": {"materials": flt(made.used), "workshop_time": flt(made.time)},
	}


def plan_work_order(
	item: Annotated[str, "The item to make, by code or name, such as WIN-CS12."],
	qty: Annotated[float, "How many to make, in the item's own unit."],
	project: Annotated[str, "The project it is made for, by name or title."] | None = None,
	wanted_by: Annotated[str, "When it is wanted, as YYYY-MM-DD."] | None = None,
	why: Annotated[str, "In a sentence, why it is made."] | None = None,
) -> dict:
	"""Suggest a draft work order to make an item with its default bill of
	materials, as a card the reader approves. Its materials and steps come from
	the bill, and it takes them from the company's stores to its work in
	progress. Nothing is made until it is submitted."""
	from erpnext import get_default_company

	from onedesk.one_ai import proposals

	if not frappe.has_permission("Work Order", "create"):
		return {"error": "The reader may not make work orders."}
	code = frappe.db.get_value("Item", {"name": item}) or frappe.db.get_value("Item", {"item_name": item})
	if not code:
		return {"error": f"No item is called {item}."}
	bom = frappe.db.get_value("BOM", {"item": code, "is_default": 1, "is_active": 1, "docstatus": 1})
	if not bom:
		return {"error": f"{code} has no bill of materials to make it from."}
	if flt(qty) <= 0:
		return {"error": "Say how many to make."}
	changes = {"production_item": code, "bom_no": bom, "qty": flt(qty), "company": get_default_company()}
	if project:
		found = frappe.db.get_value("Project", {"name": project}) or frappe.db.get_value("Project", {"project_name": project})
		if not found:
			return {"error": f"No project is called {project}."}
		changes["project"] = found
	if wanted_by:
		changes["expected_delivery_date"] = str(frappe.utils.getdate(wanted_by))
	return {
		"proposal": proposals.propose("Create", "Work Order", changes={k: v for k, v in changes.items() if v}, why=why),
		"state": "Proposed",
	}


READS = (
	"work_order_facts",
	"on_the_floor",
	"plant_floor_now",
	"sent_out_now",
)
"""The tools OneAI reads here (registry/hooks.py lists them in one_ai_reads)."""


SUGGESTS = (
	"plan_work_order",
)
"""The tools OneAI suggests, each as a card a person applies here (registry/hooks.py lists them in one_ai_suggests)."""
