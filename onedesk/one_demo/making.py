"""The workshop. Tariq keeps a bill of materials for each product, cuts,
assembles and glazes on three workstations, and makes work orders for stock,
for the villa and for the tower. Profile for the villa is sent out to be
powder coated and taken back. The demo README's making row tells it in full."""

import frappe
from frappe.utils import add_days, add_to_date, flt, get_datetime, getdate

from onedesk.one_demo.base import COMPANY, ago, ahead, as_user, dated, make, on, once, save, today, wh

SUPERVISOR = "tariq@one.test"
BUYER = "karim@one.test"
VILLA = "Mansour Villa Windows and Doors"
TOWER = "Bayview Tower Curtain Wall"
COATER = "Gulf Powder Coating"

#: workstation, its step, cost per hour, who works it
WORKSTATIONS = (
	("Saw Line", "Cutting", 60, "Arun Kumar"),
	("Assembly Bench", "Assembly", 45, "Ravi Menon"),
	("Glazing Table", "Glazing", 50, "Joseph Mathew"),
)

#: The workshop's floor, kept by Tariq, and how each workstation stands now:
#: the saw is cutting, the bench is idle, and the glazing table is down for
#: a new suction lifter.
FLOOR = "Workshop"
STANDING = {"Saw Line": "Production", "Assembly Bench": "Idle", "Glazing Table": "Maintenance"}

#: product, [(material, qty for one)], [(step, minutes for one)]
BOMS = (
	(
		"WIN-CS12",
		(("ALU-6063", 9), ("GLS-DGU", 1.3), ("HW-HINGE", 2), ("HW-HANDLE", 1), ("SEAL-EPDM", 6), ("SIL-CLR", 1)),
		(("Cutting", 12), ("Assembly", 25), ("Glazing", 15)),
	),
	(
		"DR-SL24",
		(("ALU-6063", 16), ("GLS-DGU", 4.5), ("HW-LOCK", 1), ("HW-HANDLE", 2), ("SEAL-EPDM", 12), ("SIL-CLR", 1)),
		(("Cutting", 20), ("Assembly", 45), ("Glazing", 30)),
	),
	# Balustrade glass comes cut to size, and is fixed on site.
	("BAL-GL", (("GLS-TMP10", 1.1), ("FIX-ANCH", 4), ("SIL-CLR", 1)), ()),
)

#: product, qty, started, made (all, part or none), project
ORDERS = (
	("WIN-CS12", 40, on(4, 8), 40, None),
	("DR-SL24", 14, on(4, 20), 14, None),
	("BAL-GL", 90, on(6, 12), 90, None),
	("WIN-CS12", 60, on(7, 6), 60, VILLA),
	("DR-SL24", 10, on(8, 24), 10, VILLA),
	("WIN-CS12", 30, add_days(today(), -9), 12, TOWER),
	("BAL-GL", 40, add_days(today(), -2), 0, VILLA),
)

#: The villa's last doors, asked for by Rania and not started yet.
ASKED = ("DR-SL24", 8, ahead(4))

#: Coating: metres sent, the price a metre, sent and back.
COATED = (300, 4.5, ago(20), ago(12))


def run(password=None):
	from onedesk.one_inventory import ready

	projects = {name: frappe.db.get_value("Project", {"project_name": name}) for name in (VILLA, TOWER)}
	with as_user(SUPERVISOR):
		_workshop()
		for product, materials, steps in BOMS:
			if not frappe.db.exists("BOM", {"item": product, "is_default": 1}):
				_bom(product, materials, steps)
		if not frappe.db.exists("BOM", {"item": "ALU-6063-PC", "is_default": 1}):
			_bom("ALU-6063-PC", (("ALU-6063", 1),), ())
	# Making with workstation time needs the company's account for it, and new
	# work orders their warehouses: the Inventory Check's two fixes.
	with as_user(BUYER):
		ready.fix("workshop")
		ready.fix("floor")
	if not frappe.db.exists("Work Order", {"docstatus": 1}):
		with as_user(SUPERVISOR):
			for product, qty, started, made, project in ORDERS:
				_work_order(product, qty, started, made, projects.get(project))
		_asked(projects[VILLA])
	if not frappe.db.exists("Subcontracting Order", {"docstatus": 1}):
		_coated(projects[VILLA])
	_on_the_saw()


def _workshop():
	if not frappe.db.exists("Workstation Operating Component", "Wages"):
		with as_user(BUYER):
			make({"doctype": "Workstation Operating Component", "component_name": "Wages"})
	for workstation, step, rate, _person in WORKSTATIONS:
		once(
			"Workstation",
			{"workstation_name": workstation},
			{"workstation_name": workstation, "workstation_costs": [{"operating_component": "Wages", "operating_cost": rate}]},
		)
		once("Operation", {"name": step}, {"name": step, "workstation": workstation})
	# A floor is the workshop's setup, kept by its manager.
	with as_user(BUYER):
		once("Plant Floor", {"name": FLOOR}, {"floor_name": FLOOR, "company": COMPANY, "warehouse": wh("Work In Progress")})
	for workstation, status in STANDING.items():
		if not frappe.db.get_value("Workstation", workstation, "plant_floor"):
			doc = frappe.get_doc("Workstation", workstation)
			doc.update({"plant_floor": FLOOR, "status": status})
			doc.save()


def _bom(product, materials, steps):
	where = {step: workstation for workstation, step, _rate, _person in WORKSTATIONS}
	make(
		{
			"doctype": "BOM",
			"item": product,
			"company": COMPANY,
			"quantity": 1,
			"is_default": 1,
			"is_active": 1,
			"rm_cost_as_per": "Valuation Rate",
			"with_operations": int(bool(steps)),
			"items": [{"item_code": code, "qty": qty} for code, qty in materials],
			"operations": [
				{"operation": step, "workstation": where[step], "time_in_mins": minutes} for step, minutes in steps
			],
		},
		submit=True,
	)


def _work_order(product, qty, started, made, project, request=None):
	from erpnext.manufacturing.doctype.work_order.mapper import make_stock_entry

	order = frappe.new_doc("Work Order")
	order.update(
		{
			"production_item": product,
			"bom_no": frappe.db.get_value("BOM", {"item": product, "is_default": 1}),
			"qty": qty,
			"company": COMPANY,
			"project": project,
			"wip_warehouse": wh("Work In Progress"),
			"fg_warehouse": wh("Finished Goods"),
			"source_warehouse": wh("Stores"),
			"planned_start_date": f"{started} 08:00:00",
			"expected_delivery_date": add_days(started, 10),
		}
	)
	if request:
		order.material_request, order.material_request_item = request
	# The form fetches the bill's materials and steps when the bill is chosen.
	order.get_items_and_operations_from_bom()
	order = save(order, submit=True)
	if started >= today():
		return order
	transfer = frappe.get_doc(make_stock_entry(order.name, "Material Transfer for Manufacture", qty))
	dated(transfer, started)
	save(transfer, submit=True)
	# Everything is cut at once, then assembled and glazed as far as it was made.
	done = _worked(order, {"Cutting": qty if made else 0}, made, started)
	if made:
		finish = frappe.get_doc(make_stock_entry(order.name, "Manufacture", made))
		dated(finish, min(done, getdate(today())))
		save(finish, submit=True)
	return order


def _worked(order, ahead_of, made, started):
	"""Each step's job card, done in order by whoever works its workstation,
	eight hours a day at most."""
	people = {step: person for _workstation, step, _rate, person in WORKSTATIONS}
	day = last = get_datetime(f"{started} 08:00:00")
	for row in sorted(order.operations, key=lambda one: one.idx):
		done = ahead_of.get(row.operation) or made
		if not done:
			continue
		card = frappe.get_doc("Job Card", {"work_order": order.name, "operation_id": row.name, "docstatus": 0})
		employee = frappe.db.get_value("Employee", {"employee_name": people[row.operation]})
		minutes = round(flt(row.time_in_mins) / flt(order.qty) * done)
		left, qty_left, start = minutes, done, day
		while left > 0:
			spell = min(left, 480)
			qty = qty_left if spell == left else round(done * spell / minutes)
			card.append(
				"time_logs",
				{"employee": employee, "from_time": start, "to_time": add_to_date(start, minutes=spell), "completed_qty": qty},
			)
			last = start
			left -= spell
			qty_left -= qty
			start = add_to_date(start, days=1)
		day = start
		dated(card, last.date())
		# What is not done yet is still to do, not lost.
		card.pending_qty = flt(card.for_quantity) - done
		card.save()
		card.submit()
	return last.date()


def _on_the_saw():
	"""Arun has been cutting the villa's last doors since the morning, so the
	floor has a step running."""
	from erpnext.manufacturing.doctype.workstation.workstation import update_job_card

	if frappe.db.exists("Job Card Time Log", {"from_time": ["is", "set"], "to_time": ["is", "not set"]}):
		return
	product, _qty, _wanted = ASKED
	order = frappe.db.get_value("Work Order", {"production_item": product, "docstatus": 1, "status": "Not Started"})
	card = order and frappe.db.get_value("Job Card", {"work_order": order, "operation": "Cutting", "docstatus": 0})
	if not card:
		return
	arun = frappe.db.get_value("Employee", {"employee_name": WORKSTATIONS[0][3]})
	with as_user(SUPERVISOR):
		update_job_card(
			card, "start_timer", start_time=str(add_to_date(None, minutes=-95)), employees=[{"employee": arun}]
		)


def _asked(project):
	"""Rania asks the workshop for the villa's last eight doors, and Tariq
	makes the work order from her request."""
	product, qty, wanted = ASKED
	with as_user("rania@one.test"):
		request = frappe.new_doc("Material Request")
		request.material_request_type = "Manufacture"
		request.company = COMPANY
		request.project = project
		dated(request, ago(3), "transaction_date")
		request.schedule_date = wanted
		request.append(
			"items",
			{"item_code": product, "qty": qty, "schedule_date": wanted, "warehouse": wh("Finished Goods"), "project": project},
		)
		request = save(request, submit=True)
	with as_user(SUPERVISOR):
		_work_order(product, qty, wanted, 0, project, (request.name, request.items[0].name))


def _coated(project):
	"""Karim sends the villa's profile to Gulf Powder Coating to be coated in
	the villa's colour, and takes it back into the stores."""
	from erpnext.buying.doctype.purchase_order.mapper import make_subcontracting_order
	from erpnext.controllers.subcontracting_controller import make_rm_stock_entry
	from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
		make_subcontracting_receipt,
	)
	from erpnext.subcontracting.doctype.subcontracting_receipt.mapper import make_purchase_receipt

	metres, rate, sent, back = COATED
	with as_user(BUYER):
		place = once(
			"Warehouse",
			{"warehouse_name": COATER, "company": COMPANY},
			{"warehouse_name": COATER, "company": COMPANY, "parent_warehouse": wh("All Warehouses")},
		).name
		once(
			"Subcontracting BOM",
			{"finished_good": "ALU-6063-PC", "is_active": 1},
			{
				"finished_good": "ALU-6063-PC",
				"finished_good_qty": 1,
				"finished_good_bom": frappe.db.get_value("BOM", {"item": "ALU-6063-PC", "is_default": 1}),
				"service_item": "SVC-PCOAT",
				"service_item_qty": 1,
				"service_item_uom": "Meter",
				"is_active": 1,
			},
		)
		order = frappe.new_doc("Purchase Order")
		order.update(
			{
				"supplier": COATER,
				"company": COMPANY,
				"is_subcontracted": 1,
				"supplier_warehouse": place,
				"project": project,
				"schedule_date": back,
			}
		)
		dated(order, sent, "transaction_date")
		order.append(
			"items",
			{
				"item_code": "SVC-PCOAT",
				"qty": metres,
				"rate": rate,
				"fg_item": "ALU-6063-PC",
				"fg_item_qty": metres,
				"warehouse": wh("Stores"),
				"schedule_date": back,
				"project": project,
			},
		)
		order = save(order, submit=True)
		sub = frappe.get_doc(make_subcontracting_order(order.name))
		dated(sub, sent, "transaction_date")
		sub = save(sub, submit=True)
		materials = frappe.get_doc(make_rm_stock_entry(sub.name))
		dated(materials, sent)
		save(materials, submit=True)
		receipt = frappe.get_doc(make_subcontracting_receipt(sub.name))
		dated(receipt, back)
		receipt.supplier_delivery_note = "GPC-DN-0417"
		receipt = save(receipt, submit=True)
		# The coater's order is received through a purchase receipt as well,
		# which their bill is then made against.
		taken = frappe.get_doc(make_purchase_receipt(receipt.name))
		dated(taken, back)
		save(taken, submit=True)
