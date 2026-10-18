"""Equipment that needs servicing: when it is due, and on whose calendar.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, add_years, getdate, nowdate

PERIODS = {
	"Daily": (1, 0, 0),
	"Weekly": (7, 0, 0),
	"Monthly": (0, 1, 0),
	"Quarterly": (0, 3, 0),
	"Half-yearly": (0, 6, 0),
	"Yearly": (0, 0, 1),
	"2 Yearly": (0, 0, 2),
	"3 Yearly": (0, 0, 3),
}


def next_due(periodicity: str, start, last=None, end=None):
	"""One period after the later of the start and the last time it was done,
	unless that is after the end. Pure."""
	if periodicity not in PERIODS:
		return None
	base = getdate(last) if last and (not start or getdate(last) > getdate(start)) else getdate(start or nowdate())
	days, months, years = PERIODS[periodicity]
	due = add_years(add_months(add_days(base, days), months), years)
	if end and getdate(due) > getdate(end):
		return None
	return due


FROM = ("periodicity", "start_date", "last_completion_date", "end_date")


def due(doc, method=None) -> None:
	"""Asset Maintenance before_validate: every task has its next date, however
	the schedule is saved. ERPNext's form works it out as the dates are typed,
	so a schedule saved by Data Import, OneAI or a script had none, and none of
	its services were on anybody's calendar. ERPNext's own sum leaves it empty
	for a task with an end date."""
	before = {row.name: row for row in (doc.get_doc_before_save() or frappe._dict()).get("asset_maintenance_tasks") or []}
	for task in doc.get("asset_maintenance_tasks"):
		was = before.get(task.name)
		moved = was and any(str(task.get(field) or "") != str(was.get(field) or "") for field in FROM)
		if task.next_due_date and not moved:
			continue
		task.next_due_date = next_due(task.periodicity, task.start_date, task.last_completion_date, task.end_date)


def on_time(doc, method=None) -> None:
	"""Asset Maintenance Log before_validate: a service marked Overdue whose
	date has moved past today, when the one before it was done, is Planned
	again. ERPNext marks it Overdue and never takes it back."""
	if doc.maintenance_status == "Overdue" and doc.due_date and getdate(doc.due_date) >= getdate(nowdate()):
		doc.maintenance_status = "Planned"


def next_service(asset: str) -> dict | None:
	"""The earliest open maintenance on an asset."""
	found = frappe.get_all(
		"Asset Maintenance Log",
		filters={"asset_name": asset, "maintenance_status": ["in", ["Planned", "Overdue"]], "docstatus": 0},
		fields=["name", "task_name", "due_date", "maintenance_status"],
		order_by="due_date asc",
		limit=1,
	)
	return found[0] if found else None


def unscheduled() -> list[str]:
	"""Registered assets marked Maintenance Required with no schedule."""
	return frappe.db.sql_list(
		"""select asset.name from `tabAsset` asset
		where asset.docstatus = 1 and asset.maintenance_required = 1
		and not exists (select 1 from `tabAsset Maintenance` plan where plan.asset_name = asset.name)
		order by asset.name"""
	)


def add_team(company: str) -> str:
	"""A maintenance team of one: whoever made it, as its manager."""
	user = frappe.session.user
	return (
		frappe.get_doc(
			{
				"doctype": "Asset Maintenance Team",
				"maintenance_team_name": _("Maintenance"),
				"company": company,
				"maintenance_manager": user,
				"maintenance_team_members": [{"team_member": user, "maintenance_role": "Maintenance Manager"}],
			}
		)
		.insert()
		.name
	)


def named(doc, method=None) -> None:
	"""Asset Maintenance Log before_validate: the asset's own name, for its
	list and the calendar. ERPNext's log keeps only the asset's number and its
	item, and both pickups are a Pickup Truck."""
	if doc.asset_name:
		doc.one_asset_title = frappe.db.get_value("Asset", doc.asset_name, "asset_name") or doc.asset_name
