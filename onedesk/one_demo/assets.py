"""What Sahara owns: two pickups, the CNC centre and the office laptops,
each with who has it, what it is worth after depreciation, and when it is
next due a service. Services are kept up, one truck's late. Mariam's laptop
is bought on a receipt and handed to her, a truck's gearbox is mended on the
garage's bill, Huda's laptop is waiting for a new screen, the CNC centre is
written down after a crash, and Sanjay's leaving asks for his truck back.
The demo README's assets row tells it in full."""

import frappe
from frappe.utils import add_days, get_last_day, getdate

from onedesk.one_demo.base import COMPANY, account, ago, as_user, dated, make, on, once, save, today

STORES = "karim@one.test"
BOOKS = "huda@one.test"
PEOPLE = "mariam@one.test"
DRIVER = "Sanjay"
GARAGE = "Emirates Fleet Motors"

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
	from erpnext.assets.doctype.asset.depreciation import post_depreciation_entries

	post_depreciation_entries()
	for name, late in SERVICED:
		_serviced(name, late)
	if not frappe.db.exists("Purchase Order Item", {"item_code": "IT-LAPTOP", "docstatus": 1}):
		_laptop()
	if not frappe.db.exists("Asset Repair", {"docstatus": ["<", 2]}):
		_mended()
	if not frappe.db.exists("Asset Value Adjustment", {"docstatus": 1}):
		_written_down()
	if not frappe.db.exists("Employee Separation", {"employee": _employee(DRIVER)}):
		_driver_leaving()
	_shifts()


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


SERVICED = (("Pickup Truck 1", False), ("Pickup Truck 2", True), ("CNC Profile Machining Centre", False))


def _serviced(name, late):
	"""Each service done the day after it fell due, by whoever does it, up to
	the one still to come. A late truck's last one is left undone."""
	from onedesk.one_inventory.maintenance import next_due

	asset = frappe.db.get_value("Asset", {"asset_name": name})
	day = getdate(today())
	while True:
		log = frappe.db.get_value(
			"Asset Maintenance Log",
			{"asset_maintenance": asset, "docstatus": 0, "maintenance_status": ["in", ["Planned", "Overdue"]]},
			["name", "due_date", "periodicity", "task_assignee_email"],
			as_dict=True,
		)
		if not log or not log.due_date or getdate(log.due_date) > day:
			return
		if late and getdate(next_due(log.periodicity, log.due_date)) > day:
			return
		with as_user(log.task_assignee_email):
			done = frappe.get_doc("Asset Maintenance Log", log.name)
			done.maintenance_status = "Completed"
			done.completion_date = min(add_days(log.due_date, 1), day)
			done.actions_performed = "Checked and serviced as the schedule says."
			save(done, submit=True)


def _laptop():
	"""Mariam's laptop, bought from Gulf Office Supplies on a receipt that
	registers it, and handed to her."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	from onedesk.one_inventory import custody

	with as_user(STORES):
		order = frappe.new_doc("Purchase Order")
		order.update({"supplier": "Gulf Office Supplies", "company": COMPANY, "schedule_date": ago(15)})
		dated(order, ago(20), "transaction_date")
		order.append("items", {"item_code": "IT-LAPTOP", "qty": 1, "rate": 5900, "schedule_date": ago(15)})
		order = save(order, submit=True)
		receipt = frappe.get_doc(make_purchase_receipt(order.name))
		dated(receipt, ago(14))
		for row in receipt.items:
			row.asset_location = "Head Office"
		receipt.supplier_delivery_note = "GOS-DN-1180"
		receipt = save(receipt, submit=True)
		asset = frappe.get_doc("Asset", {"purchase_receipt": receipt.name})
		asset.asset_name = "Laptop Mariam"
		asset.save()
		custody.give(asset.name, frappe.db.get_value("Employee", {"user_id": "mariam@one.test"}))


def _mended():
	"""Pickup Truck 1's gearbox slipped, and Emirates Fleet Motors mended it
	on a bill booked to repairs. Huda's laptop screen cracked two days ago
	and waits for its repair."""
	repairs = account("Repairs and Maintenance")
	if not frappe.db.exists("Account", repairs):
		with as_user(BOOKS):
			make(
				{
					"doctype": "Account",
					"account_name": "Repairs and Maintenance",
					"parent_account": frappe.db.get_value(
						"Account", {"company": COMPANY, "account_name": "Indirect Expenses", "is_group": 1}
					),
					"company": COMPANY,
					"account_type": "Expense Account",
				}
			)
	with as_user(BOOKS):
		bill = frappe.new_doc("Purchase Invoice")
		bill.update({"supplier": GARAGE, "company": COMPANY, "bill_no": "EFM-INV-2231", "bill_date": ago(34)})
		dated(bill, ago(34))
		bill.append("items", {"item_code": "SVC-VREP", "qty": 1, "rate": 3850, "expense_account": repairs})
		bill = save(bill, submit=True)
	with as_user(STORES):
		truck = frappe.db.get_value("Asset", {"asset_name": "Pickup Truck 1"})
		make(
			{
				"doctype": "Asset Repair",
				"asset": truck,
				"company": COMPANY,
				"failure_date": f"{ago(40)} 08:30:00",
				"completion_date": f"{ago(35)} 17:00:00",
				"repair_status": "Completed",
				"description": "The gearbox slips in third gear.",
				"actions_performed": "Emirates Fleet Motors replaced the clutch pack.",
				"invoices": [{"purchase_invoice": bill.name, "expense_account": repairs, "repair_cost": 3850}],
			},
			submit=True,
		)
		make(
			{
				"doctype": "Asset Repair",
				"asset": frappe.db.get_value("Asset", {"asset_name": "Laptop Huda"}),
				"company": COMPANY,
				"failure_date": f"{ago(2)} 10:00:00",
				"repair_status": "Pending",
				"description": "The screen is cracked and stays dark.",
			}
		)


def _written_down():
	"""The CNC centre's spindle crashed, and Huda writes it down by a tenth,
	today: ERPNext takes no adjustment dated before its last depreciation,
	which is posted to the end of last month."""
	with as_user(BOOKS):
		cut = frappe.new_doc("Asset Value Adjustment")
		cut.update(
			{
				"asset": frappe.db.get_value("Asset", {"asset_name": "CNC Profile Machining Centre"}),
				"company": COMPANY,
				"date": today(),
				"difference_account": account("Impairment"),
			}
		)
		cut.set_current_asset_value()
		cut.new_asset_value = round(cut.current_asset_value * 0.9, -3)
		save(cut, submit=True)


def _employee(first_name):
	return frappe.db.get_value("Employee", {"first_name": first_name})


def _driver_leaving():
	"""Sanjay, who drives Pickup Truck 1, resigns and works to the end of next
	month. Mariam starts his leaving checklist: his exit interview with her,
	his final pay with the books, and, because he holds the truck, a step for
	the stores to take it back (one_inventory/custody.py `leaving`)."""
	from frappe.utils import add_months

	employee = _employee(DRIVER)
	with as_user(PEOPLE):
		worker = frappe.get_doc("Employee", employee)
		worker.resignation_letter_date = ago(3)
		worker.relieving_date = get_last_day(add_months(today(), 1))
		worker.reason_for_leaving = "Driving for a family business"
		worker.save()
		make(
			{
				"doctype": "Employee Separation",
				"employee": employee,
				"company": COMPANY,
				"boarding_begins_on": today(),
				"activities": [
					{"activity_name": "Exit interview", "user": PEOPLE, "begin_on": 0, "duration": 1},
					{"activity_name": "Final pay and end of service", "user": BOOKS, "begin_on": 20, "duration": 5},
				],
			},
			submit=True,
		)


def _shifts():
	"""How much harder a machine wears on a longer day, for depreciation by
	shift."""
	once("Asset Shift Factor", {"shift_name": "Single Shift"}, {"shift_name": "Single Shift", "shift_factor": 1, "default": 1})
	once("Asset Shift Factor", {"shift_name": "Double Shift"}, {"shift_name": "Double Shift", "shift_factor": 1.5})
