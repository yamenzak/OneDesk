"""What OneAI does with OneInventory's equipment (agent.py lists these tools):
what is out of order and which services are due, one asset's facts, and a
hand-over suggested as a card."""

from typing import Annotated

import frappe
from frappe.utils import flt


def upkeep_now(
	days: Annotated[int, "The services late or due within this many days. 30 if not said."] = 30,
) -> dict:
	"""What the Upkeep page shows: services due this week and late, the
	services not done yet that are late or due within the days asked, soonest
	first, with who does each, the equipment out of order and since when, and
	what repairs cost over the last twelve months."""
	from frappe.utils import add_days, getdate, today

	from onedesk.one_inventory import upkeep

	if not frappe.has_permission("Asset Maintenance Log", "read") and not frappe.has_permission("Asset Repair", "read"):
		return {"error": "The reader may not see services or repairs."}
	until = add_days(getdate(today()), max(0, int(days if days is not None else 30)))
	due = upkeep.due()
	soon = [one for one in due if one["due_date"] and getdate(one["due_date"]) <= until]
	return {
		"figures": upkeep.figures(),
		"services": [
			{"asset": one["asset_name"], "job": one["task_name"], "due": one["due_date"], "late": one["late"], "done_by": one["assign_to_name"]}
			for one in soon
		],
		"services_later": len(due) - len(soon),
		"out_of_order": [
			{"asset": one["asset_name"], "wrong": one["description"], "since": one["failure_date"], "days": one["days_out"]}
			for one in upkeep.repairs()
			if one["open"]
		],
	}


def _asset_named(asset: str) -> str | None:
	return frappe.db.get_value("Asset", {"name": asset}) or frappe.db.get_value("Asset", {"asset_name": asset})


def asset_facts(asset: Annotated[str, "The asset, by its number or its name, such as Pickup Truck 1."]) -> dict:
	"""One piece of equipment as its page says it: who has it and where it is
	kept, what it cost and is worth now, its next service and whether it is
	late, its repairs and what they cost, and changes to its value."""
	from onedesk.one_inventory import assets
	from onedesk.one_inventory.maintenance import next_service

	name = _asset_named(asset)
	if not name or not frappe.has_permission("Asset", "read", doc=name):
		return {"error": f"No asset the reader may see is {asset}."}
	doc = frappe.get_doc("Asset", name)
	said = assets.said(name)
	service = next_service(name) if doc.maintenance_required else None
	repairs = frappe.get_all(
		"Asset Repair",
		filters={"asset": name, "docstatus": ["<", 2]},
		fields=["name", "repair_status", "failure_date", "completion_date", "total_repair_cost", "description"],
		order_by="failure_date desc",
	)
	return {
		"asset": doc.name,
		"name": doc.asset_name,
		"item": doc.item_name or doc.item_code,
		"status": doc.status,
		"held_by": said["custodian_name"],
		"kept_at": doc.location,
		"cost": flt(said["cost"]),
		"worth_now": flt(said["worth"]),
		"next_service": {
			"task": service.task_name,
			"due": str(service.due_date),
			"late": frappe.utils.getdate(service.due_date) < frappe.utils.getdate(frappe.utils.today()),
		}
		if service
		else None,
		"repairs": [
			{
				"status": one.repair_status,
				"failed_on": str(one.failure_date),
				"mended_on": str(one.completion_date) if one.completion_date else None,
				"cost": flt(one.total_repair_cost),
				"what": one.description,
			}
			for one in repairs
		],
		"value_changes": [
			dict(one)
			for one in frappe.get_all(
				"Asset Value Adjustment",
				filters={"asset": name, "docstatus": 1},
				fields=["date", "current_asset_value as was", "new_asset_value as now"],
			)
		],
	}


def services_due() -> dict:
	"""Services on the company's equipment that are late or due within a
	month, soonest first, with who does each. Read as the reader may see the
	services.

	Home's services due (home.needs_you), not one of OneAI's tools: OneAI
	reads `upkeep_now(days=...)`."""
	from frappe.utils import add_days, getdate, today

	if not frappe.has_permission("Asset Maintenance Log", "read"):
		return {"error": "The reader may not see services."}
	day = getdate(today())
	out = []
	for one in frappe.get_list(
		"Asset Maintenance Log",
		filters=[["docstatus", "=", 0], ["maintenance_status", "in", ["Planned", "Overdue"]], ["due_date", "is", "set"], ["due_date", "<=", add_days(day, 30)]],
		fields=["name", "asset_maintenance", "task_name", "due_date", "assign_to_name"],
		order_by="due_date asc",
	):
		out.append(
			{
				"service": one.name,
				"asset": frappe.db.get_value("Asset", one.asset_maintenance, "asset_name") or one.asset_maintenance,
				"task": one.task_name,
				"due": str(one.due_date),
				"late": getdate(one.due_date) < day,
				"done_by": one.assign_to_name,
			}
		)
	return {"services": out, "late": sum(1 for one in out if one["late"])}


def plan_handover(
	asset: Annotated[str, "The asset, by its number or its name, such as Laptop Mariam."],
	employee: Annotated[str, "Who is given it, by employee number or name."],
	why: Annotated[str, "In a sentence, why it is handed over."] | None = None,
) -> dict:
	"""Suggest handing a piece of equipment to a person, from whoever has it
	now, as a card the reader approves. It is a draft handover until it is
	submitted, which tells the person and makes the sheet they sign."""
	from onedesk.one.company import reader_company

	from onedesk.one_ai import proposals

	if not frappe.has_permission("Asset Movement", "create"):
		return {"error": "The reader may not hand equipment over."}
	name = _asset_named(asset)
	if not name:
		return {"error": f"No asset is called {asset}."}
	to = frappe.db.get_value("Employee", {"name": employee, "status": "Active"}) or frappe.db.get_value(
		"Employee", {"employee_name": employee, "status": "Active"}
	)
	if not to:
		return {"error": f"Nobody working here is called {employee}."}
	holder = frappe.db.get_value("Asset", name, "custodian")
	if holder == to:
		return {"error": f"{employee} already has it."}
	row = {"asset": name, "to_employee": to}
	if holder:
		row["from_employee"] = holder
	changes = {
		"purpose": "Issue",
		"company": reader_company(),
		"transaction_date": str(frappe.utils.now_datetime()),
		"assets": [row],
	}
	return {"proposal": proposals.propose("Create", "Asset Movement", changes=changes, why=why), "state": "Proposed"}
