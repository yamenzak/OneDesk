"""OneInventory on the calendar: maintenance that is due, from ERPNext's Asset
Maintenance Log. Clicking one opens the log, where it is recorded done. See
one_inventory/maintenance.py."""

import frappe
from frappe import _lt

from onedesk.one_calendar import layers

LAYERS = [
	{
		"key": "my-maintenance",
		"label": _lt("My Maintenance"),
		"color": "orange",
		"group": "Mine",
		"doctype": "Asset Maintenance Log",
		"rows": "onedesk.one_inventory.calendar.mine",
	},
	{
		"key": "maintenance",
		"label": _lt("Maintenance Due"),
		"color": "orange",
		"group": "Workspace",
		"on": False,
		"doctype": "Asset Maintenance Log",
		"rows": "onedesk.one_inventory.calendar.everyone",
	},
	# On an asset's own calendar: its maintenance, whoever does it.
	{
		"key": "asset-maintenance",
		"label": _lt("Maintenance"),
		"color": "orange",
		"group": "Workspace",
		"doctype": "Asset Maintenance Log",
		"rows": "onedesk.one_inventory.calendar.this_asset",
		"about": ["Asset"],
		"only_about": True,
	},
]


def mine(start, end) -> list[dict]:
	return _due(start, end, [["task_assignee_email", "=", frappe.session.user]])


def everyone(start, end) -> list[dict]:
	return _due(start, end, [])


def this_asset(start, end, record: tuple) -> list[dict]:
	return _due(start, end, [["asset_name", "=", record[1]]])


def _due(start, end, which: list) -> list[dict]:
	return [
		{
			"name": one.name,
			"title": f"{one.task_name or frappe._('Maintenance')} · {one.item_name or one.asset_name}",
			"start": one.due_date,
			"all_day": 1,
		}
		for one in frappe.get_list(
			"Asset Maintenance Log",
			filters=[
				*which,
				["maintenance_status", "in", ["Planned", "Overdue"]],
				["docstatus", "=", 0],
				*layers.within("due_date", start, end),
			],
			fields=["name", "task_name", "item_name", "asset_name", "due_date"],
			limit=layers.MOST,
		)
	]
