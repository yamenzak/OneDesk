"""Servicing and mending the company's equipment, as OneAI and Home read
it: the services due, the repairs, each asset's plan and the log of what was
done, each as ERPNext's Asset Maintenance, Asset Maintenance Log and Asset
Repair keep it, which are frappe's own lists and forms. `done` is the log's
Mark Done. How it works is in the module's AGENTS.md.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, get_datetime, getdate, now_datetime, today

from onedesk.one.company import reader_company

MOST = 60
WEEK = 7


def figures() -> dict:
	"""Services due this week and those late, equipment out of order, and
	what repairs cost over the last twelve months."""
	out = {"this_week": None, "late": None, "broken": None, "repairs_cost": None}
	if frappe.has_permission("Asset Maintenance Log", "read"):
		open_ = frappe.get_list(
			"Asset Maintenance Log",
			filters={"docstatus": 0, "maintenance_status": ["in", ["Planned", "Overdue"]]},
			fields=["due_date"],
		)
		day = getdate(today())
		out.update(
			this_week=sum(1 for one in open_ if one.due_date and day <= getdate(one.due_date) <= getdate(add_days(day, WEEK))),
			late=sum(1 for one in open_ if one.due_date and getdate(one.due_date) < day),
		)
	if frappe.has_permission("Asset Repair", "read"):
		company = reader_company()
		out["broken"] = len(
			frappe.get_list(
				"Asset Repair", filters={"docstatus": 0, "repair_status": "Pending", "company": company}, pluck="name"
			)
		)
		out["repairs_cost"] = flt(
			sum(
				flt(one.repair_cost)
				for one in frappe.get_list(
					"Asset Repair",
					filters={"docstatus": 1, "company": company, "completion_date": [">=", add_months(today(), -12)]},
					fields=["repair_cost"],
				)
			)
		)
	return out


def _assets(names) -> dict:
	"""Each asset's own name and picture, {asset: row}."""
	names = [one for one in set(names) if one]
	if not names:
		return {}
	return {
		one.name: one
		for one in frappe.get_all(
			"Asset",
			filters={"name": ["in", names], "company": reader_company()},
			fields=["name", "asset_name", "image", "location", "custodian"],
		)
	}


def due(search: str | None = None) -> list[dict]:
	"""Services not done yet, the soonest first, each with the asset, the job,
	who does it and whether it is late."""
	if not frappe.has_permission("Asset Maintenance Log", "read"):
		return []
	found = frappe.get_list(
		"Asset Maintenance Log",
		filters={"docstatus": 0, "maintenance_status": ["in", ["Planned", "Overdue"]]},
		fields=["name", "asset_maintenance", "task_name", "due_date", "assign_to_name", "maintenance_type", "periodicity"],
		order_by="due_date asc",
		limit=MOST,
	)
	assets = _assets(one.asset_maintenance for one in found)
	day = getdate(today())
	out = []
	for one in found:
		asset = assets.get(one.asset_maintenance) or frappe._dict()
		if search and search.lower() not in f"{asset.asset_name} {one.task_name} {one.assign_to_name}".lower():
			continue
		out.append(
			{
				**one,
				"due_date": str(one.due_date) if one.due_date else None,
				"asset": one.asset_maintenance,
				"asset_name": asset.asset_name or one.asset_maintenance,
				"image": asset.image,
				"late": bool(one.due_date) and getdate(one.due_date) < day,
			}
		)
	return out


def repairs(search: str | None = None) -> list[dict]:
	"""Repairs, those still open first, each with what is wrong, since when it
	has been out of use, and what it cost."""
	if not frappe.has_permission("Asset Repair", "read"):
		return []
	or_filters = {"asset_name": ["like", f"%{search}%"], "description": ["like", f"%{search}%"]} if search else None
	found = frappe.get_list(
		"Asset Repair",
		filters={"docstatus": ["<", 2], "company": reader_company()},
		or_filters=or_filters,
		fields=["name", "asset", "asset_name", "repair_status", "failure_date", "completion_date", "repair_cost", "description", "docstatus", "downtime"],
		order_by="failure_date desc",
		limit=MOST,
	)
	assets = _assets(one.asset for one in found)
	now = now_datetime()
	out = []
	for one in found:
		ended = get_datetime(one.completion_date) if one.completion_date else now
		out.append(
			{
				**one,
				"failure_date": str(one.failure_date) if one.failure_date else None,
				"completion_date": str(one.completion_date) if one.completion_date else None,
				"repair_cost": flt(one.repair_cost),
				"image": (assets.get(one.asset) or {}).get("image"),
				"open": one.docstatus == 0 and one.repair_status == "Pending",
				"days_out": max(0, (ended - get_datetime(one.failure_date)).days) if one.failure_date else None,
			}
		)
	return sorted(out, key=lambda one: not one["open"])


def plans(search: str | None = None) -> list[dict]:
	"""Each asset's plan: its team, and each job with how often, when it was
	last done and when it is next due."""
	if not frappe.has_permission("Asset Maintenance", "read"):
		return []
	found = frappe.get_list(
		"Asset Maintenance",
		filters={"company": reader_company()},
		fields=["name", "asset_name", "maintenance_team", "maintenance_manager_name"],
		order_by="modified desc",
		limit=MOST,
	)
	assets = _assets(one.asset_name for one in found)
	tasks: dict = {}
	for row in frappe.get_all(
		"Asset Maintenance Task",
		filters={"parent": ["in", [one.name for one in found] or [""]]},
		fields=["parent", "maintenance_task", "periodicity", "last_completion_date", "next_due_date", "assign_to_name", "maintenance_status"],
		order_by="idx",
	):
		tasks.setdefault(row.parent, []).append(
			{
				"task": row.maintenance_task,
				"periodicity": row.periodicity,
				"last": str(row.last_completion_date) if row.last_completion_date else None,
				"next": str(row.next_due_date) if row.next_due_date else None,
				"by": row.assign_to_name,
				"status": row.maintenance_status,
			}
		)
	out = []
	for one in found:
		asset = assets.get(one.asset_name) or frappe._dict()
		if search and search.lower() not in f"{asset.asset_name} {one.maintenance_team}".lower():
			continue
		jobs = tasks.get(one.name, [])
		out.append(
			{
				"name": one.name,
				"asset": one.asset_name,
				"asset_name": asset.asset_name or one.asset_name,
				"image": asset.image,
				"team": one.maintenance_team,
				"manager": one.maintenance_manager_name,
				"tasks": jobs,
				"next": min((job["next"] for job in jobs if job["next"]), default=None),
			}
		)
	return sorted(out, key=lambda one: (one["next"] is None, one["next"] or ""))


def log(search: str | None = None) -> list[dict]:
	"""What was done, the latest first: services done and repairs finished."""
	out = []
	if frappe.has_permission("Asset Maintenance Log", "read"):
		done = frappe.get_list(
			"Asset Maintenance Log",
			filters={"docstatus": 1, "maintenance_status": "Completed"},
			fields=["name", "asset_maintenance", "task_name", "completion_date", "assign_to_name", "actions_performed"],
			order_by="completion_date desc",
			limit=MOST,
		)
		assets = _assets(one.asset_maintenance for one in done)
		out += [
			{
				"kind": "service",
				"name": one.name,
				"asset_name": (assets.get(one.asset_maintenance) or {}).get("asset_name") or one.asset_maintenance,
				"what": one.task_name,
				"on": str(one.completion_date) if one.completion_date else None,
				"by": one.assign_to_name,
				"notes": frappe.utils.strip_html(one.actions_performed or "").strip(),
			}
			for one in done
		]
	if frappe.has_permission("Asset Repair", "read"):
		out += [
			{
				"kind": "repair",
				"name": one["name"],
				"asset_name": one["asset_name"],
				"what": one["description"],
				"on": (one["completion_date"] or "")[:10] or None,
				"cost": one["repair_cost"],
				"notes": "",
			}
			for one in repairs()
			if one["docstatus"] == 1
		]
	if search:
		out = [one for one in out if search.lower() in f"{one['asset_name']} {one['what']} {one.get('by') or ''}".lower()]
	return sorted(out, key=lambda one: one["on"] or "", reverse=True)[:MOST]


@frappe.whitelist(methods=["POST"])
def done(service: str, on: str | None = None, notes: str | None = None) -> str:
	"""A service recorded as done: ERPNext's own log, completed on the day and
	submitted, which works out the job's next date."""
	entry = frappe.get_doc("Asset Maintenance Log", service)
	entry.check_permission("submit")
	if entry.docstatus != 0:
		frappe.throw(_("{0} is recorded already.").format(service))
	entry.maintenance_status = "Completed"
	entry.completion_date = on or today()
	if notes:
		entry.actions_performed = notes
	entry.save()
	entry.submit()
	return entry.name
