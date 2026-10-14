"""Shop Floor (page/floor, frontend/src/floor): the open work orders and each
step's job card, read through ERPNext's own Shop Floor. How it works is in
the module's README, Under the hood.
"""

import erpnext
import frappe
from erpnext.manufacturing.page.shop_floor import shop_floor
from frappe.utils import flt, get_datetime, getdate, now_datetime, nowdate

#: How many work orders the board shows before a search narrows them.
MOST = 40


@frappe.whitelist()
def read(
	work_order: str | None = None,
	workstation: str | None = None,
	done: bool | int = 0,
	search: str | None = None,
) -> dict:
	"""The board (open or done work orders), or one work order's or one
	workstation's job cards, and the figures over the page."""
	frappe.has_permission("Work Order", "read", throw=True)
	said = {
		"figures": figures(),
		"workstations": frappe.get_list("Workstation", fields=["name", "workstation_name", "status"], order_by="name asc"),
		"can": {
			"start": bool(frappe.has_permission("Job Card", "write")),
			"submit": bool(frappe.has_permission("Job Card", "submit")),
			"Stock Entry": bool(frappe.has_permission("Stock Entry", "create")),
			"Quality Inspection": bool(frappe.has_permission("Quality Inspection", "submit")),
			"Work Order": bool(frappe.has_permission("Work Order", "create")),
		},
		"employee": frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name"),
		"work_order": None,
		"steps": [],
	}
	if work_order or workstation:
		got = shop_floor.get_data(workstation=workstation, work_order=work_order)
		said["steps"] = [_step(one) for one in got.get("job_cards") or []]
		said["mode"] = got.get("mode")
		said["capacity"] = got.get("capacity")
		if work_order:
			said["work_order"] = _work_order(work_order)
		return said
	board = shop_floor.get_work_orders("completed" if frappe.utils.cint(done) else "open", 0, MOST, search)
	said["work_orders"] = [_card(one) for one in board["work_orders"]]
	said["total"] = board["total"]
	return said


def figures() -> dict:
	"""What is open, what is running now, what waits to start, and what was
	finished today, counted as ERPNext counts a job card."""
	# Open as the board has it: a work order whose steps are all done is the
	# floor's no more, though it waits for its finished goods.
	open_orders = shop_floor.get_work_orders("open", 0, 1)["total"]
	company = erpnext.get_default_company()
	drafts = frappe.get_all(
		"Job Card",
		filters={"docstatus": 0, "is_subcontracted": 0, "company": company},
		fields=["name", "status", "is_paused"],
	)
	running = [one.name for one in drafts if running_now(one)]
	return {
		"open": open_orders,
		"running": len(running),
		"waiting": sum(1 for one in drafts if one.status == "Open"),
		"done_today": frappe.db.count(
			"Job Card",
			{
				"docstatus": 1,
				"company": company,
				"modified": [">=", get_datetime(f"{getdate(nowdate())} 00:00:00")],
			},
		),
	}


def running_now(job_card) -> bool:
	"""A job card is running while a time log of it has started and not ended,
	and it is not paused. ERPNext leaves a row with neither for each employee."""
	if job_card.get("is_paused"):
		return False
	return bool(
		frappe.db.exists(
			"Job Card Time Log",
			{"parent": job_card.name, "from_time": ["is", "set"], "to_time": ["is", "not set"]},
		)
	)


def _card(one: dict) -> dict:
	"""One work order on the board, with its project by name and when it is wanted."""
	project, wanted = frappe.db.get_value("Work Order", one.name, ["project", "expected_delivery_date"])
	return {
		**one,
		"project": project,
		"wanted": str(wanted) if wanted else None,
		"project_name": frappe.db.get_value("Project", project, "project_name") if project else None,
		"workstation_name": one.get("workstation_name") or one.get("workstation"),
		"late": _late(one.name),
	}


def _late(work_order: str) -> bool:
	wanted = frappe.db.get_value("Work Order", work_order, "expected_delivery_date")
	return bool(wanted and getdate(wanted) < getdate(nowdate()))


def _work_order(name: str) -> dict:
	row = frappe.db.get_value(
		"Work Order",
		name,
		[
			"name",
			"production_item",
			"item_name",
			"qty",
			"produced_qty",
			"status",
			"project",
			"expected_delivery_date",
			"material_transferred_for_manufacturing as transferred",
			"skip_transfer",
			"process_loss_qty",
		],
		as_dict=True,
	)
	if not row:
		return None
	row["project_name"] = frappe.db.get_value("Project", row.project, "project_name") if row.project else None
	row["late"] = _late(name)
	row["image"] = frappe.get_cached_value("Item", row.production_item, "image")
	ready = flt(row.qty if row.skip_transfer else row.transferred) - flt(row.produced_qty)
	# What Finish would take, as the work order's own Finish button reckons it.
	row["can_finish"] = max(ready - flt(row.process_loss_qty), 0)
	return row


def _instructions(one: dict) -> dict | None:
	"""The operation's own instructions, less a description that only says its name again."""
	said = dict(one.get("instructions") or {})
	if (said.get("description") or "").strip().lower() == (one.operation or "").strip().lower():
		said["description"] = ""
	return said if said.get("description") or said.get("work_instruction") else None


def _step(one: dict) -> dict:
	"""One job card: who is on it, how long it has run, what is short of its
	materials, its instructions and its quality check, as ERPNext's page has
	them, and what its buttons may do now."""
	logs = one.get("time_logs") or []
	open_log = next((log for log in logs if log.get("from_time") and not log.get("to_time")), None)
	worked = sum(flt(log.get("time_in_mins")) for log in logs if log.get("to_time"))
	employees = sorted({log.get("employee") for log in logs if log.get("employee")})
	names = dict(
		frappe.get_all(
			"Employee",
			filters={"name": ["in", employees], "company": erpnext.get_default_company()},
			fields=["name", "employee_name"],
			as_list=True,
		)
	) if employees else {}
	draft = one.docstatus == 0
	return {
		"name": one.name,
		"operation": one.operation,
		"workstation": one.workstation,
		"work_order": one.work_order,
		"item": one.finished_good or one.production_item,
		"item_name": frappe.get_cached_value("Item", one.finished_good or one.production_item, "item_name"),
		"image": one.get("item_image"),
		"status": one.status,
		"docstatus": one.docstatus,
		"for_quantity": flt(one.for_quantity),
		"done": flt(one.total_completed_qty),
		"loss": flt(one.process_loss_qty),
		"uom": one.get("fg_uom") or one.stock_uom,
		"paused": bool(one.is_paused),
		"running": bool(open_log) and not one.is_paused,
		"since": str(open_log.get("from_time")) if open_log else None,
		"minutes": worked,
		"people": [names.get(who, who) for who in employees],
		"materials": one.get("materials") or [],
		"short": [row for row in one.get("materials") or [] if row.get("status") == "short"],
		"to_move": bool(one.get("make_material_request")) and not one.get("skip_material_transfer"),
		"instructions": _instructions(one),
		"qc": one.get("qc") or {},
		"expected": str(one.expected_end_date) if one.get("expected_end_date") else None,
		# What its buttons may do now, as ERPNext's page offers them.
		"may": {
			"start": draft and not open_log and not one.is_paused and one.status in ("Open", "Not Started", "Material Transferred"),
			"pause": draft and bool(open_log) and not one.is_paused,
			"resume": draft and bool(one.is_paused),
			"record": draft and (bool(open_log) or bool(one.is_paused)),
			"submit": draft and not open_log and flt(one.total_completed_qty) > 0,
			"finish": one.docstatus == 1 and one.status == "To Manufacture",
		},
		"late": bool(one.get("expected_end_date") and get_datetime(one.expected_end_date) < now_datetime() and draft),
	}
