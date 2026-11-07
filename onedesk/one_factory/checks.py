"""OneFactory's part of the integration suite (one_demo/check.py runs it):
bills of materials, work orders and their steps on the Shop Floor, the plant
floor, and work sent to suppliers, as the workshop reads them."""

import datetime

import frappe
from frappe.utils import flt

from onedesk.one_demo.base import COMPANY, as_user, wh
from onedesk.one_demo.check import _Told, check
from onedesk.one_demo.people import OWNER


@check
def onefactory_the_shop_floor_runs_a_step_from_start_to_close():
	"""The Shop Floor: the board counts the open work orders as ERPNext's Shop
	Floor does, a work order shows its steps, and a step is started, paused,
	resumed and closed through ERPNext's own calls, each time saying what may
	be done next. OneAI reads what is running. Somebody outside the workshop
	sees none of it."""
	from erpnext.manufacturing.doctype.workstation.workstation import update_job_card
	from erpnext.manufacturing.page.shop_floor import shop_floor

	from onedesk.one_factory import ai, floor

	at = frappe.utils.now_datetime()
	with as_user("tariq@one.test"):
		board = floor.read()
		assert board["figures"]["open"] == board["total"] == len(board["work_orders"]), board["figures"]
		door = next(one for one in board["work_orders"] if one["production_item"] == "DR-SL24")
		said = floor.read(work_order=door["name"])
		assert said["work_order"]["project_name"], said["work_order"]
		assert [one["operation"] for one in said["steps"]] == ["Cutting", "Assembly", "Glazing"], said["steps"]
		cut, joint = said["steps"][0], said["steps"][1]
		assert cut["running"] and cut["may"]["pause"] and cut["may"]["record"] and not cut["may"]["start"], cut
		assert cut["people"] == ["Arun Kumar"] and cut["minutes"] == 0 and cut["since"], cut
		assert joint["may"]["start"] and not joint["may"]["pause"], joint["may"]
		assert said["employee"], "Tariq starts a step as himself"
		running = ai.on_the_floor()
		assert any(one["job_card"] == cut["name"] and one["state"] == "running" for one in running["steps"]), running
		assert running["figures"]["running"] >= 1, running["figures"]

		update_job_card(cut["name"], "pause_job", end_time=str(at))
		cut = floor.read(work_order=door["name"])["steps"][0]
		assert cut["paused"] and cut["may"]["resume"] and not cut["running"], cut
		update_job_card(cut["name"], "resume_job", start_time=str(at + datetime.timedelta(minutes=10)))

		closed_before = floor.figures()["done_today"]
		shop_floor.complete_and_submit(
			cut["name"], cut["for_quantity"], cut["for_quantity"], 0, 0, str(at + datetime.timedelta(minutes=50))
		)
		cut = floor.read(work_order=door["name"])["steps"][0]
		assert cut["docstatus"] == 1 and cut["done"] == cut["for_quantity"], cut
		assert not any(cut["may"][key] for key in ("start", "pause", "resume", "record")), cut["may"]
		assert floor.figures()["done_today"] == closed_before + 1
		update_job_card(joint["name"], "start_timer", start_time=str(at), employees=[{"employee": said["employee"]}])
		joint = floor.read(work_order=door["name"])["steps"][1]
		assert joint["running"] and joint["people"] == ["Tariq Haidar"], joint
		saw = floor.read(workstation="Saw Line")
		assert all(one["workstation"] == "Saw Line" for one in saw["steps"]), saw["steps"]
	with as_user("nadia@one.test"):
		assert ai.on_the_floor().get("error")
		try:
			floor.read()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the workshop read the Shop Floor")


@check
def onefactory_home_says_what_needs_the_workshop():
	"""OneFactory's Home: the figures are the Shop Floor's and the suppliers'
	own, a work order past the day it was wanted is late on Today and its
	maker and the project's manager are told the next morning, and somebody
	outside the workshop cannot open it."""
	from frappe.utils import add_days, today

	from onedesk.one_factory import control, floor, home, tell

	order = frappe.get_all("Work Order", filters={"docstatus": 1, "status": ["in", ["Not Started", "In Process"]], "project": ["is", "set"]}, fields=["name", "owner", "project"], limit=1)[0]
	frappe.db.set_value("Work Order", order.name, "expected_delivery_date", add_days(today(), -1), update_modified=False)
	with as_user("karim@one.test"):
		said = home.read()
		assert said["figures"]["open"] == floor.figures()["open"], said["figures"]
		assert order.name in {one["name"] for one in said["needs"]["late"]["rows"]}, said["needs"]["late"]
		assert said["figures"]["late"] == said["needs"]["late"]["count"]
		assert {"Work Order", "Shop Floor", "Subcontracting Order", "Work Order Summary"} <= {one["label"] for one in said["everything"]}
	with _Told() as told:
		tell.late()
	manager = frappe.db.get_value("Project", order.project, "one_manager")
	assert manager in told.to("Work Order Late"), told.said
	with as_user("nadia@one.test"):
		try:
			home.read()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the workshop opened OneFactory's Home")
		try:
			control.save_workshop()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the books emptied the workshop's settings")
	with as_user(OWNER):
		said = control.workshop()
		assert said["may"] and control.costed() and control.placed(), said
		again = control.save_workshop(**{key: said[key] for key in control.FIELDS})
		assert {key: again[key] for key in control.FIELDS} == {key: said[key] for key in control.FIELDS}


@check
def onefactory_sent_out_says_what_went_and_what_came_back():
	"""Work sent to suppliers, on frappe's own Subcontracting Order: the
	tower's profile with Gulf Powder Coating, all sent and nothing back yet,
	the villa's done with, and what the materials with the coater are
	worth. Taking the tower's back through ERPNext's receipt moves it to
	done. OneAI reads it. Tariq sees it, somebody outside the stores
	and the workshop does not."""
	from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
		make_subcontracting_receipt,
	)

	from onedesk.one_demo.making import COATER, COATING
	from onedesk.one_factory import ai, sent_out

	metres = COATING[0]
	assert not frappe.db.exists("Page", "sent_out")
	with as_user("karim@one.test"):
		tower = next(one for one in sent_out.orders() if one["supplier"] == COATER)
		assert tower["status"] == "Material Transferred" and not tower["late"], tower
		assert [(row["item"], row["qty"], row["back"]) for row in tower["makes"]] == [("ALU-6063-PC", metres, 0)], tower["makes"]
		assert [(row["item"], row["sent"]) for row in tower["materials"]] == [("ALU-6063", metres)], tower["materials"]
		assert tower["project_name"] == "Bayview Tower Curtain Wall"
		figures = sent_out.figures()
		assert figures["out"] >= 1 and figures["worth"] > 0, figures
		assert any(one["status"] == "Completed" for one in sent_out.orders(done=True))
		facts = ai.sent_out_now()
		assert any(one["order"] == tower["name"] for one in facts["out"]), facts

		receipt = frappe.get_doc(make_subcontracting_receipt(tower["name"]))
		receipt.insert()
		receipt.submit()
		assert tower["name"] not in {one["name"] for one in sent_out.orders()}
		assert tower["name"] in {one["name"] for one in sent_out.orders(done=True)}
	with as_user("tariq@one.test"):
		assert sent_out.figures()["out"] is not None
	with as_user("nadia@one.test"):
		assert not sent_out.orders() and sent_out.figures()["out"] is None
		assert ai.sent_out_now().get("error")


@check
def onefactory_the_plant_floor_shows_each_workstation():
	"""A plant floor, as ERPNext's own form shows it and OneAI reads it: the
	workshop's three workstations with the statuses ERPNext keeps (worked out
	from their job cards each time one is saved, or set by hand), the step running on the saw and who is on it, the steps waiting
	at each, and the stock kept on the floor. A status changed on a
	workstation shows at once, and the figures follow. OneAI reads it.
	Somebody outside the workshop sees none of it."""
	from onedesk.one_factory import ai, plant

	with as_user("tariq@one.test"):
		assert not frappe.db.exists("Page", "plant")
		frappe.client.set_value("Workstation", "Glazing Table", "status", "Maintenance")
		said = plant.now()
		assert said["plant"]["name"] == "Workshop", said["plant"]
		shown = {one["name"]: one for one in said["workstations"]}
		assert {name: one["status"] for name, one in shown.items()} == {
			name: frappe.db.get_value("Workstation", name, "status") for name in shown
		}, shown
		assert shown["Saw Line"]["status"] == "Production" and shown["Glazing Table"]["status"] == "Maintenance", shown
		saw = shown["Saw Line"]
		assert [step["operation"] for step in saw["running"]] == ["Cutting"], saw
		assert saw["running"][0]["people"] == ["Arun Kumar"], saw["running"]
		assert shown["Assembly Bench"]["waiting"] >= 1, shown["Assembly Bench"]
		assert said["figures"]["workstations"] == 3 and said["figures"]["stopped"] == 1 and said["figures"]["running"] == 1, said["figures"]
		making_before = said["figures"]["making"]
		assert said["stock"] and all(one["actual_qty"] > 0 for one in said["stock"]), said["stock"]
		assert [one["name"] for one in plant.now(status="Maintenance")["workstations"]] == ["Glazing Table"]

		frappe.client.set_value("Workstation", "Glazing Table", "status", "Production")
		after = plant.now()
		assert after["figures"]["making"] == making_before + 1 and after["figures"]["stopped"] == 0, after["figures"]
		facts = ai.plant_floor_now()
		assert {one["workstation"]: one["status"] for one in facts["workstations"]}["Glazing Table"] == "Production"
		assert ai.plant_floor_now("Nowhere").get("error")
	with as_user("nadia@one.test"):
		assert ai.plant_floor_now().get("error")
		try:
			plant.now()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the workshop read the Plant Floor")


@check
def onefactory_making_from_bill_to_finished_goods():
	"""Making, as Tariq, Samir, Rania and Huda meet it. Tariq keeps the bills of
	materials and makes the work orders, the villa's and the tower's among
	them. Each step is a job card worked by whoever works its workstation, the
	materials used count in the project's cost, and the villa's manager is
	told when its order is made. Rania asked the workshop for the villa's last
	doors. The villa's profile went out to be powder coated and came back."""
	from erpnext.stock.utils import get_stock_balance

	from onedesk.one_demo import making
	from onedesk.one_factory import control, heads, tell

	villa = frappe.db.get_value("Project", {"project_name": making.VILLA})
	tower = frappe.db.get_value("Project", {"project_name": making.TOWER})
	window = frappe.get_doc("BOM", {"item": "WIN-CS12", "is_default": 1, "docstatus": 1})
	assert window.owner == making.SUPERVISOR and [one.operation for one in window.operations] == ["Cutting", "Assembly", "Glazing"]
	assert heads.bom_steps(window) == "Cutting · Assembly · Glazing" and flt(window.operating_cost) > 0
	assert heads.bom_orders(window)["value"] == "3"
	orders = frappe.get_all("Work Order", filters={"docstatus": 1}, fields=["name", "owner", "project", "status", "production_item", "produced_qty", "qty"])
	assert {one.owner for one in orders} == {making.SUPERVISOR}, "Tariq makes the work orders"
	assert {one.project for one in orders} == {None, villa, tower}

	done = frappe.get_doc("Work Order", {"project": villa, "production_item": "DR-SL24", "status": "Completed"})
	cards = frappe.get_all("Job Card", filters={"work_order": done.name, "docstatus": 1}, fields=["name", "operation", "total_completed_qty", "total_time_in_mins", "process_loss_qty"])
	assert {one.operation for one in cards} == {"Cutting", "Assembly", "Glazing"} and all(one.total_completed_qty == done.qty for one in cards)
	glazed = frappe.get_doc("Job Card", next(one.name for one in cards if one.operation == "Glazing"))
	assert heads.card_by(glazed) == "Joseph Mathew" and heads.card_done(glazed)["meter"] == {"value": done.qty, "of": done.qty}
	made = frappe.get_doc("Stock Entry", {"work_order": done.name, "purpose": "Manufacture", "docstatus": 1})
	assert made.project == villa and flt(made.total_additional_costs) > 0, "the workshop's time is in the doors' value"
	assert all(row.project == villa for row in made.items)

	going = frappe.get_doc("Work Order", {"project": tower, "docstatus": 1})
	steps = {step["label"]: step for step in heads.work_progress(going)["steps"]}
	assert going.status == "In Process" and steps["Manufactured"]["note"] == "12 of 30 Nos"
	assert steps["Material Transferred"]["note"] == "All on the floor" and steps["Material Transferred"]["state"] == "done"
	steps = {one.operation: one for one in frappe.get_all("Job Card", filters={"work_order": going.name, "docstatus": 1}, fields=["operation", "total_completed_qty", "process_loss_qty"])}
	assert steps["Cutting"].total_completed_qty == 30 and steps["Assembly"].total_completed_qty == 12 and not steps["Assembly"].process_loss_qty

	used = frappe.db.sql(
		"""select sum(row.amount) from `tabStock Entry Detail` row join `tabStock Entry` entry on entry.name = row.parent
		where entry.purpose = 'Manufacture' and entry.docstatus = 1 and row.project = %s and ifnull(row.t_warehouse, '') = ''""",
		villa,
	)[0][0]
	project = frappe.get_doc("Project", villa)
	kept = flt(project.total_consumed_material_cost)
	project.set_consumed_material_cost()
	assert flt(used) > 0 and flt(kept, 2) == flt(project.total_consumed_material_cost, 2) and kept >= flt(used)

	asked = frappe.get_doc("Work Order", {"material_request": ["is", "set"], "docstatus": 1})
	assert frappe.db.get_value("Material Request", asked.material_request, "owner") == "rania@one.test"
	assert heads.work_for(asked)["value"] == "Rania Sabbagh" and asked.project == villa and asked.status == "Not Started"

	manager = frappe.db.get_value("Project", villa, "one_manager")
	with as_user(making.SUPERVISOR), _Told() as told:
		tell.work_done(made)
	assert told.to("Work Order Done") == {manager, making.SUPERVISOR}
	assert frappe.db.exists("Notification Log", {"document_name": done.name, "for_user": manager})
	assert not frappe.db.exists("Notification Log", {"document_name": done.name, "for_user": making.SUPERVISOR})

	printed = frappe.get_print("Work Order", done.name, "One Work Order")
	assert making.VILLA in printed and "Cutting" in printed and "Aluminium Profile 6063" in printed
	for_stock = next(one.name for one in orders if not one.project)
	assert "Mansour &amp; Sons" in printed or "Mansour & Sons" in printed, "made for the villa's customer"
	assert "Made For" not in frappe.get_print("Work Order", for_stock, "One Work Order"), "goods for stock are made for nobody"

	sent = frappe.get_doc("Subcontracting Order", {"supplier": making.COATER, "docstatus": 1, "project": villa})
	assert sent.project == villa and sent.status == "Completed" and {step["label"]: step["state"] for step in heads.sub_progress(sent)["steps"]} == {"Ordered": "done", "Material Transferred": "done", "Received": "done"}
	back = frappe.get_doc("Subcontracting Receipt", frappe.db.get_value("Subcontracting Receipt Item", {"subcontracting_order": sent.name, "docstatus": 1}, "parent"))
	assert heads.sub_order(back)["value"] == sent.name
	assert frappe.db.get_value("Purchase Order", sent.purchase_order, "status") == "To Bill"
	assert flt(get_stock_balance("ALU-6063-PC", wh("Stores"))) == 300
	assert flt(get_stock_balance("ALU-6063", wh(making.COATER))) == making.COATING[0]

	assert control.costed() and control.placed(), "the workshop's account and warehouses are set"

	with as_user(making.SUPERVISOR):
		imported = frappe.get_doc(
			{"doctype": "Work Order", "production_item": "WIN-CS12", "bom_no": window.name, "qty": 2, "company": COMPANY}
		).insert()
		assert [one.operation for one in imported.operations] == ["Cutting", "Assembly", "Glazing"]
		assert imported.wip_warehouse == wh("Work In Progress") and imported.fg_warehouse == wh("Finished Goods")
		imported.delete()

	from onedesk.one_ai import proposals, tools
	from onedesk.one_factory import ai

	open_work = {"docstatus": 1, "status": ["in", ["Not Started", "In Process"]]}
	with as_user(making.SUPERVISOR):
		hand = tools.list_records(
			"Work Order",
			{**open_work, "project": frappe.db.get_value("Project", {"project_name": making.TOWER})},
			fields=["item_name", "qty", "produced_qty", "status", "project", "expected_delivery_date"],
			order_by="expected_delivery_date asc",
		)
		assert [one["name"] for one in hand] == [going.name] and hand[0]["produced_qty"] == 12, hand
		facts = ai.work_order_facts(going.name)
		assert {one["step"]: one["done"] for one in facts["steps"]} == {"Cutting": 30, "Assembly": 12, "Glazing": 12}
		assert facts["cost_so_far"]["workshop_time"] > 0 and facts["materials"]
		card = ai.plan_work_order("Casement Window 1200", 10, project=making.VILLA, why="The villa's last windows")
		drafted = proposals.apply(card["proposal"])
	order_ = frappe.get_doc("Work Order", drafted["record"])
	assert order_.docstatus == 0 and order_.project == villa and len(order_.operations) == 3
	order_.delete()
	with as_user("nadia@one.test"):
		assert ai.plan_work_order("WIN-CS12", 1).get("error")
		try:
			tools.list_records("Work Order", open_work)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the workshop listed its work orders")

	for person in (making.SUPERVISOR, "rania@one.test"):
		with as_user(person):
			assert frappe.has_permission("Work Order", "create") and frappe.has_permission("Job Card", "submit")
	with as_user("karim@one.test"):
		assert frappe.has_permission("Subcontracting BOM", "write")
	with as_user(making.SUPERVISOR):
		assert frappe.has_permission("Manufacturing Settings", "write")
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Work Order", "read") and not frappe.has_permission("BOM", "read")


@check
def onefactory_what_making_costs_is_an_ability():
	"""See What Making Costs: Tariq, who runs the workshop, reads a bill's
	cost per unit and its Costing tab; Karim, who works in it, sees neither."""
	from onedesk.one_factory import costs, heads

	window = frappe.get_doc("BOM", {"item": "WIN-CS12", "is_default": 1, "docstatus": 1})
	with as_user("tariq@one.test"):
		assert costs.seen() and heads.bom_cost(window)
		window.onload_values = None
		costs.onload(window)
		assert not window.get_onload().get("one_costs_hidden")
	with as_user("karim@one.test"):
		assert not costs.seen() and heads.bom_cost(window) is None
		window.set_onload("one_costs_hidden", 0)
		costs.onload(window)
		assert window.get_onload().get("one_costs_hidden") == 1
