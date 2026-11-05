"""OneInventory's part of the integration suite (one_demo/check.py runs it):
items, stock and warehouses, buying and receiving, delivering,
batches, equipment and its upkeep, as their people read them, and the one
ability."""

import frappe
from frappe.utils import add_days, flt, getdate, today

from onedesk.one_demo.base import COMPANY, as_user, wh
from onedesk.one_demo.check import CENTS, VILLA, _Told, check
from onedesk.one_demo.people import OWNER


def _before_reordering():
	"""The stores as they were before the nightly reorder ran: the demo's
	silicone is low in Stores, and once a night has passed ERPNext's
	reordering has asked for more (Material Request Raised), which takes it
	off Running Low by ERPNext's own rule. Those requests are cancelled here,
	inside the check's rollback, so the screens can be read with something
	low whatever day it is."""
	raised = frappe.get_all(
		"Material Request",
		filters={"owner": "Administrator", "docstatus": 1, "status": "Pending", "material_request_type": "Purchase"},
		pluck="name",
	)
	for name in raised:
		frappe.get_doc("Material Request", name).cancel()
	return raised


@check
def oneinventory_assets_items_and_orders_for_the_stores():
	"""An asset's and an item's page as Karim reads them, an asset given to
	somebody and taken back, a purchase order from the reorder rows, and a
	readiness fix."""
	from onedesk.one_inventory import assets, custody, item, order, ready

	with as_user("karim@one.test"):
		truck = frappe.get_all("Asset", filters={"asset_name": "Pickup Truck 2", "docstatus": 1}, pluck="name")[0]
		assert assets.said(truck)
		assert item.said("ALU-6063")
		nadia = frappe.db.get_value("Employee", {"employee_name": "Nadia Khoury"})
		custody.give(truck, nadia)
		assert frappe.db.get_value("Asset", truck, "custodian") == nadia
		custody.take_back(truck)
		made = order.order([{"item_code": "ALU-6063", "qty": 50, "warehouse": wh("Stores"), "supplier": "Al Noor Aluminium"}])
		assert made and frappe.db.get_value("Purchase Order", made[0], "docstatus") == 0
		listed = order.rows()
		assert listed, "nothing to order in the demo"
		said = order.read()
		assert said["figures"]["lines"] == len(said["lines"]) == len(listed) and said["currency"], said["figures"]
		assert all(one["unit"] and one["warehouse_label"] and one["why"] in ("requested", "low") for one in said["lines"])
		assert said["figures"]["cost"] == sum(one["cost"] or 0 for one in said["lines"]) and said["can"]["order"]
		first = listed[0]
		order.order([{**first, "supplier": first.get("supplier") or "Al Noor Aluminium"}])
		def row(one):
			return one.get("material_request_item") or (one["item_code"], one["warehouse"])

		assert row(first) not in {row(one) for one in order.rows()}, "a row already on a draft order is offered again"
	with as_user(OWNER):
		ready.fix("depreciation")


@check
def oneinventory_an_item_opens_on_its_own_page():
	"""An item opens on its page as its reader may see it. The profile says
	where it is kept and who it was last bought from; the window says more is
	promised than there is and how many are being made, and lists what it is
	made from. OneAI reads an item as the page does, says what is running
	low, and a change it suggests to a reorder level is saved when approved.
	Somebody without OneInventory is refused the page."""
	from onedesk.one_ai import proposals
	from onedesk.one_inventory import ai, view

	with as_user("karim@one.test"):
		profile = view.read("ALU-6063")
		assert profile["kind"] == "Stock" and profile["stock"]["places"] and profile["stock"]["moves"], profile["stock"]
		assert profile["last_bought"] and profile["last_bought"].supplier, profile["last_bought"]
		assert profile["buying"]["suppliers"] and profile["making"]["used_in"], "the profile goes into the windows"
		assert view.files("ALU-6063") == 0
		facts = ai.item_facts("ALU-6063")
		assert facts["on_hand"] == profile["summary"]["on_hand"] and facts["suppliers"], facts
		assert "item_facts" in (ai.page({"page": "item-view", "record": "ALU-6063"}) or "")
		low = ai.running_low()
		assert {"low", "count"} <= set(low), low
		card = ai.plan_item_change("ALU-6063", warehouse=wh("Stores"), reorder_level=500, reorder_qty=1000, why="Bigger jobs coming")
		assert "proposal" in card, card
		proposals.apply(card["proposal"])
	level = frappe.get_all("Item Reorder", filters={"parent": "ALU-6063", "warehouse": wh("Stores")}, fields=["warehouse_reorder_level", "warehouse_reorder_qty"])
	assert level and level[0].warehouse_reorder_level == 500 and level[0].warehouse_reorder_qty == 1000, level
	with as_user("tariq@one.test"):
		window = view.read("WIN-CS12")
		assert window["made"] and window["making"]["materials"] and window["making"]["orders"], window["making"]
		if window["headline"]:
			assert window["headline"]["key"] in ("short", "low"), window["headline"]
	with as_user("huda@one.test"):
		service = view.read("SVC-INST")
		assert service["kind"] == "Service" and service["stock"] is None and service["selling"]["customers"]
	with as_user("nadia@one.test"):
		try:
			view.read("ALU-6063")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody without OneInventory reads an item's page")


@check
def oneinventory_an_items_stock_says_where_it_is_and_what_moved():
	"""The Stock view names each warehouse as people call it, says what is
	free to use and which reorder row is its own, so the page changes the
	level in place. A transfer is one move from the one warehouse to the
	other, with who made it."""
	from onedesk.one_inventory import view

	with as_user("karim@one.test"):
		said = view.read("ALU-6063")
	places = {one["called"]: one for one in said["stock"]["places"]}
	stores = places.get("Stores")
	assert stores, list(places)
	assert stores["free"] == stores["on_hand"] - stores["reserved"], stores
	assert stores["row"] and stores["level"], "the Stores reorder row is the item's own"
	assert all(" - " not in called for called in places), list(places)
	moved = [one for one in said["stock"]["moves"] if one.get("from")]
	villa = next((one for one in moved if one["to"] == "Mansour Villa Site"), None)
	assert villa, "the transfer to the Mansour villa reads as one move"
	assert villa["from"] == "Stores" and villa["actual_qty"] > 0 and len(villa["left"]) == 2, villa
	assert all(one["by"] for one in said["stock"]["moves"]), "each move says who made it"


@check
def oneinventory_an_items_buying_says_who_at_what_and_what_next():
	"""The Buying view: the default supplier first with their part number,
	the last price and the one before, what they agreed for the year; the
	quotes still open cheapest first by what a metre costs in dirhams, one in
	euros; what is still to arrive; who asked for what is not yet ordered,
	and for which project; and the last price paid, which the buying price
	is held against. The header's last price says it was received."""
	from onedesk.one_inventory import view

	with as_user("karim@one.test"):
		said = view.read("ALU-6063")
	buying = said["buying"]
	first = buying["suppliers"][0]
	assert first["supplier"] == "Al Noor Aluminium" and first["default"], first
	assert first["part_no"] and first["row"], "the part number is the item's own supplier row"
	assert first["before"] and first["before"] != first["rate"], first
	assert first["agreed"] and first["agreed"]["left"] > 0, first
	quotes = buying["quotes"]
	assert len(quotes) >= 2 and quotes[0]["cheapest"], quotes
	assert [one["per_unit"] for one in quotes] == sorted(one["per_unit"] for one in quotes), quotes
	assert any(one["currency"] == "EUR" and one["base_rate"] != one["rate"] for one in quotes), quotes
	assert all(one["qty"] >= one["done"] for one in buying["orders"]), buying["orders"]
	asked = [one for one in buying["requests"] if one["project_name"]]
	assert asked and asked[0]["by"], buying["requests"]
	assert buying["last_paid"] and buying["last_paid"]["currency"] == said["currency"], buying["last_paid"]
	assert said["last_bought"].kind == "received", said["last_bought"]
	makers = buying["manufacturers"]
	assert makers and makers[0]["is_default"] and makers[0]["manufacturer_part_no"], makers


@check
def oneinventory_an_items_selling_says_what_can_go_and_who_buys():
	"""The Selling view: what is on hand goes to the orders soonest due first,
	so the late order and the next two can go now and the big one is short;
	an order not fully billed can be invoiced; the quotes still open, one in
	dollars with what it comes to in dirhams; each customer's last twelve
	months with returns taken off and their last price; and the sales a
	selling price is held against."""
	from onedesk.one_inventory import view

	assert [(one["can_go"], one["short"]) for one in view.ready(
		[{"left": 5, "due": "2026-02-01"}, {"left": 4, "due": "2026-01-01"}, {"left": 3, "due": None}], 6
	)] == [(2, 3), (4, 0), (0, 3)]
	with as_user("wsadmin@one.test"):
		said = view.read("WIN-CS12")
	selling = said["selling"]
	orders = {one["party"]: one for one in selling["orders"]}
	assert orders["Crescent Schools"]["late"] and not orders["Crescent Schools"]["short"], orders["Crescent Schools"]
	assert not orders["Marina Hotels Group"]["short"] and not orders["Mansour & Sons"]["short"], orders
	assert orders["Bayview Developments"]["short"] == 280, orders["Bayview Developments"]
	assert orders["Mansour & Sons"]["to_bill"] and orders["Mansour & Sons"]["project_name"], orders["Mansour & Sons"]
	quotes = selling["quotes"]
	assert any(one["quotation_to"] == "Lead" for one in quotes), quotes
	assert any(one["currency"] == "USD" and one["base_rate"] != one["rate"] for one in quotes), quotes
	customers = {one["customer"]: one for one in selling["customers"]}
	crescent = customers["Crescent Schools"]
	assert (crescent["qty"], crescent["returned"], crescent["amount"]) == (23, 1, 54050), crescent
	assert crescent["rate"] == 2350 and crescent["last"], crescent
	acme = customers["Acme Holdings"]
	assert acme["currency"] == "USD" and acme["their_amount"] and acme["their_amount"] != acme["amount"], acme
	assert selling["sales"] and all(one["rate"] for one in selling["sales"]), selling["sales"]
	assert any(one["price_list_rate"] > 2350 for one in selling["prices"]), selling["prices"]
	with as_user("omar@one.test"):
		assert view.read("WIN-CS12")["selling"]["prices"], "Omar sells the window and sees its price"


@check
def oneinventory_an_items_making_says_what_can_be_made_and_how_far():
	"""The Making view: how many the free stock of its materials would make
	and which runs out first, the steps that make it, each open work order
	step by step with what Finish would take, what was made in the last
	year, and, for a material, what the open work orders still need of it."""
	from onedesk.one_inventory import view

	assert view.can_make([]) is None
	assert view.can_make(
		[{"item_code": "A", "item_name": "A", "covers": 9}, {"item_code": "B", "item_name": "B", "covers": 4}]
	) == {"qty": 4, "limit": "B"}
	with as_user("wsadmin@one.test"):
		window = view.read("WIN-CS12")["making"]
		profile = view.read("ALU-6063")["making"]
	assert window["made_here"] and window["materials"], window
	least = min(one["covers"] for one in window["materials"])
	assert window["can_make"]["qty"] == least, window["can_make"]
	assert [one["operation"] for one in window["steps"]] == ["Cutting", "Assembly", "Glazing"], window["steps"]
	order = window["orders"][0]
	assert [step["operation"] for step in order["steps"]] == ["Cutting", "Assembly", "Glazing"], order
	assert order["can_finish"] == order["transferred"] - order["produced_qty"], order
	assert order["project_name"], order
	assert sum(one["produced_qty"] for one in window["made"]) >= 100, window["made"]
	assert not profile["made_here"], "a bought material has no work orders of its own"
	assert any(one["item_name"] == "Sliding Door 2400" and one["left"] > 0 for one in profile["needed"]), profile["needed"]


@check
def oneinventory_home_says_what_needs_somebody_and_where_everything_is():
	"""OneInventory's Home: the orders late, the items running low, the lots
	going off, the services due this week, the work orders past their date
	and the drafts left, each counted as its own screen counts it, and a
	directory of everything the reader may open. Somebody outside the stores
	sees none of it."""
	from onedesk.one_inventory import ai, batches, home

	_before_reordering()
	with as_user("karim@one.test"):
		said = home.read()
		needs = said["needs"]
		assert needs["late"]["count"] == ai.late_orders()["count"] == said["figures"]["late"] > 0, needs["late"]
		assert needs["low"]["count"] == ai.running_low()["count"] == said["figures"]["low"] > 0, needs["low"]
		assert needs["lots"]["count"] == len(batches.dated()) == said["figures"]["going_off"] > 0, needs["lots"]
		assert len(needs["late"]["rows"]) <= home.FEW
		assert said["figures"]["worth"] > 0
		shown = {one["target"] for one in said["everything"]}
		assert {"Item", "Warehouse", "Stock Ledger", "to-order", "stock-on-hand"} <= shown, shown
		assert all(one["about"] and one["label"] for one in said["everything"])
		assert {one["group"] for one in said["everything"]} <= {key for key, _label in home.GROUPS}
	with as_user("nadia@one.test"):
		said = home.read()
		assert said["figures"]["worth"] is None and not said["needs"]["late"]["count"], said["figures"]
		assert not any(one["target"] in ("Warehouse", "Stock Ledger", "Purchase Order") for one in said["everything"])


@check
def oneinventory_home_tells_the_story_of_the_stock():
	"""OneInventory's Overview: stock's worth today and month by month, the
	same worth split by warehouse and by item group, goods' path from each
	supplier to a customer or a project, how old the stock is, how far the
	requests got, the work orders by status and the equipment by kind, each
	as the reader may see it. Somebody outside the stores sees none of it."""
	from onedesk.one_inventory import home, story

	with as_user("karim@one.test"):
		told = story.read()
		worth = home.read()["figures"]["worth"]
		cards = told["cards"]
		assert round(cards["worth"]["value"], 2) == round(worth, 2) > 0, cards["worth"]
		assert cards["worth"]["series"][-1] == round(worth, 2), cards["worth"]["series"]
		said = {
			"worth": story.stock_worth(),
			"taken_in": story.taken_in_this_month(),
			"sent_out": story.sent_out_this_month(),
			"made": story.made_this_month(),
			"on_order": story.still_on_order(),
			"papers": story.moves_this_month(),
		}
		for key, name in story.CARDS:
			assert frappe.db.get_value("Number Card", name, "module") == "One Inventory", name
			assert said[key]["value"] == cards[key]["value"] and cards[key]["card"] == name, (name, said[key], cards[key])
		assert len(cards["worth"]["series"]) == len(told["months"]) <= story.MONTHS
		where = told["where"]
		assert round(sum(one["worth"] for one in where["warehouses"])) == round(worth)
		assert round(sum(one["worth"] for one in where["groups"])) == round(worth)
		assert all(" - " not in one["name"] for one in where["warehouses"]), where["warehouses"]
		paths = told["moves"]["paths"]
		assert any(one["from"] == "Al Noor Aluminium" for one in paths), paths
		assert not any(one["to"].startswith("PROJ-") for one in paths), paths
		assert round(sum(one["worth"] for one in told["ages"])) == round(worth), told["ages"]
		steps = [one["requests"] for one in told["buying"]["requests"]]
		assert steps == sorted(steps, reverse=True) and steps[0] > 0, steps
		assert {one["kind"] for one in told["equipment"]["kinds"]} >= {"Vehicles", "Machinery"}
	with as_user("nadia@one.test"):
		told = story.read()
		assert not told["cards"].get("worth") and not told["where"] and not told["moves"], told["cards"]


@check
def oneinventory_lots_and_numbers_are_read_where_people_look():
	"""Batch and Serial No are frappe's own lists; what the item's Stock tab
	and OneAI read of them: the sealant's two lots, the one going off first,
	each with what is left and where, the six smart locks by number in the
	Stores, and the items kept either way. An item set up to be kept in
	lots, and a lot made for it, show at once. Somebody outside the stores
	sees none of it, and /desk/lots leads to the Batch list."""
	from onedesk.one_demo.lots import LOCK, LOCKS
	from onedesk.one_inventory import ai, lots

	assert not frappe.db.exists("Page", "lots")
	with as_user("karim@one.test"):
		sealant = [one for one in lots.lots() if one["item"] == "SIL-WP"]
		assert [one["batch_id"] for one in sealant] == ["SIL-WP-A1", "SIL-WP-B2"], sealant
		assert sealant[0]["state"] == "Expiring Soon" and not sealant[1]["state"], sealant
		assert {place["warehouse"] for place in sealant[0]["where"]} == {wh("Stores"), wh("Mansour Villa Site")}, sealant[0]
		assert sum(place["qty"] for place in sealant[0]["where"]) == sealant[0]["batch_qty"]
		figures = lots.figures()
		assert figures["going_off"] >= 1 and figures["serials"] >= len(LOCKS[1]), figures
		assert [one["batch_id"] for one in lots.lots(soon=1) if one["item"] == "SIL-WP"] == ["SIL-WP-A1"]

		numbers = lots.serials(item=LOCK)
		assert sorted(one["serial_no"] for one in numbers) == LOCKS[1], numbers
		assert all(one["status"] == "Active" and one["warehouse"] == wh("Stores") for one in numbers), numbers
		assert [one["serial_no"] for one in lots.serials(search="SL-0003")] == ["SL-0003"]
		kept = {one["name"]: one for one in lots.kept_in_lots()}
		assert kept["SIL-WP"]["has_batch_no"] and kept[LOCK]["has_serial_no"], kept

		frappe.get_doc({"doctype": "Item", "item_code": "CHK-PRIMER", "item_name": "Check Primer", "item_group": "Consumable", "stock_uom": "Nos", "is_stock_item": 1}).insert()
		offered = [row[0] for row in lots.can_be_tracked("Item", "", "name", 0, 500)]
		assert "CHK-PRIMER" in offered and "SIL-WP" not in offered and "ALU-6063-PC" not in offered, offered
		frappe.client.set_value("Item", "CHK-PRIMER", {"has_batch_no": 1, "create_new_batch": 1, "batch_number_series": "PR-.###", "has_expiry_date": 1, "shelf_life_in_days": 90})
		made = frappe.client.insert({"doctype": "Batch", "item": "CHK-PRIMER", "batch_id": "", "manufacturing_date": frappe.utils.today()})
		assert made["batch_id"].startswith("PR-"), made
		assert str(made["expiry_date"]) == frappe.utils.add_days(frappe.utils.today(), 90), made
		assert "CHK-PRIMER" in {one["name"] for one in lots.kept_in_lots()}

		facts = ai.lots_and_numbers(item="SIL-WP")
		assert [one["lot"] for one in facts["lots"]] == ["SIL-WP-A1", "SIL-WP-B2"], facts
		assert len(ai.lots_and_numbers(item=LOCK)["numbers"]) == len(LOCKS[1])
		assert ai.lots_and_numbers().get("figures"), "OneAI reads the counts the list does"
		assert ai.lots_and_numbers(item="NOPE").get("error")
	with as_user("nadia@one.test"):
		assert lots.figures()["lots"] is None and not frappe.has_permission("Batch", "create")
		assert ai.lots_and_numbers().get("error")


@check
def oneinventory_quotes_ask_compare_and_order():
	"""Asking for prices, on frappe's own request and quote forms: the
	stores' profile asked of Al Noor and Euro Hardware, Euro
	Hardware's answer in euros compared in dirhams, Al Noor still waiting,
	and the villa's request with every cheapest line ordered already. Al
	Noor's quote typed in makes them cheapest, Order the Cheapest drafts
	their order from their quote, and Ask for Prices drafts a request by
	ERPNext's own mapper. OneAI reads it. Somebody outside buying sees none
	of it."""
	from erpnext.buying.doctype.request_for_quotation.mapper import make_supplier_quotation_from_rfq

	from onedesk.one_demo.ordering import ALUMINIUM, EURO, STORES_ASKED
	from onedesk.one_inventory import ai, quotes

	code, qty, rate = STORES_ASKED
	assert not frappe.db.exists("Page", "quotes")
	with as_user("karim@one.test"):
		figures, asked = quotes.figures(), quotes.asked()
		assert figures["waiting"] >= 1 and figures["expiring"] >= 1, figures
		stores = next(one for one in asked if any(row["supplier"] == EURO for row in one["suppliers"]))
		answered = {row["supplier"]: row["answered"] for row in stores["suppliers"]}
		assert answered == {ALUMINIUM: False, EURO: True} and not stores["ordered"], stores

		compared = quotes.compare(stores["name"])
		line = compared["lines"][0]
		assert line["item"] == code and line["qty"] == qty and line["cheapest"] == EURO, line
		offer = line["offers"][EURO]
		assert offer["rate"] == rate and offer["base_rate"] > rate * 3, offer
		assert [one["quote"] is None for one in compared["suppliers"]] == [True, False], compared["suppliers"]

		villa = quotes.compare(next(one["name"] for one in asked if one["ordered"] and one["answered"] == 2))
		assert all(one["ordered"] for one in villa["lines"]) and not any(one["cheapest_on"] for one in villa["suppliers"]), villa

		theirs = make_supplier_quotation_from_rfq(stores["name"], for_supplier=ALUMINIUM)
		for row in theirs.items:
			row.rate = 24.0
		theirs.insert()
		theirs.submit()
		compared = quotes.compare(stores["name"])
		assert compared["lines"][0]["cheapest"] == ALUMINIUM, compared["lines"]
		made = quotes.order_cheapest(stores["name"])
		order = frappe.get_doc("Purchase Order", made[0])
		assert len(made) == 1 and order.docstatus == 0 and order.supplier == ALUMINIUM, made
		assert [(row.item_code, row.qty, row.supplier_quotation) for row in order.items] == [(code, qty, theirs.name)], order.items

		pending = frappe.get_list("Material Request", filters={"docstatus": 1, "material_request_type": "Purchase", "status": "Pending"}, pluck="name", limit=1)
		if pending:
			drafted = frappe.get_doc("Request for Quotation", quotes.ask(pending[0], [ALUMINIUM, EURO]))
			assert drafted.docstatus == 0 and [row.supplier for row in drafted.suppliers] == [ALUMINIUM, EURO], drafted.suppliers
			assert all(row.material_request == pending[0] for row in drafted.items)

		facts = ai.quotes_now()
		assert facts["figures"] == quotes.figures() and facts["newest_compared"], facts
	with as_user("nadia@one.test"):
		assert not quotes.asked() and quotes.figures()["waiting"] is None, quotes.figures()
		assert not frappe.has_permission("Request for Quotation", "create")
		assert ai.quotes_now().get("error")


@check
def oneinventory_upkeep_says_what_is_due_broken_and_done():
	"""Servicing the equipment, on frappe's own maintenance log and repair
	forms: the second truck's service late with Yousef, Huda's laptop out of
	order, a plan for each serviced asset and the CNC centre's checks done.
	Mark Done on the truck's service takes it off what is due, puts it in
	the log and moves its next date a quarter on, as ERPNext works it out.
	OneAI reads it. Somebody outside the stores sees none of it."""
	from onedesk.one_inventory import ai, upkeep

	assert not frappe.db.exists("Page", "upkeep")
	with as_user("karim@one.test"):
		figures = upkeep.figures()
		assert figures["late"] >= 1 and figures["broken"] >= 1, figures
		truck = next(one for one in upkeep.due() if one["asset_name"] == "Pickup Truck 2")
		assert truck["late"] and truck["assign_to_name"] == "Yousef Bakr", truck
		broken = [one for one in upkeep.repairs() if one["open"]]
		assert [one["asset_name"] for one in broken] == ["Laptop Huda"] and broken[0]["days_out"] >= 0, broken
		plans = {one["asset_name"]: one for one in upkeep.plans()}
		assert {"Pickup Truck 1", "Pickup Truck 2", "CNC Profile Machining Centre"} <= set(plans), list(plans)
		assert any(one["asset_name"] == "CNC Profile Machining Centre" for one in upkeep.log())
		facts = ai.upkeep_now()
		assert any(one["asset"] == "Pickup Truck 2" and one["late"] for one in facts["services"]), facts

		upkeep.done(truck["name"], frappe.utils.today(), "Oil and filters changed.")
		assert truck["name"] not in {one["name"] for one in upkeep.due()}
		assert truck["name"] in {one["name"] for one in upkeep.log()}
		task = frappe.db.get_value("Asset Maintenance Task", {"parent": truck["asset"]}, ["last_completion_date", "next_due_date"], as_dict=True)
		assert str(task.last_completion_date) == frappe.utils.today() and str(task.next_due_date) == str(frappe.utils.add_months(frappe.utils.today(), 3)), task
	with as_user("nadia@one.test"):
		assert not upkeep.due() and upkeep.figures()["late"] is None
		assert not frappe.has_permission("Asset Maintenance Log", "submit")
		assert ai.upkeep_now().get("error")


@check
def oneinventory_an_items_head_has_its_barcodes_and_trends():
	"""A new item is given its code as its first barcode. Manage Barcodes puts
	them in the order it is given, so the first two are the head's, and
	somebody who may only read the item can't change them. The head's cards
	draw twelve months of stock held, its worth and what was ordered, and the
	prices it was last bought at."""
	from onedesk.one_inventory import barcodes, view

	with as_user("karim@one.test"):
		item = frappe.get_doc(
			{"doctype": "Item", "item_code": "CHK-BAR-1", "item_name": "Barcode check", "item_group": "Raw Material", "stock_uom": "Nos"}
		).insert()
		assert [row.barcode for row in item.barcodes] == ["CHK-BAR-1"], item.barcodes
		rows = barcodes.save("CHK-BAR-1", [{"barcode": "6291041500213", "barcode_type": "EAN"}, {"barcode": "CHK-BAR-1"}])
		assert [row["barcode"] for row in rows] == ["6291041500213", "CHK-BAR-1"], rows
		said = view.read("CHK-BAR-1")
		assert [row["barcode"] for row in said["barcodes"]][: barcodes.FEATURED] == ["6291041500213", "CHK-BAR-1"]
		head = view.read("ALU-6063")
		trends = head["trends"]
		assert len(trends["held"]) == 12 and len(trends["worth"]) == 12 and len(trends["ordered"]) == 12, trends
		assert abs(trends["held"][-1] - head["summary"]["on_hand"]) < 0.001, (trends["held"], head["summary"])
		assert trends["prices"], "the last prices it was bought at"
	with as_user("nadia@one.test"):
		try:
			barcodes.save("CHK-BAR-1", [])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody who can't change the item changed its barcodes")


@check
def oneinventory_lots_say_their_dates_and_where_they_went():
	"""The sealant's January lot runs out of date within the month with some
	still in the Stores and some at the villa. The item's page says so under
	Needs You, the lot's head says what is left and where, when it expires,
	the receipt it came from and that some was taken out, and whoever keeps
	the stores is told once. Past its date, it says Expired. Somebody
	without OneInventory is refused the item."""
	from frappe.utils import today

	from onedesk.one_inventory import batches, heads, tell, view

	old = frappe.get_doc("Batch", {"batch_id": "SIL-WP-A1", "item": "SIL-WP"})
	with as_user("karim@one.test"):
		said = view.read("SIL-WP")
		states = {one["batch_id"]: one["state"] for one in said["stock"]["batches"]}
		assert states == {"SIL-WP-A1": "Expiring Soon", "SIL-WP-B2": None}, states
		left = batches.left(old.name)
		assert {one["warehouse"] for one in left} == {wh("Stores"), wh("Mansour Villa Site")}, left
		assert sum(one["qty"] for one in left) == old.batch_qty == 120
		assert heads.batch_left(old).startswith("120"), heads.batch_left(old)
		assert heads.batch_expires(old)["tone"] == "waiting"
		came = heads.batch_came_from(old)
		assert came["route"].startswith("/desk/purchase-receipt/") and came["route"].endswith(came["value"]), came
		assert heads.batch_went(old)["value"] == 1
		assert [one.batch_id for one in batches.dated("SIL-WP")] == ["SIL-WP-A1"]
	with _Told() as told:
		tell.expiring()
	keepers = told.to("Expiring Soon")
	assert keepers and keepers <= set(frappe.get_all("Has Role", filters={"role": "Stock Manager"}, pluck="parent")), keepers
	frappe.db.set_value("Batch", old.name, "expiry_date", add_days(today(), -1))
	old.reload()
	assert heads.batch_expires(old)["tone"] == "alarm" and batches.state(old.expiry_date, old.batch_qty) == "Expired"
	with as_user("nadia@one.test"):
		try:
			view.read("SIL-WP")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody without OneInventory reads the sealant")


@check
def oneinventory_new_item_parts_list_and_sizes():
	"""New Item makes an item by its kind, measured by area or length or by the
	piece; a sheet kept by the piece says how many square metres it is. A
	parts list pasted in is matched to the items there are, and its new parts
	are added as stock items. A line of a measured item takes its quantity
	from its size, in the line's unit, on a quotation and on the order made
	from it, and the size is kept for print, in the line's size unit. Concrete
	is sold by volume; a line typed in centimetres counts as one."""
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	from onedesk.one_inventory import kinds, measure, parts

	with as_user("karim@one.test"):
		glass = kinds.make({"kind": "Stock", "title": "Clear Glass 8 mm", "code": "DEMO-GLASS-8", "group": "Products", "unit": "Square Meter", "measured_by": "Area", "sold": 1, "selling_price": 60, "bought": 1})
		sheet = kinds.make({"kind": "Stock", "title": "Aluminium Sheet 3 mm", "code": "DEMO-SHEET-3", "group": "Products", "unit": "Nos", "measured_by": "Area", "per_unit_area": 3.125, "sold": 1, "selling_price": 180, "bought": 1})
		profile = kinds.make({"kind": "Stock", "title": "Edge Trim", "code": "DEMO-TRIM", "group": "Products", "unit": "Meter", "measured_by": "Length", "sold": 1, "selling_price": 12, "bought": 1})
		concrete = kinds.make({"kind": "Stock", "title": "Ready-Mix Concrete", "code": "DEMO-CONCRETE", "group": "Products", "unit": "Litre", "measured_by": "Volume", "per_unit_volume": 0.001, "sold": 1, "selling_price": 1, "bought": 1})
		assert round(measure.line_quantity(concrete, "Volume", "Cubic Meter", 2, 100, 50, 20, "Centimeter"), 3) == 0.2
		assert round(measure.line_quantity(concrete, "Volume", "Litre", 2, 100, 50, 20, "Centimeter"), 1) == 200.0
		try:
			measure.line_quantity(concrete, "Volume", "Litre", 1, 1, 1, 1, "Kilogram")
			raise AssertionError("a size in kilograms")
		except frappe.ValidationError:
			pass
		assert frappe.db.get_value("Item", glass, "one_measured_by") == "Area"
		assert {(r.uom, round(r.conversion_factor, 2)) for r in frappe.get_doc("Item", sheet).uoms} >= {("Square Meter", 0.32)}
		assert set(kinds.stocked(["ALU-6063"])) == {"ALU-6063"}, "the Items list reads what the stores hold"
		found = parts.read(text="code,name,qty\nALU-6063,,2\nDEMO-GASKET,Door gasket,4\nALU-6063,,1")
		assert [(one["code"], one["qty"], one["new"]) for one in found["parts"]] == [("ALU-6063", 3.0, False), ("DEMO-GASKET", 4.0, True)], found
		rows = parts.add(found["parts"])
		assert [row["item_code"] for row in rows] == ["ALU-6063", "DEMO-GASKET"] and frappe.db.exists("Item", "DEMO-GASKET")
		assert round(measure.line_quantity(glass, "Area", "Square Meter", 4, 1200, 800), 3) == 3.84
		assert round(measure.line_quantity(sheet, "Area", "Nos", 2, 1250, 2500), 3) == 2.0
		assert round(measure.line_quantity(profile, "Length", "Meter", 6, 2400), 3) == 14.4
		assert measure.unit_is("Foot") == "Length" and measure.unit_is("Square Foot") == "Area" and not measure.unit_is("Nos")
		cord = frappe.get_doc({"doctype": "Item", "item_code": "DEMO-CORD", "item_name": "Backer Rod", "item_group": "Products", "stock_uom": "Meter"}).insert()
		assert cord.one_measured_by == "Length", cord.one_measured_by
		bolt = frappe.get_doc({"doctype": "Item", "item_code": "DEMO-BOLT", "item_name": "Bolt", "item_group": "Products", "stock_uom": "Nos"}).insert()
		assert bolt.one_measured_by == "No", bolt.one_measured_by
		bolt.stock_uom = "Square Meter"
		bolt.save()
		assert bolt.one_measured_by == "Area", "a new unit that is an area sells it by area"
		assert frappe.db.get_value("Item", sheet, "one_measured_by") == "Area", "a sheet kept by the piece keeps what it says"
		assert not frappe.db.exists("Item", {"one_measured_by": ["in", ["", None]]}), "every item says how it is sold"
		panel = frappe.get_doc({"doctype": "Item", "item_code": "DEMO-CW", "item_name": "Curtain Wall Panel", "item_group": "Products", "stock_uom": "Nos", "one_measured_by": "Piece"}).insert()
		assert panel.one_measured_by == "Piece", "a panel sold by the piece keeps what it says"
	with as_user("omar@one.test"):
		customer = frappe.get_all("Customer", limit=1, pluck="name")[0]
		quote = frappe.get_doc({"doctype": "Quotation", "quotation_to": "Customer", "party_name": customer, "items": [
			{"item_code": glass, "one_pieces": 4, "one_length": 1200, "one_width": 800, "qty": 1},
			{"item_code": sheet, "one_pieces": 2, "one_length": 1250, "one_width": 2500, "qty": 1},
			{"item_code": profile, "one_pieces": 6, "one_length": 2400, "qty": 1},
			{"item_code": "DEMO-CW", "one_length": 20525, "one_width": 3500, "qty": 2},
			{"item_code": concrete, "one_size_uom": "Centimeter", "one_pieces": 2, "one_length": 100, "one_width": 50, "one_height": 20, "uom": "Cubic Meter", "qty": 1},
		]}).insert()
		said = [(row.qty, row.uom, row.one_size) for row in quote.items]
		assert said == [
			(3.84, "Square Meter", "4 × 1200 × 800 mm"), (2.0, "Nos", "2 × 1250 × 2500 mm"), (14.4, "Meter", "6 × 2400 mm"),
			(2.0, "Nos", "20525 × 3500 mm"), (0.2, "Cubic Meter", "2 × 100 × 50 × 20 cm"),
		], said
		assert quote.items[0].one_size_uom == "Millimeter", "the workspace's unit, said on the line"
		quote.submit()
		order = make_sales_order(quote.name)
		assert [(row.one_pieces, row.one_length, row.qty) for row in order.items][:1] == [(4, 1200, 3.84)], "the order keeps the size"


@check
def oneinventory_a_return_is_counted_on_what_it_came_back_against():
	"""A window sent back is counted on its delivery, and goods sent back to a
	supplier on their receipt, so the delivery's head says Returned and its
	billed share reads true. The demo saves a return and submits it as the
	form does; one built and submitted in one go was never counted."""
	from frappe.utils import flt

	for doctype in ("Delivery Note", "Purchase Receipt"):
		returns = frappe.get_all(doctype, filters={"is_return": 1, "docstatus": 1}, pluck="return_against")
		assert returns, f"the demo sends back no {doctype}"
		for against in returns:
			assert flt(frappe.db.get_value(doctype, against, "per_returned")) > 0, (doctype, against)
	assert not frappe.get_all("Stock Reconciliation", filters={"docstatus": 1, "set_warehouse": ["is", "not set"]})
	shipment = frappe.get_all("Shipment Delivery Note", filters={"parenttype": "Shipment"}, pluck="delivery_note")
	assert shipment and frappe.db.get_value("Delivery Note", shipment[0], "customer") == "Gulf Properties REIT", shipment


@check
def oneinventory_transfer_stock_moves_it_in_one_step():
	"""Transfer Stock on Stock on Hand asks only where from, where to and what,
	with the project and a note, and ERPNext's Material Transfer is made and submitted as the reader: the
	hinges leave Stores and arrive in Finished Goods, a batched item (the
	sealant) takes its batches as ERPNext picks them, more than there is is
	refused by ERPNext's own check, and somebody without OneInventory cannot
	move anything."""
	from frappe.utils import flt

	from onedesk.one_inventory import stock

	def held(item, place):
		return flt(frappe.db.get_value("Bin", {"item_code": item, "warehouse": wh(place)}, "actual_qty"))

	before = held("HW-HINGE", "Stores"), held("HW-HINGE", "Finished Goods")
	with as_user("karim@one.test"):
		project = frappe.get_all("Project", filters={"status": "Open"}, pluck="name", limit=1)[0]
		name = stock.transfer(
			wh("Stores"), wh("Finished Goods"), [{"item": "HW-HINGE", "qty": 10}, {"item": "SIL-WP", "qty": 5}], project=project, remarks="For the villa's doors"
		)
		entry = frappe.get_doc("Stock Entry", name)
		assert entry.docstatus == 1 and entry.purpose == "Material Transfer" and len(entry.items) == 2, entry.as_dict()
		assert entry.project == project and {row.project for row in entry.items} == {project} and entry.remarks == "For the villa's doors"
		assert (held("HW-HINGE", "Stores"), held("HW-HINGE", "Finished Goods")) == (before[0] - 10, before[1] + 10)
		try:
			stock.transfer(wh("Stores"), wh("Finished Goods"), [{"item": "HW-HINGE", "qty": 1_000_000}])
			raise AssertionError("moved more than there is")
		except frappe.ValidationError:
			pass
	with as_user("nadia@one.test"):
		try:
			stock.transfer(wh("Stores"), wh("Finished Goods"), [{"item": "HW-HINGE", "qty": 1}])
			raise AssertionError("moved stock without OneInventory")
		except frappe.PermissionError:
			pass


@check
def oneinventory_stock_on_hand_says_what_the_stores_hold():
	"""Stock on Hand lists what is held now, its worth what the warehouses
	hold in the books' own figures. The silicone is low in Stores, more
	windows are promised than there are, one warehouse or a search narrows it,
	and a warehouse's head says what it holds, under a group too. OneAI reads
	the stores as the page does, and the Inventory Check sends new stock to
	the Stores. Somebody without OneInventory is refused."""
	from frappe.utils import flt

	from onedesk.one_inventory import ai, heads, ready, stock

	_before_reordering()
	held = sum(flt(one) for one in frappe.get_all("Bin", pluck="stock_value"))
	with as_user("karim@one.test"):
		every = stock.on_hand()
		assert every["count"] and abs(every["worth"] - held) < 0.01, (every["worth"], held)
		company = frappe.db.get_value("Warehouse", wh("Stores"), "company")
		assert {frappe.db.get_value("Warehouse", one["name"], "company") for one in every["warehouses"]} == {company}
		low = {one["item"]: one for one in every["items"] if one["low_in"]}
		assert "SIL-CLR" in low and wh("Stores") in low["SIL-CLR"]["low_in"], list(low)
		assert any(one["item"] == "WIN-CS12" and one["free"] < 0 for one in every["items"]), "the windows are promised beyond what there is"
		assert all(one["state"] == "short" for one in every["items"] if one["free"] < 0), "short is the status of anything promised beyond what there is"
		assert all(one["on_hand"] == one["committed"] + one["free"] for one in every["items"]), "on hand is committed and available, as Shopify splits it"
		stores = stock.on_hand(warehouse=wh("Stores"))
		in_stores = sum(flt(one) for one in frappe.get_all("Bin", filters={"warehouse": wh("Stores")}, pluck="stock_value"))
		assert abs(stores["worth"] - in_stores) < 0.01 and stores["worth"] < every["worth"]
		assert sorted(one["item"] for one in stock.on_hand(search="silicone")["items"]) == ["SIL-CLR", "SIL-WP"]
		place = frappe.get_doc("Warehouse", wh("Stores"))
		assert heads.warehouse_items(place) == sum(1 for one in stores["items"] if one["on_hand"] > 0)
		assert heads.warehouse_low(place)["value"] >= 1 and heads.warehouse_last(place)
		assert heads.warehouse_worth(place)
		group = frappe.db.get_value("Warehouse", {"is_group": 1, "parent_warehouse": ["in", ("", None)]}) or frappe.db.get_value("Warehouse", {"is_group": 1})
		assert heads.warehouse_items(frappe.get_doc("Warehouse", group)) >= heads.warehouse_items(place), "a group holds what is under it"
		facts = ai.stock_on_hand(warehouse=wh("Stores"))
		assert abs(facts["worth"] - in_stores) < 0.01 and any(one["item"] == "SIL-CLR" and one["low_in"] for one in facts["lines"]), facts["worth"]
		assert ai.stock_on_hand(warehouse="Nowhere").get("error")
		assert "stock_on_hand" in (ai.page({"page": "stock-on-hand"}) or "")
	with as_user(OWNER):
		ready.fix("home")
		said = {one["key"]: one for one in ready.checks()}
		assert frappe.db.get_value("Company", ready.company().name, "default_warehouse") == wh("Stores")
		assert said["home"]["state"] == said["below_zero"]["state"] == said["reorder"]["state"] == ready.READY, said
	with as_user("nadia@one.test"):
		assert ai.stock_on_hand().get("error")
		try:
			stock.on_hand()
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody without OneInventory reads the stores")


@check
def oneinventory_goods_arrive_as_the_receipt_says():
	"""Receiving, as Karim and Huda do it. The euro hardware's freight and duty
	are added to what each piece cost, in dirhams, and its value in the stores
	is its euro price at the rate plus those. Six of forty square metres of
	tempered glass are rejected on arrival after their inspection, kept apart
	and left off the bill. A receipt prints as a goods received note, and OneAI
	reads a receipt, says what is still to come and drafts the next one."""
	from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice

	from onedesk.one_ai import proposals
	from onedesk.one_inventory import ai, heads, ready

	euro = frappe.db.get_value("Landed Cost Purchase Receipt", {"docstatus": 1}, "receipt_document")
	assert euro, "no landed cost in the demo"
	assert frappe.has_permission("Landed Cost Voucher", "create", user="huda@one.test"), "the accountant cannot add freight and duty"
	glass = frappe.db.get_value("Quality Inspection", {"reference_type": "Purchase Receipt", "docstatus": 1}, "reference_name")
	with as_user("karim@one.test"):
		doc = frappe.get_doc("Purchase Receipt", euro)
		assert doc.currency == "EUR" and abs(flt(doc.base_net_total) - flt(doc.net_total) * flt(doc.conversion_rate)) <= CENTS
		added = sum(flt(row.landed_cost_voucher_amount) for row in doc.items)
		charges = sum(flt(one) for one in frappe.get_all("Landed Cost Taxes and Charges", filters={"parent": ["in", frappe.get_all("Landed Cost Purchase Receipt", filters={"receipt_document": euro, "docstatus": 1}, pluck="parent")]}, pluck="base_amount"))
		assert added and abs(added - charges) <= CENTS, (added, charges)
		valued = sum(flt(row.valuation_rate) * flt(row.stock_qty) for row in doc.items)
		assert abs(valued - flt(doc.base_net_total) - added) <= 1, (valued, doc.base_net_total, added)
		assert heads.receipt_landed(doc) and "€" in heads.receipt_worth(doc)["label"], heads.receipt_worth(doc)
		assert heads.receipt_order(doc)["route"].startswith("/desk/purchase-order/")
		arrived = frappe.get_doc("Purchase Receipt", glass)
		row = arrived.items[0]
		assert (row.received_qty, row.qty, row.rejected_qty) == (40, 34, 6) and frappe.db.get_value("Warehouse", row.rejected_warehouse, "is_rejected_warehouse")
		assert heads.receipt_rejected(arrived)["tone"] == "alarm" and heads.receipt_rejected(doc) is None
		printed = frappe.get_print("Purchase Receipt", arrived.name, print_format="One Purchase Receipt")
		assert "Goods Received Note" in printed and arrived.supplier_name in printed
		facts = ai.receipt_facts(glass)
		assert facts["lines"][0]["rejected"] == 6 and facts["inspections"][0]["item"] == "GLS-TMP10", facts
		assert ai.receipt_facts(euro)["freight_and_duty"], "freight and duty on the euro hardware"
		coming = ai.still_to_arrive(supplier="Euro Hardware Trading")
		assert coming["lines"] and all(one["supplier"] == "Euro Hardware Trading" for one in coming["lines"]), coming
		order = coming["lines"][0]["order"]
		card = ai.plan_receipt(order, lines=[{"item": coming["lines"][0]["item"], "qty": 1}])
		made = proposals.apply(card["proposal"])["record"]
		drafted = frappe.get_doc("Purchase Receipt", made)
		assert drafted.docstatus == 0 and [(one.purchase_order, one.qty) for one in drafted.items] == [(order, 1)], drafted.items
		drafted.delete()
	with as_user(OWNER):
		ready.fix("rejected")
		assert {one["key"]: one for one in ready.checks()}["rejected"]["state"] == ready.READY
		bill = make_purchase_invoice(glass)
		assert [flt(one.qty) for one in bill.items] == [34], "the six rejected are not billed"
	assert frappe.db.get_value("Notification", "Material Request Receipt Notification", "enabled"), "nobody is told their goods came"
	with as_user("nadia@one.test"):
		assert ai.receipt_facts(glass).get("error")


@check
def oneinventory_goods_go_out_as_the_order_says():
	"""Delivering, as Karim does it. The villa's windows were picked, packed in
	three crates and put on Yousef's trip, and its twenty sliding doors are
	held for it: held stock is counted once, not twice, in what is free to
	sell. A delivery says its order, total and trip, a packing slip and a pick
	list print, anybody who reads an order can open it, and OneAI reads a
	delivery, says what is still to go and drafts the next one."""
	from onedesk.one_ai import memory, proposals
	from onedesk.one_inventory import ai, heads, item, ready, stock, trips

	villa = frappe.db.get_value("Sales Order", {"project": VILLA, "docstatus": 1})
	note = frappe.db.get_value("Delivery Note Item", {"against_sales_order": villa, "docstatus": 1}, "parent")
	assert note, "nothing of the villa's has gone out"
	assert frappe.db.get_value("Stock Reservation Entry", {"voucher_no": villa, "item_code": "DR-SL24", "docstatus": 1}, "reserved_qty") == 20
	with as_user("karim@one.test"):
		assert frappe.has_permission("Selling Settings", "read"), "an order opens with a permission error"
		doc = frappe.get_doc("Delivery Note", note)
		assert heads.delivery_order(doc)["value"] == villa
		assert "Yousef Bakr" in heads.delivery_trip(doc)["value"], heads.delivery_trip(doc)
		assert heads.delivery_total(doc)
		trip = frappe.get_doc("Delivery Trip", frappe.db.get_value("Delivery Stop", {"delivery_note": note}, "parent"))
		trips.onload(trip)
		assert trip.get_onload().maps is False, "the route buttons show with no maps key"
		slip = frappe.get_doc("Packing Slip", {"delivery_note": note, "docstatus": 1})
		printed = frappe.get_print("Packing Slip", slip.name, print_format="One Packing Slip")
		assert "Packing Slip" in printed and doc.customer_name in printed and "From Case" in printed
		pick = frappe.get_doc("Pick List", frappe.db.get_value("Pick List Item", {"sales_order": villa}, "parent"))
		assert "Pick List" in frappe.get_print("Pick List", pick.name, print_format="One Pick List")
		bins = frappe.get_all("Bin", filters={"item_code": "DR-SL24"}, fields=["warehouse", "actual_qty", "reserved_qty", "reserved_stock", "ordered_qty", "projected_qty", "stock_value"])
		said = item.summary(bins, [])
		ordered = sum(flt(one.reserved_qty) for one in bins)
		assert said["held"] == 20 and said["free"] == said["on_hand"] - ordered, said
		row = next(one for one in stock.on_hand(search="DR-SL24")["items"] if one["item"] == "DR-SL24")
		assert row["free"] == said["free"] and row["held"] == 20, row
		facts = memory.about_record("Delivery Note", note)
		assert {row["against_sales_order"] for row in facts["items"]} == {villa}, facts["items"]
		assert {"Packing Slip", "Delivery Trip"} <= set(facts["links_here"]), facts["links_here"]
		going = ai.still_to_deliver(project=VILLA)
		doors = next(one for one in going["lines"] if one["item"] == "DR-SL24")
		assert doors["held_for_it"] == 20, doors
		card = ai.plan_delivery(villa, lines=[{"item": "WIN-CS12", "qty": 1}])
		made = proposals.apply(card["proposal"])["record"]
		drafted = frappe.get_doc("Delivery Note", made)
		assert drafted.docstatus == 0 and [(one.against_sales_order, one.qty) for one in drafted.items] == [(villa, 1)], drafted.items
		drafted.delete()
	assert {one["key"]: one for one in ready.checks()}["held"]["state"] == ready.READY
	with as_user("nadia@one.test"):
		try:
			memory.about_record("Delivery Note", note)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the stores read a delivery")


@check
def oneinventory_stock_moves_and_counts_reach_the_books():
	"""Moving and counting, as Karim, Tariq and Huda do it. The villa's
	materials went from the stores to its site on a transfer note, Tariq used
	some there, and a count of the stores found three hinges short, posted to
	the books as a loss. A recalculation that fails and a warehouse posting to
	the wrong account reach the stock and accounts managers."""
	from erpnext.stock.utils import get_stock_balance

	from onedesk.one_inventory import heads, ready, tell

	site = frappe.db.get_value("Warehouse", {"warehouse_name": "Mansour Villa Site"})
	sent = frappe.get_doc("Stock Entry", frappe.db.get_value("Stock Entry", {"docstatus": 1, "purpose": "Material Transfer", "to_warehouse": site}))
	used = frappe.get_doc("Stock Entry", frappe.db.get_value("Stock Entry", {"docstatus": 1, "purpose": "Material Issue", "from_warehouse": site}))
	assert sent.owner == "karim@one.test" and used.owner == "tariq@one.test"
	with as_user("tariq@one.test"):
		assert frappe.has_permission("Stock Settings", "read")
	assert sent.project == used.project == frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	moved = {
		code: sum(flt(one) for one in frappe.get_all("Stock Ledger Entry", filters={"warehouse": site, "item_code": code, "voucher_type": "Stock Entry", "is_cancelled": 0}, pluck="actual_qty"))
		for code in ("ALU-6063", "SIL-CLR")
	}
	assert moved == {"ALU-6063": 40, "SIL-CLR": 6}, moved
	assert flt(get_stock_balance("ALU-6063", site)) == 40

	assert heads.move_from(sent)["value"] == "Stores" and heads.move_to(sent)["value"] == "Mansour Villa Site"
	assert heads.move_value(sent) and heads.move_used(sent) is None and heads.move_to(used) is None
	printed = frappe.get_print("Stock Entry", sent.name, print_format="One Stock Entry")
	assert "Transfer Note" in printed and "Issue Note" in frappe.get_print("Stock Entry", used.name, print_format="One Stock Entry")
	assert "Mansour Villa Site" in printed and "Villa 14, Al Wasl Road" in printed, "it says where the goods go"
	assert frappe.db.get_value("Print Format", "One Stock Entry", "doc_type") == "Stock Entry"

	count = frappe.get_doc("Stock Reconciliation", {"purpose": "Stock Reconciliation", "docstatus": 1})
	adjustment = frappe.get_cached_value("Company", count.company, "stock_adjustment_account")
	assert count.owner == "karim@one.test" and count.expense_account == adjustment and flt(count.difference_amount) < 0
	posted = frappe.get_all("GL Entry", filters={"voucher_no": count.name, "account": adjustment, "is_cancelled": 0}, fields=["debit", "credit"])
	assert flt(sum(flt(one.debit) - flt(one.credit) for one in posted), 2) == flt(-count.difference_amount, 2)
	assert heads.count_where(count)["value"] == "Stores" and heads.count_items(count) == "1"
	assert frappe.get_meta("Stock Reconciliation").get_field("purpose").default == "Stock Reconciliation"

	with as_user("huda@one.test"):
		rows = {one["key"]: one for one in ready.checks()}
	assert rows["stock_accounts"]["state"] == ready.READY and rows["reposts"]["state"] == ready.READY
	entry = frappe.get_all("Repost Item Valuation", filters={"docstatus": 1, "status": "Completed"}, pluck="name", limit=1)[0]
	rejected = frappe.db.get_value("Warehouse", {"warehouse_name": "Rejected"})
	cash = frappe.db.get_value("Account", {"company": count.company, "account_type": "Cash", "is_group": 0})
	frappe.db.set_value("Repost Item Valuation", entry, "status", "Failed", update_modified=False)
	frappe.db.set_value("Warehouse", rejected, "account", cash, update_modified=False)
	frappe.flags.pop("warehouse_account_map", None)
	try:
		with as_user("huda@one.test"):
			rows = {one["key"]: one for one in ready.checks()}
		assert rows["reposts"]["state"] == ready.TO_DO and rows["reposts"]["fix"] == "reposts"
		assert rows["stock_accounts"]["state"] == ready.TO_DO and rejected in rows["stock_accounts"]["says"]
		with _Told() as told:
			tell.stock_values()
		assert {"huda@one.test", "karim@one.test"} <= told.to("Reposting Failed")
		assert {"huda@one.test", "karim@one.test"} <= told.to("Stock Account Wrong")
	finally:
		frappe.db.set_value("Repost Item Valuation", entry, "status", "Completed", update_modified=False)
		frappe.db.set_value("Warehouse", rejected, "account", None, update_modified=False)
		frappe.flags.pop("warehouse_account_map", None)

	from onedesk.one_ai import proposals, tools
	from onedesk.one_inventory import ai

	with as_user("karim@one.test"):
		facts = tools.read_record("Stock Entry", sent.name)
		assert facts["project"] == sent.project and {(one["item_code"], one["t_warehouse"]) for one in facts["items"]} == {(code, site) for code in ("ALU-6063", "HW-LOCK", "SIL-CLR")}
		found = tools.read_record("Stock Reconciliation", count.name)
		assert flt(found["difference_amount"]) == flt(count.difference_amount) and flt(found["items"][0]["current_qty"]) - flt(found["items"][0]["qty"]) == 3
		card = ai.plan_transfer(site, [{"item": "SEAL-EPDM", "qty": 50}], project=sent.project)
		made = frappe.get_doc("Stock Entry", proposals.apply(card["proposal"])["record"])
		assert made.docstatus == 0 and made.purpose == "Material Transfer" and made.project == sent.project
		assert [(one.item_code, one.qty, one.s_warehouse, one.t_warehouse) for one in made.items] == [("SEAL-EPDM", 50, frappe.get_cached_value("Company", count.company, "default_warehouse"), site)]
		made.delete()
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Stock Entry", "read", doc=sent.name)
		for doctype, name in (("Stock Entry", sent.name), ("Stock Reconciliation", count.name)):
			try:
				tools.read_record(doctype, name)
			except frappe.PermissionError:
				continue
			raise AssertionError(f"somebody outside the stores read {doctype} {name}")


@check
def oneinventory_a_documents_head_says_where_it_stands():
	"""Every stores document Karim opens says what is next in a sentence, and
	one that moves through stages draws them: Al Noor's late order in red with
	its Received step late, a paid order in green with every step done."""
	from onedesk.one import head

	tracked = {"Purchase Order", "Material Request", "Purchase Receipt", "Delivery Note", "Work Order", "Subcontracting Order"}
	with as_user("karim@one.test"):
		for doctype in sorted(tracked | {"BOM", "Asset"}):
			record = frappe.get_doc("Record Head", doctype)
			for name in frappe.get_all(doctype, filters={"docstatus": 1}, pluck="name", limit=20):
				document = frappe.get_doc(doctype, name)
				said = head.said(document, record)
				assert said["sentence"] and said["sentence"]["text"], (doctype, name)
				if doctype in tracked and not document.get("is_return"):
					steps = next((one["steps"] for one in said["band"] if one.get("steps")), None)
					assert steps and all(step["state"] in ("done", "now", "late", "next") for step in steps), (doctype, name, said["band"])
		record = frappe.get_doc("Record Head", "Purchase Order")
		late = frappe.get_all("Purchase Order", filters={"docstatus": 1, "per_received": 0, "status": ["not in", ["Closed", "On Hold"]], "schedule_date": ["<", today()]}, pluck="name")
		assert late
		said = head.said(frappe.get_doc("Purchase Order", late[0]), record)
		assert said["sentence"]["colour"] == "red", said["sentence"]
		assert [step["state"] for step in said["band"][0]["steps"]][:2] == ["done", "late"], said["band"][0]
		paid = frappe.get_all("Purchase Order", filters={"docstatus": 1, "status": "Completed"}, pluck="name")
		finished = [one for one in (head.said(frappe.get_doc("Purchase Order", name), record) for name in paid) if one["sentence"]["colour"] == "green"]
		assert finished and all(step["state"] == "done" for step in finished[0]["band"][0]["steps"]), finished[:1]


@check
def oneinventory_buying_from_request_to_order():
	"""Buying, as Rania, Karim, a supplier on the portal and Huda do it. Rania
	asked for sealant, anchors and gaskets for the villa, Al Noor and Emirates
	Sealants priced them, Emirates Sealants on the portal, and each line went to
	whoever was cheaper on it. Al Noor is late and Karim is told. Al Noor's
	aluminium is agreed for the year, the losing quotes expired, the glass
	orders never made good are closed, and Gulf Glass and Al Noor are scored.
	A request line cannot be ordered twice over on drafts."""
	from onedesk.one_inventory import ai, heads, order, ready, supplier_items, tell

	villa = frappe.db.get_value("Project", {"project_name": "Mansour Villa Windows and Doors"})
	asked = frappe.get_doc("Material Request", {"owner": "rania@one.test", "project": villa, "docstatus": 1, "material_request_type": "Purchase"})
	assert flt(asked.per_ordered) == 100
	rfq = frappe.get_doc("Request for Quotation", frappe.db.get_value("Request for Quotation Item", {"material_request": asked.name}, "parent"))
	assert {one.supplier for one in rfq.suppliers} == {"Al Noor Aluminium", "Emirates Sealants & Fixings"}
	quotes = {one.supplier: frappe.get_doc("Supplier Quotation", one.name) for one in frappe.get_all("Supplier Quotation", filters={"name": ["in", frappe.get_all("Supplier Quotation Item", filters={"request_for_quotation": rfq.name}, pluck="parent")]}, fields=["name", "supplier"])}
	portal = quotes["Emirates Sealants & Fixings"]
	assert frappe.db.exists("Portal User", {"parent": portal.supplier, "user": portal.owner})
	assert {one.project for one in portal.items} == {villa}

	with as_user("karim@one.test"):
		compared = ai.quotes_now(request=asked.name)
	cheapest = {one["item"]: one["cheapest"] for request in compared["compared"] for one in request["lines"]}
	assert cheapest == {"SIL-CLR": "Emirates Sealants & Fixings", "FIX-ANCH": "Al Noor Aluminium", "SEAL-EPDM": "Al Noor Aluminium"}, cheapest
	ordered = {row.item_code: frappe.db.get_value("Purchase Order", row.parent, "supplier") for row in frappe.get_all("Purchase Order Item", filters={"material_request": asked.name, "docstatus": 1}, fields=["item_code", "parent"])}
	assert ordered == {code: frappe.db.get_value("Supplier", {"supplier_name": name}) for code, name in cheapest.items()}
	assert heads.rfq_cheapest(rfq)["value"] == "Split between 2" and heads.rfq_answered(rfq)["value"] == "2 of 2"
	assert heads.quote_cheapest(portal)["value"] == "1 of 3 lines" and heads._request_quotes(asked) == (2, 2)

	late = frappe.get_doc("Purchase Order", frappe.db.get_value("Purchase Order Item", {"material_request": asked.name, "item_code": "FIX-ANCH", "docstatus": 1}, "parent"))
	assert heads.order_said(late)["colour"] == "red"
	named = {one.name for one in tell.late()}
	assert late.name in named
	closed = frappe.get_all("Purchase Order", filters={"status": "Closed"}, pluck="name")
	services = frappe.get_all("Purchase Order Item", filters={"item_code": ["like", "SVC-%"], "docstatus": 1}, pluck="parent")
	assert closed and not named & set(closed) and not named & set(services)
	said = frappe.db.get_value("Notification Log", {"for_user": "karim@one.test", "document_type": "Purchase Order", "document_name": late.name}, "email_content")
	assert said and "Wall Anchor Set" in said, said
	with _Told() as told:
		tell.orders_late()
	assert "karim@one.test" in told.to("Order Late")
	with as_user("karim@one.test"):
		said = ai.still_to_arrive(late_only=True)
	assert late.name in {one["order"] for one in said["orders"]} and all(line["late_by_days"] > 0 for one in said["orders"] for line in one["lines"]), said

	expired = frappe.get_all("Supplier Quotation", filters={"status": "Expired"}, pluck="name")
	assert expired and heads.quote_valid(frappe.get_doc("Supplier Quotation", expired[0]))["tone"] == "quiet"

	agreed = frappe.get_doc("Blanket Order", {"supplier": "Al Noor Aluminium", "docstatus": 1})
	on_it = frappe.get_all("Purchase Order Item", filters={"blanket_order": agreed.name, "docstatus": 1}, fields=["parent", "rate", "qty"])
	assert on_it and all(flt(one.rate) == flt(agreed.items[0].rate) for one in on_it)
	assert flt(agreed.items[0].ordered_qty) == sum(flt(one.qty) for one in on_it)
	assert heads.blanket_ordered(agreed)["meter"]["value"] == flt(agreed.items[0].ordered_qty)
	printed = frappe.get_print("Blanket Order", agreed.name, print_format="One Blanket Order")
	assert "Blanket Order" in printed and "Al Noor Aluminium" in printed

	with as_user("karim@one.test"):
		tab = supplier_items.read("Al Noor Aluminium")
	lines = {one["item"]: one for one in tab["items"]}
	assert lines["ALU-6063"]["agreed"] and lines["ALU-6063"]["orders"], lines.get("ALU-6063")
	assert lines["FIX-ANCH"]["last"]["rate"] > 0 and lines["FIX-ANCH"]["unit"], lines.get("FIX-ANCH")
	assert tab["count"] == len(tab["items"]) and all(one["item_name"] for one in tab["items"])

	glass = frappe.get_doc("Material Request Item", {"item_code": "GLS-DGU", "project": villa, "docstatus": 1, "ordered_qty": 0})
	with as_user("karim@one.test"):
		first = order.order([{"item_code": glass.item_code, "qty": glass.stock_qty, "warehouse": glass.warehouse, "supplier": "Gulf Glass Industries", "material_request": glass.parent, "material_request_item": glass.name, "uom": glass.stock_uom}])
		assert glass.name not in {one.get("material_request_item") for one in order.rows()}
		try:
			order.order([{"item_code": glass.item_code, "qty": 1, "warehouse": glass.warehouse, "supplier": "Al Noor Aluminium", "material_request": glass.parent, "material_request_item": glass.name, "uom": glass.stock_uom}])
			raise AssertionError("a request line was ordered twice over on drafts")
		except frappe.ValidationError as refused:
			assert "left to order" in str(refused)
		frappe.delete_doc("Purchase Order", first[0])

	card = frappe.get_doc("Supplier Scorecard", "Gulf Glass Industries")
	assert frappe.db.count("Supplier Scorecard Period", {"scorecard": card.name, "docstatus": 1}) >= 6
	assert {one.criteria_name for one in card.criteria} == {name for name, _formula in ready.CRITERIA}
	with as_user("karim@one.test"):
		assert {one["key"]: one for one in ready.checks()}["scoring"]["state"] == ready.READY

	with as_user("karim@one.test"):
		assert frappe.has_permission("Blanket Order", "create") and frappe.has_permission("Supplier Scorecard", "write")
		assert ai.plan_quote_request(asked.name, ["Al Noor Aluminium"]).get("error"), "a request ordered already"
		card_ = ai.plan_quote_request(glass.parent, ["Gulf Glass Industries", "Al Noor Aluminium"], message="Prices for the villa's glass, please.")
		changes = frappe.parse_json(frappe.db.get_value("AI Proposal", card_["proposal"], "changes"))
		assert {one["supplier"] for one in changes["suppliers"]} == {"Gulf Glass Industries", "Al Noor Aluminium"}
		assert {(one["item_code"], one["material_request"]) for one in changes["items"]} == {("GLS-DGU", glass.parent)}
	with as_user("rania@one.test"):
		assert frappe.has_permission("Material Request", "create") and frappe.has_permission("Supplier Scorecard", "read")
		assert not frappe.has_permission("Supplier Scorecard", "write") and not frappe.has_permission("Blanket Order", "cancel")
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Blanket Order", "read") and ai.quotes_now(request=asked.name).get("error")


@check
def oneinventory_equipment_bought_given_serviced_and_mended():
	"""Equipment, as Karim, Yousef, Mariam and Huda meet it. Mariam's laptop is
	bought on a receipt that registers it, handed to her and signed for, and
	she is told. Mariam sees what each person holds. The services are kept up
	by whoever does them, one truck's late and told. A truck mended on the
	garage's bill, a laptop waiting for its screen, the CNC centre written
	down after a crash."""
	from onedesk.one_demo import assets as demo
	from onedesk.one_hr import heads as hr_heads
	from onedesk.one_inventory import heads, tell

	laptop = frappe.get_doc("Asset", {"asset_name": "Laptop Mariam"})
	mariam = frappe.db.get_value("Employee", {"user_id": "mariam@one.test"})
	assert laptop.docstatus == 1 and laptop.purchase_receipt and laptop.custodian == mariam
	assert frappe.db.get_value("Purchase Receipt", laptop.purchase_receipt, "owner") == demo.STORES
	given = frappe.get_doc(
		"Asset Movement",
		frappe.db.get_value("Asset Movement Item", {"asset": laptop.name, "to_employee": mariam}, "parent"),
	)
	assert given.purpose == "Issue" and given.owner == demo.STORES and given.docstatus == 1
	assert heads.handed_what(given)["value"] == "Laptop Mariam" and heads.handed_to(given)["value"] == "Mariam Saleh"
	assert frappe.db.exists("Notification Log", {"type": "Equipment Handed Over", "for_user": "mariam@one.test", "document_name": laptop.name})

	printed = frappe.get_print("Asset Movement", given.name, "One Equipment Handover")
	assert "Laptop Mariam" in printed and "Mariam Saleh" in printed and "I have received the equipment above" in printed
	assert "Received By" in printed

	yousef = frappe.get_doc("Employee", {"user_id": "yousef@one.test"})
	with as_user("mariam@one.test"):
		assert frappe.has_permission("Asset", "read") and not frappe.has_permission("Asset", "write")
		assert hr_heads.equipment(yousef)["value"] == "1 held"

	trucks = {name: frappe.db.get_value("Asset", {"asset_name": name}) for name, _late in demo.SERVICED}
	day = getdate(today())
	open_ = {
		one.asset_maintenance: one
		for one in frappe.get_all(
			"Asset Maintenance Log",
			filters={"docstatus": 0, "maintenance_status": ["in", ["Planned", "Overdue"]]},
			fields=["name", "asset_maintenance", "due_date", "maintenance_status", "task_assignee_email"],
		)
	}
	for name, late in demo.SERVICED:
		log = open_[trucks[name]]
		assert log.due_date and (getdate(log.due_date) < day) == late, (name, log)
		assert log.maintenance_status == ("Overdue" if late else "Planned"), (name, log)
		done = frappe.get_all("Asset Maintenance Log", filters={"asset_maintenance": trucks[name], "docstatus": 1}, fields=["owner"])
		assert done and {one.owner for one in done} == {log.task_assignee_email}
	late = frappe.get_doc("Asset Maintenance Log", open_[trucks["Pickup Truck 2"]].name)
	assert heads.service_due(late)["tone"] == "alarm" and heads.service_asset(late)["value"] == "Pickup Truck 2"
	with _Told() as told:
		tell.services()
	assert told.to("Service Late") == {"yousef@one.test", "tariq@one.test"}
	assert told.to("Service Due") <= {"yousef@one.test", "tariq@one.test"}

	plan = frappe.get_doc("Asset Maintenance", trucks["Pickup Truck 1"])
	was = plan.asset_maintenance_tasks[0].next_due_date
	plan.asset_maintenance_tasks[0].next_due_date = None
	with as_user(demo.STORES):
		plan.save()
	assert str(plan.asset_maintenance_tasks[0].next_due_date) == str(was)
	coming = frappe.get_doc("Asset Maintenance Log", open_[trucks["Pickup Truck 1"]].name)
	coming.maintenance_status = "Overdue"
	with as_user("yousef@one.test"):
		coming.save()
	assert coming.maintenance_status == "Planned"

	mended = frappe.get_doc("Asset Repair", {"asset": trucks["Pickup Truck 1"], "docstatus": 1})
	bill = frappe.get_doc("Purchase Invoice", mended.invoices[0].purchase_invoice)
	assert mended.repair_status == "Completed" and flt(mended.total_repair_cost) == 3850 and bill.supplier == demo.GARAGE
	assert heads.repair_out(mended)["value"] == "5 days" and heads.repair_cost(mended)
	waiting = frappe.get_doc("Asset Repair", {"repair_status": "Pending"})
	assert frappe.db.get_value("Asset", waiting.asset, "status") == "Out of Order" and heads.repair_out(waiting)["tone"] == "alarm"

	cut = frappe.get_doc("Asset Value Adjustment", {"docstatus": 1})
	assert flt(cut.new_asset_value) < flt(cut.current_asset_value) and cut.owner == demo.BOOKS
	assert heads.worth_change(cut)["tone"] == "alarm"
	assert frappe.db.exists("Journal Entry", {"name": cut.journal_entry, "docstatus": 1})

	from onedesk.one_ai import proposals, tools
	from onedesk.one_inventory import ai

	with as_user(demo.STORES):
		facts = ai.asset_facts("Pickup Truck 1")
		assert facts["held_by"] == "Sanjay Patel" and facts["repairs"][0]["cost"] == 3850 and facts["next_service"]
		holder = tools.find_records("Employee", "Yousef Bakr")[0]["name"]
		held = tools.list_records("Asset", {"custodian": holder, "docstatus": 1}, fields=["asset_name", "location", "status"])
		assert [one["asset_name"] for one in held] == ["Pickup Truck 2"], held
		due = ai.upkeep_now(days=30)
		assert any(one["asset"] == "Pickup Truck 2" and one["late"] for one in due["services"]), due
		card = ai.plan_handover("Laptop Mariam", "Yousef Bakr", why="Mariam is away for a month")
		drafted = proposals.apply(card["proposal"])
	handover = frappe.get_doc("Asset Movement", drafted["record"])
	assert handover.docstatus == 0 and handover.assets[0].from_employee == mariam and handover.assets[0].to_employee == yousef.name
	handover.delete()
	with as_user("nadia@one.test"):
		assert ai.asset_facts("Pickup Truck 1").get("error")
		try:
			tools.list_records("Asset", {"docstatus": 1})
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("somebody outside the stores listed the equipment")
		assert ai.upkeep_now().get("error") and ai.plan_handover("Laptop Nadia", "Yousef Bakr").get("error")

	with as_user("yousef@one.test"):
		assert frappe.has_permission("Asset Maintenance Log", "submit")
	with as_user(demo.STORES):
		assert frappe.has_permission("Asset Movement", "submit") and frappe.has_permission("Asset Repair", "submit")
	with as_user("nadia@one.test"):
		assert not frappe.has_permission("Asset", "read") and not frappe.has_permission("Asset Repair", "read")


@check
def oneinventory_hand_offs_from_the_other_side():
	"""OneInventory's hand-offs, as the person on the other side meets them.
	Mariam starts Sanjay's leaving checklist herself, and it asks the stores
	for his truck back. Omar's order for Crescent Schools' classrooms says how much has gone out and since when
	it is late. Huda's receipt for the coating says what it cost, and the
	coater's bill arrives by mail as a draft against the order. Yousef's
	services name the pickup they are for."""
	from onedesk.one_crm import heads as crm_heads
	from onedesk.one_demo import assets as demo
	from onedesk.one_inventory import heads

	driver = demo._employee(demo.DRIVER)
	truck = frappe.db.get_value("Asset", {"asset_name": "Pickup Truck 1"})
	separation = frappe.get_doc("Employee Separation", {"employee": driver})
	assert separation.docstatus == 1 and separation.owner == demo.PEOPLE, (separation.docstatus, separation.owner)
	with as_user(demo.PEOPLE):
		assert frappe.has_permission("Employee Separation", "submit") and frappe.has_permission("Employee Onboarding", "submit")
	back = next(row for row in separation.activities if truck in (row.activity_name or ""))
	assert back.task and demo.STORES in frappe.parse_json(frappe.db.get_value("Task", back.task, "_assign") or "[]"), back.task

	order = frappe.get_doc("Sales Order", {"customer": "Crescent Schools", "docstatus": 1})
	assert 0 < order.per_delivered < 100, order.per_delivered
	late = crm_heads.deliver_by(order)
	assert isinstance(late, dict) and late["tone"] == "alarm", late

	receipt = frappe.get_doc("Purchase Receipt", {"supplier": "Gulf Powder Coating", "docstatus": 1, "is_subcontracted": 1})
	assert heads.receipt_worth(receipt) not in (None, frappe.utils.fmt_money(0, currency=receipt.currency)), heads.receipt_worth(receipt)
	bill = frappe.get_doc("Purchase Invoice", {"bill_no": "GPC-2207"})
	assert bill.docstatus == 0 and flt(bill.grand_total) == 1417.5 and bill.project, (bill.docstatus, bill.grand_total, bill.project)
	assert all(row.purchase_order == receipt.items[0].purchase_order for row in bill.items), [row.purchase_order for row in bill.items]
	asked = getdate("2026-11-07")
	assert getdate(bill.due_date) == asked or asked < getdate(bill.posting_date), (bill.due_date, bill.posting_date)

	titles = frappe.get_all("Asset Maintenance Log", filters={"item_code": "VEH-PICKUP"}, pluck="one_asset_title")
	assert set(titles) == {"Pickup Truck 1", "Pickup Truck 2"}, titles


@check
def oneinventory_broken_glass_goes_back_and_the_bill_is_debited():
	"""Broken glass found after Gulf Glass's August bill goes back on the
	receipt, and a debit note takes it off the bill, at the bill's price and
	its VAT, so what Sahara owes falls by exactly that."""
	note = frappe.get_all("Purchase Invoice", filters={"is_return": 1, "docstatus": 1, "supplier": "Gulf Glass Industries"}, fields=["name", "return_against", "grand_total"], limit=1)
	assert note, "no debit note against a bill"
	note = note[0]
	bill = frappe.get_doc("Purchase Invoice", note.return_against)
	returned = frappe.get_doc("Purchase Invoice", note.name)
	for row in returned.items:
		billed = next(one for one in bill.items if one.item_code == row.item_code)
		assert flt(row.rate) == flt(billed.rate), (row.rate, billed.rate)
	assert abs(flt(returned.grand_total) + flt(sum(-r.amount for r in returned.items)) * 1.05) <= CENTS, returned.grand_total
	paid = frappe.db.sql(
		"""select ifnull(sum(allocated_amount), 0) from `tabPayment Entry Reference`
		where reference_doctype = 'Purchase Invoice' and reference_name = %s and docstatus = 1""",
		bill.name,
	)[0][0]
	owed = flt(bill.outstanding_amount) + flt(frappe.db.get_value("Purchase Invoice", note.name, "outstanding_amount"))
	assert abs(owed - (flt(bill.grand_total) + flt(note.grand_total) - flt(paid))) <= CENTS, (owed, bill.grand_total, note.grand_total, paid)
	assert frappe.db.exists("Purchase Receipt", {"is_return": 1, "supplier": "Gulf Glass Industries", "docstatus": 1, "posting_date": [">=", bill.posting_date]})


@check
def oneinventory_the_stock_in_the_books_is_what_the_warehouses_hold():
	"""What the stock is worth in the books is what the warehouses hold, each
	warehouse's account against its stock ledger, and ERPNext's weekly
	recalculation keeps them so (Inventory Check's corrected)."""
	from erpnext.stock import get_warehouse_account_map

	held = {}
	for warehouse, account in get_warehouse_account_map(COMPANY).items():
		if account.get("account"):
			held.setdefault(account["account"], 0.0)
			held[account["account"]] += flt(
				frappe.db.sql(
					"select ifnull(sum(stock_value_difference), 0) from `tabStock Ledger Entry` where warehouse = %s and is_cancelled = 0",
					warehouse,
				)[0][0]
			)
	off = {}
	for account, value in held.items():
		booked = flt(frappe.db.sql("select ifnull(sum(debit - credit), 0) from `tabGL Entry` where account = %s and is_cancelled = 0", account)[0][0])
		if abs(value - booked) > 1:
			off[account] = (round(value, 2), round(booked, 2))
	assert held and not off, off
	from onedesk.one_inventory import ready

	assert {row["key"]: row["state"] for row in ready.checks()}["corrected"] == ready.READY, "stock and the books are put right each week"


@check
def oneinventory_what_was_ordered_is_received_and_billed_price_for_price():
	"""What Karim ordered is what was received and billed, price for price."""
	wrong = []
	for child, link in (("Purchase Receipt Item", "purchase_order_item"), ("Purchase Invoice Item", "po_detail")):
		for row in frappe.db.sql(
			f"""select row.parent, row.item_code, row.rate, src.rate as was from `tab{child}` row
			join `tabPurchase Order Item` src on src.name = row.{link} where row.docstatus = 1 and row.{link} is not null""",
			as_dict=True,
		):
			if abs(flt(row.rate) - flt(row.was)) > CENTS:
				wrong.append((child, row.parent, row.item_code, row.rate, row.was))
	assert not wrong, wrong[:5]


@check
def oneinventory_fixing_the_check_is_an_ability():
	"""Fix What the Check Finds is a Stock Manager's, and an Accounts
	Manager's as it always was; a Stock User's Fix is refused."""
	from onedesk.one_inventory import ready

	assert ready.fixes("karim@one.test") and ready.fixes("huda@one.test")
	assert not ready.fixes("rania@one.test")
	with as_user("rania@one.test"):
		try:
			ready.fix("home")
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("a Stock User fixed what Inventory Check found")


@check
def oneinventory_a_count_is_drafted_and_another_company_keeps_its_stock():
	"""OneAI drafts a count of the Stores from what Karim says he counted,
	beside what the books hold, batch by batch for a batched item, and
	nothing moves until it is submitted.
	Stock kept by a second company, One Dev here, never reaches Sahara's
	Stock Summary, its Home or the count: figures are one company's at a
	time. Somebody who may not count is refused."""
	from onedesk.one_ai import proposals
	from onedesk.one_inventory import ai, home, stock

	with as_user("karim@one.test"):
		before = stock.on_hand()["worth"], home.read()["figures"]["worth"]
		books = flt(frappe.db.get_value("Bin", {"item_code": "SIL-CLR", "warehouse": wh("Stores")}, "actual_qty"))
		card = ai.plan_count(wh("Stores"), [{"item": "SIL-CLR", "qty": books - 2}], why="Month-end count")
		drafted = proposals.apply(card["proposal"])
		assert ai.plan_count(wh("Stores"), [{"item": "SIL-WP", "qty": 10}]).get("error"), "a batched item is counted batch by batch"
		assert ai.plan_count(wh("Stores"), [{"item": "SIL-WP", "qty": 48, "batch": "SIL-WP-A1"}]).get("proposal")
		assert ai.plan_count(wh("Stores"), [{"item": "NOT-AN-ITEM", "qty": 1}]).get("error")
	count = frappe.get_doc("Stock Reconciliation", drafted["record"])
	assert count.docstatus == 0 and count.set_warehouse == wh("Stores") and count.company == COMPANY, count.as_dict()
	line = count.items[0]
	assert (line.item_code, line.qty, line.current_qty) == ("SIL-CLR", books - 2, books), line.as_dict()
	with as_user("nadia@one.test"):
		assert ai.plan_count(wh("Stores"), [{"item": "SIL-CLR", "qty": 1}]).get("error")

	other = frappe.db.get_value("Company", {"name": ["!=", COMPANY]})
	assert other, "the bench has a second company"
	place = frappe.db.get_value("Warehouse", {"company": other, "is_group": 0, "warehouse_name": "Stores"}) or frappe.db.get_value(
		"Warehouse", {"company": other, "is_group": 0}
	)
	receipt = frappe.get_doc(
		{"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": other, "items": [{"item_code": "SIL-CLR", "qty": 10, "basic_rate": 30, "t_warehouse": place}]}
	)
	receipt.insert()
	receipt.submit()
	with as_user("karim@one.test"):
		after = stock.on_hand()
		assert (after["worth"], home.read()["figures"]["worth"]) == before, "another company's stock reached Sahara's figures"
		assert place not in {one["name"] for one in after["warehouses"]}
