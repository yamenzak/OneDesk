"""What Sahara owns: two pickups, the CNC centre and the office laptops,
each with who has it, what it is worth after depreciation, and when it is
next due a service."""

import frappe
from frappe.utils import get_last_day

from onedesk.one_demo.base import COMPANY, as_user, make, on, today

STORES = "karim@one.test"

#: name, item, location, bought (years back, month, day), cost, custodian
ASSETS = (
	("Pickup Truck 1", "VEH-PICKUP", "Main Workshop", (2, 3, 10), 138000, "Sanjay"),
	("Pickup Truck 2", "VEH-PICKUP", "Main Workshop", (1, 2, 2), 149000, "Yousef"),
	("CNC Profile Machining Centre", "MCH-CNC", "Main Workshop", (1, 11, 20), 520000, "Tariq"),
	("Laptop Nadia", "IT-LAPTOP", "Head Office", (1, 6, 1), 6500, "Nadia"),
	("Laptop Huda", "IT-LAPTOP", "Head Office", (1, 1, 15), 6200, "Huda"),
)


def run(password=None):
	for location in ("Head Office", "Main Workshop"):
		if not frappe.db.exists("Location", location):
			make({"doctype": "Location", "location_name": location})
	from onedesk.one_demo.setup import last_years

	last_years()
	with as_user(STORES):
		for name, item, location, (back, month, day), cost, custodian in ASSETS:
			if frappe.db.exists("Asset", {"asset_name": name}):
				continue
			bought = f"{today().year - back}-{month:02d}-{day:02d}"
			# Booked by the books every month end before this year began.
			months = back * 12 - month + 1
			years = {"VEH-PICKUP": 5, "MCH-CNC": 10, "IT-LAPTOP": 3}[item]
			make(
				{
					"doctype": "Asset",
					"asset_name": name,
					"item_code": item,
					"company": COMPANY,
					"location": location,
					"custodian": frappe.db.get_value("Employee", {"first_name": custodian}),
					"asset_type": "Existing Asset",
					"purchase_date": bought,
					"available_for_use_date": bought,
					"net_purchase_amount": cost,
					"purchase_amount": cost,
					"calculate_depreciation": 1,
					"opening_accumulated_depreciation": round(cost / (years * 12) * months, 2),
					"opening_number_of_booked_depreciations": months,
					"maintenance_required": int(item != "IT-LAPTOP"),
					"finance_books": [
						{
							"depreciation_method": "Straight Line",
							"total_number_of_depreciations": years * 12,
							"frequency_of_depreciation": 1,
							"depreciation_start_date": get_last_day(on(1, 1)),
						}
					],
				},
				submit=True,
			)
		_maintenance()
	# This year's month ends so far, booked as ERPNext's daily job books them.
	from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries

	post_depreciation_entries()


def _maintenance():
	team = "Workshop Maintenance"
	if not frappe.db.exists("Asset Maintenance Team", team):
		make(
			{
				"doctype": "Asset Maintenance Team",
				"maintenance_team_name": team,
				"company": COMPANY,
				"maintenance_manager": "tariq@one.test",
				"maintenance_team_members": [
					{"team_member": "tariq@one.test", "maintenance_role": "Maintenance Manager"},
					{"team_member": "yousef@one.test", "maintenance_role": "Maintenance User"},
				],
			}
		)
	for asset in frappe.get_all("Asset", filters={"maintenance_required": 1, "docstatus": 1}, fields=["name", "asset_name", "item_code"]):
		if frappe.db.exists("Asset Maintenance", asset.name):
			continue
		truck = asset.item_code == "VEH-PICKUP"
		make(
			{
				"doctype": "Asset Maintenance",
				"asset_name": asset.name,
				"company": COMPANY,
				"maintenance_team": team,
				"asset_maintenance_tasks": [
					{
						"maintenance_task": "Service" if truck else "Spindle and coolant check",
						"maintenance_type": "Preventive Maintenance",
						"maintenance_status": "Planned",
						"start_date": on(1, 15) if truck else on(2, 1),
						"periodicity": "Quarterly" if truck else "Monthly",
						"assign_to": "yousef@one.test" if truck else "tariq@one.test",
					}
				],
			}
		)
