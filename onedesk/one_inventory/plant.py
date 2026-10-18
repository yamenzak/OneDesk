"""Plant Floor (page/plant, frontend/src/plant): a floor's workstations as
cards, what each is doing now, and the stock kept on the floor, read through
ERPNext's own Plant Floor and Workstation. How it works is in the module's
README, Under the hood.
"""

import erpnext
import frappe
from erpnext.manufacturing.doctype.plant_floor import plant_floor
from erpnext.manufacturing.doctype.workstation import workstation as workstations
from frappe.utils import flt

from onedesk.one_inventory import floor as shop

STATUSES = ("Production", "Off", "Idle", "Problem", "Maintenance", "Setup")


@frappe.whitelist()
def read(plant: str | None = None, workstation_type: str | None = None, status: str | None = None) -> dict:
	"""The floors, and one floor's workstations and stock."""
	frappe.has_permission("Workstation", "read", throw=True)
	floors = frappe.get_list(
		"Plant Floor",
		filters={"company": ["in", [erpnext.get_default_company(), "", None]]},
		fields=["name", "floor_name", "warehouse", "company"],
		order_by="creation asc",
	)
	said = {
		"floors": floors,
		"statuses": STATUSES,
		"can": {
			"Plant Floor": bool(frappe.has_permission("Plant Floor", "create")),
			"Workstation": bool(frappe.has_permission("Workstation", "write")),
			"Stock Entry": bool(frappe.has_permission("Stock Entry", "create")),
		},
		"plant": None,
		"workstations": [],
		"types": [],
		"stock": [],
	}
	chosen = next((one for one in floors if one.name == plant), floors[0] if floors else None)
	if not chosen:
		return said
	said["plant"] = chosen
	everything = workstations.get_workstations(plant_floor=chosen.name)
	said["types"] = sorted(
		{one for one in frappe.get_all("Workstation", filters={"plant_floor": chosen.name}, pluck="workstation_type") if one}
	)
	shown = workstations.get_workstations(
		plant_floor=chosen.name, workstation_type=workstation_type, workstation_status=status
	)
	said["workstations"] = [_workstation(one) for one in shown]
	said["figures"] = figures(everything)
	if chosen.warehouse and frappe.has_permission("Warehouse", "read", doc=chosen.warehouse):
		said["stock"] = [
			_stock(one)
			for one in plant_floor.get_stock_summary(chosen.warehouse)
			if flt(one.actual_qty) or flt(one.pending_qty) or flt(one.reserved_qty_for_production)
		]
	return said


def figures(rows: list) -> dict:
	"""How many workstations there are, how many are making, how many are
	stopped by a problem or for maintenance, and the steps running on them."""
	names = [one.name for one in rows]
	return {
		"workstations": len(rows),
		"making": sum(1 for one in rows if one.status == "Production"),
		"stopped": sum(1 for one in rows if one.status in ("Problem", "Maintenance")),
		"running": sum(len(_running(name)) for name in names),
	}


def _running(name: str) -> list:
	cards = frappe.get_all(
		"Job Card",
		filters={"workstation": name, "docstatus": 0, "is_paused": 0, "company": erpnext.get_default_company()},
		fields=["name", "operation", "work_order", "production_item", "is_paused"],
	)
	return [one for one in cards if shop.running_now(one)]


def _workstation(one: dict) -> dict:
	"""One workstation's card: its type, status and picture, the steps
	running on it and who is on them, and how many wait to start there."""
	running = []
	for card in _running(one.name):
		logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": card.name, "from_time": ["is", "set"], "to_time": ["is", "not set"]},
			fields=["employee", "from_time"],
		)
		people = [log.employee for log in logs]
		running.append(
			{
				"job_card": card.name,
				"operation": card.operation,
				"work_order": card.work_order,
				"item_name": frappe.get_cached_value("Item", card.production_item, "item_name"),
				"people": [frappe.db.get_value("Employee", who, "employee_name") or who for who in people if who],
				"since": str(min(log.from_time for log in logs)) if logs else None,
			}
		)
	return {
		"name": one.name,
		"description": one.description,
		"status": one.status,
		"workstation_type": frappe.db.get_value("Workstation", one.name, "workstation_type"),
		"image": one.on_status_image if one.status == "Production" else one.off_status_image,
		"running": running,
		"waiting": frappe.db.count(
			"Job Card",
			{"workstation": one.name, "docstatus": 0, "status": "Open", "company": erpnext.get_default_company()},
		),
	}


def _stock(one: dict) -> dict:
	"""One item kept on the floor, as ERPNext's stock summary reads it."""
	return {
		"item_code": one.item_code,
		"item_name": one.item_name,
		"image": one.image,
		"actual_qty": flt(one.actual_qty),
		"for_making": flt(one.reserved_qty_for_production),
		"coming": flt(one.pending_qty),
		"uom": frappe.get_cached_value("Item", one.item_code, "stock_uom"),
		"unit": frappe.get_cached_value("UOM", frappe.get_cached_value("Item", one.item_code, "stock_uom"), "symbol")
		or frappe.get_cached_value("Item", one.item_code, "stock_uom"),
	}
