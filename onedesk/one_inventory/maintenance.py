"""Equipment that needs servicing: when it is due, and on whose calendar.

ERPNext's **Asset Maintenance** is a schedule per asset — tasks, each with a
periodicity, a start and an optional end, and the person it is assigned to —
and an **Asset Maintenance Log** per due date, which somebody completes. It
assigns the person a to-do and marks a log Overdue once its day passes. Two
things were missing:

- **A schedule with an end date is never due.** ERPNext's
  `calculate_next_due_date` blanks the next due date whenever an end date is
  set (`or next_due_date` is true as soon as there is one), so a task that
  runs until the warranty ends has no due date, no log and no reminder.
  `due` (Asset Maintenance validate) works the date out again for those,
  from ERPNext's own periodicities (`next_due`, pure), and leaves it empty
  only when the next one falls after the end.
- **Due maintenance was on no calendar.** One's calendar has three layers
  for it (one_inventory/calendar.py): the reader's own, everybody's, and an
  asset's own, each opening the log to record it done. An asset's page says
  when its next service is (`next_service`, read by assets.said).
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_months, add_years, getdate, nowdate

#: ERPNext's periodicities, as (days, months, years).
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


def due(doc, method=None) -> None:
	"""Asset Maintenance validate: a task with an end date is due too."""
	for task in doc.get("asset_maintenance_tasks"):
		if task.end_date and not task.next_due_date:
			task.next_due_date = next_due(task.periodicity, task.start_date, task.last_completion_date, task.end_date)


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
