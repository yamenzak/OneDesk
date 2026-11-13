"""OneInventory on the calendar: maintenance that is due, from ERPNext's Asset
Maintenance Log, which opens the log where it is recorded done (see
one_inventory/maintenance.py); and the goods expected from suppliers and the
deliveries due to customers, the reader's company's, each opening its
order."""

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
	{
		"key": "goods-expected",
		"label": _lt("Goods Expected"),
		"color": "blue",
		"group": "Workspace",
		"on": False,
		"doctype": "Purchase Order",
		"rows": "onedesk.one_inventory.calendar.expected",
	},
	{
		"key": "deliveries-due",
		"label": _lt("Deliveries Due"),
		"color": "green",
		"group": "Workspace",
		"on": False,
		"doctype": "Sales Order",
		"rows": "onedesk.one_inventory.calendar.delivering",
	},
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
			"title": f"{one.task_name or frappe._('Maintenance')} · {one.one_asset_title or one.item_name or one.asset_name}",
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
			fields=["name", "task_name", "one_asset_title", "item_name", "asset_name", "due_date"],
			limit=layers.MOST,
		)
	]


def expected(start, end) -> list[dict]:
	"""Purchase orders still to arrive, on the day they are wanted."""
	from onedesk.one.company import reader_company

	return [
		{"name": one.name, "title": f"{one.supplier_name} · {one.name}", "start": one.schedule_date, "all_day": 1}
		for one in frappe.get_list(
			"Purchase Order",
			filters=[
				["docstatus", "=", 1],
				["status", "in", ["To Receive and Bill", "To Receive"]],
				["company", "=", reader_company()],
				*layers.within("schedule_date", start, end),
			],
			fields=["name", "supplier_name", "schedule_date"],
			limit=layers.MOST,
		)
	]


def delivering(start, end) -> list[dict]:
	"""Sales orders still to go out, on the day they are promised."""
	from onedesk.one.company import reader_company

	return [
		{"name": one.name, "title": f"{one.customer_name} · {one.name}", "start": one.delivery_date, "all_day": 1}
		for one in frappe.get_list(
			"Sales Order",
			filters=[
				["docstatus", "=", 1],
				["status", "in", ["To Deliver and Bill", "To Deliver"]],
				["company", "=", reader_company()],
				*layers.within("delivery_date", start, end),
			],
			fields=["name", "customer_name", "delivery_date"],
			limit=layers.MOST,
		)
	]
