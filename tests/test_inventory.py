"""OneInventory: what the company holds — items, stock, what is bought and
delivered, and the equipment it keeps — on ERPNext's Stock, Buying and Assets."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

INVENTORY = tree.APP / "one_inventory"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
RAIL = json.loads((INVENTORY / "sidebar" / "oneinventory" / "oneinventory.json").read_text())


def _owned(rail):
	return {item.get("link_to") for item in rail["items"] if item.get("is_default_module") and item["type"] == "Link"} - {None}


def test_oneinventory_follows_onebook_in_the_dock():
	dock = [row["link_to"] for row in json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())["items"]]
	assert dock.index("OneInventory") == dock.index("OneBook") + 1


def test_stock_buying_and_assets_are_one_place_and_nothing_is_owned_twice():
	owned = _owned(RAIL)
	assert {"Item", "Purchase Receipt", "Delivery Note", "Stock Entry", "Stock Reconciliation", "Purchase Order", "Asset"} <= owned
	assert "Supplier" not in owned, "a supplier is somebody OneBook pays"
	book = json.loads((tree.APP / "one_book" / "sidebar" / "onebook" / "onebook.json").read_text())
	crm = json.loads((tree.APP / "one_crm" / "sidebar" / "onecrm" / "onecrm.json").read_text())
	assert not owned & _owned(book) and not owned & _owned(crm)
	assert "Sales Order" in _owned(crm), "the order a won deal becomes"


def test_every_report_row_names_a_report_erpnext_ships():
	reports = [item["link_to"] for item in RAIL["items"] if item.get("link_type") == "Report"]
	erpnext = Path("/home/frappe/bench1/apps/erpnext/erpnext")
	if not erpnext.exists():
		return
	shipped = {
		json.loads(p.read_text())["name"]
		for root in (erpnext, tree.APP / "one_inventory")
		for p in root.glob("**/report/*/*.json")
		if p.parent.name == p.stem
	}
	assert set(reports) <= shipped, set(reports) - shipped


def test_the_usual_asset_categories_are_made_only_for_ledgers_the_chart_has():
	import ast

	source = (tree.APP / "one_inventory" / "ready.py").read_text(encoding="utf-8")
	space = {}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "USUAL":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name == "plan":
			exec(ast.unparse(node), space)
	made = space["plan"]({"Electronic Equipment": "Electronic Equipment - ONE", "Software": "Software - ONE"})
	assert made == [("Computers", "Electronic Equipment - ONE", 36), ("Software", "Software - ONE", 36)]


def test_the_inventory_check_opens_setup_and_shares_the_books_checks_page():
	rail = json.loads((tree.APP / "one_inventory" / "sidebar" / "oneinventory" / "oneinventory.json").read_text())
	setup = next(item for item in rail["items"] if item["label"] == "Setup")
	assert (setup["link_type"], setup["link_to"], setup.get("route")) == ("Page", "inventory", "setup")
	# The Home's Setup part opens on the Inventory Check.
	home = (tree.APP / "one_inventory" / "home.py").read_text()
	assert home.index('("setup", _lt("Inventory Check")') < home.index('("setup", _lt("Warehouses")')
	page = (tree.APP / "one_inventory" / "report" / "inventory_check" / "inventory_check.js").read_text()
	assert "onedesk.check.report(" in page
	assert '"/assets/onedesk/js/check.js"' in (tree.APP / "hooks.py").read_text()


def _pure(path, name, **extra):
	import ast

	space = dict(extra)
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name == name:
			exec(ast.unparse(node), space)
	return space[name]


def test_an_item_is_low_when_what_is_there_and_coming_is_at_its_level():
	summary = _pure(tree.APP / "one_inventory" / "item.py", "summary", flt=lambda v: float(v or 0))
	bins = [
		{"warehouse": "Stores", "actual_qty": 15, "reserved_qty": 5, "ordered_qty": 40, "projected_qty": 50, "stock_value": 187.5},
		{"warehouse": "Van", "actual_qty": 10, "projected_qty": 10, "stock_value": 125},
	]
	levels = [
		{"warehouse": "Stores", "warehouse_reorder_level": 20},
		{"warehouse": "Van", "warehouse_reorder_level": 10},
		{"warehouse": "Annex", "warehouse_reorder_level": 5},
	]
	said = summary(bins, levels)
	assert (said["on_hand"], said["free"], said["ordered"], said["value"]) == (25, 20, 40, 312.5)
	assert said["below"] == ["Van", "Annex"], "on order counts; a warehouse with none is at nought"


def test_the_item_page_draws_the_band():
	heads = (tree.APP / "one_inventory" / "heads.py").read_text()
	assert '"doctype": "Item"' in heads and "item.said(name)" in heads


def test_how_many_to_order_is_erpnexts_rule():
	quantity = _pure(tree.APP / "one_inventory" / "order.py", "quantity", flt=lambda v: float(v or 0))
	assert quantity(40, 100, 30) == 100, "the reorder quantity"
	assert quantity(40, 5, 10) == 30, "or back up to the level, if that is more"


def test_a_request_line_is_left_to_order_less_what_orders_and_drafts_hold():
	left = _pure(tree.APP / "one_inventory" / "order.py", "left", flt=lambda v: float(v or 0))
	assert left(600, 0, 0) == 600
	assert left(600, 200, 300) == 100, "what submitted orders took and drafts hold"
	assert left(600, 400, 300) == 0, "never less than nothing"
	assert left(600, None, None) == 600


def test_a_draft_order_cannot_order_a_request_twice_over():
	assert '"onedesk.one_inventory.order.within_requests"' in HOOKS
	order = (tree.APP / "one_inventory" / "order.py").read_text()
	assert "held = drafted(" in order.split("def rows()")[1], "To Order reads the same sums as the order's rule"


def test_an_order_is_made_per_supplier_and_a_row_with_none_needs_one():
	grouped = _pure(tree.APP / "one_inventory" / "order.py", "grouped", flt=lambda v: float(v or 0))
	rows = [
		{"item_code": "Paper", "qty": 50, "supplier": "Gulf"},
		{"item_code": "Brackets", "qty": 100, "supplier": "Gulf"},
		{"item_code": "Gloves", "qty": 24, "supplier": None},
		{"item_code": "Anchors", "qty": 0, "supplier": "Gulf"},
	]
	assert {name: [row["item_code"] for row in lines] for name, lines in grouped(rows).items()} == {"Gulf": ["Paper", "Brackets"]}
	assert list(grouped(rows, "Emirates Hardware")) == ["Gulf", "Emirates Hardware"]


def test_an_item_that_becomes_a_fixed_asset_makes_its_assets_when_bought():
	import ast

	source = (tree.APP / "one_inventory" / "assets.py").read_text(encoding="utf-8")
	space = {}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SERIES":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name == "fixed_item":
			exec(ast.unparse(node), space)

	class Item(dict):
		__getattr__ = dict.get

		def __setattr__(self, key, value):
			self[key] = value

		def get_doc_before_save(self):
			return self.get("_before")

	new = Item(is_fixed_asset=1, asset_naming_series=None, auto_create_assets=0)
	space["fixed_item"](new)
	assert new.auto_create_assets == 1 and new.asset_naming_series == "ACC-ASS-.YYYY.-"
	kept = Item(is_fixed_asset=1, asset_naming_series="X-", auto_create_assets=0, _before=Item(is_fixed_asset=1))
	space["fixed_item"](kept)
	assert kept.auto_create_assets == 0, "somebody turned it off on an item that was already an asset"


def test_a_receipt_registers_the_assets_it_made():
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"on_submit": "onedesk.one_inventory.assets.registered"' in hooks
	assert '"validate": "onedesk.one_inventory.assets.fixed_item"' in hooks
	source = (tree.APP / "one_inventory" / "assets.py").read_text(encoding="utf-8")
	assert 'savepoint("one_asset")' in source and 'rollback(save_point="one_asset")' in source


def test_leaving_asks_for_each_asset_back_once():
	import ast

	source = (tree.APP / "one_inventory" / "custody.py").read_text(encoding="utf-8")
	space = {"_": lambda text: text}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "KEEPER":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name == "returns":
			exec(ast.unparse(node), space)
	held = [{"name": "ACC-ASS-1", "asset_name": "Laptop"}, {"name": "ACC-ASS-2", "asset_name": "Phone"}]
	made = space["returns"](held, {"Return Laptop (ACC-ASS-1)"})
	assert [row["activity_name"] for row in made] == ["Return Phone (ACC-ASS-2)"]
	assert made[0]["role"] == "Stock Manager"


def test_custody_is_wired_to_the_asset_the_employee_and_leaving():
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"before_submit": "onedesk.one_inventory.custody.leaving"' in hooks
	heads = (tree.APP / "one_inventory" / "heads.py").read_text()
	assert "custody.give(doc.name, employee)" in heads and "custody.take_back(doc.name, location)" in heads
	assert "_equipment(doc)" in (tree.APP / "one_hr" / "employee.py").read_text()


def test_a_schedule_with_an_end_date_is_due_until_the_end():
	import ast
	from datetime import date, timedelta

	source = (tree.APP / "one_inventory" / "maintenance.py").read_text(encoding="utf-8")
	space = {
		"getdate": lambda day: day if isinstance(day, date) else date.fromisoformat(day),
		"nowdate": lambda: "2026-09-24",
		"add_days": lambda day, n: day + timedelta(days=n),
		"add_months": lambda day, n: day.replace(year=day.year + (day.month - 1 + n) // 12, month=(day.month - 1 + n) % 12 + 1),
		"add_years": lambda day, n: day.replace(year=day.year + n),
	}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "PERIODS":
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name == "next_due":
			exec(ast.unparse(node), space)
	next_due = space["next_due"]
	assert next_due("Quarterly", date(2026, 7, 1), end=date(2029, 9, 10)) == date(2026, 10, 1)
	assert next_due("Quarterly", date(2026, 7, 1), last=date(2026, 9, 15)) == date(2026, 12, 15)
	assert next_due("Yearly", date(2026, 7, 1), end=date(2027, 1, 1)) is None, "past the end: none"


def test_maintenance_is_on_the_calendar_once():
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"onedesk.one_inventory.calendar.LAYERS"' in hooks
	assert '"Asset Maintenance": {"before_validate": "onedesk.one_inventory.maintenance.due"}' in hooks
	todos = (tree.APP / "one_task" / "calendar.py").read_text()
	assert '["reference_type", "not in", ["Task", "Asset Maintenance"]]' in todos


def test_stock_goes_to_the_stores_unless_there_are_none():
	home = _pure(INVENTORY / "ready.py", "home")

	assert home(["Finished Goods - SGA", "Stores - SGA"]) == "Stores - SGA"
	assert home(["Finished Goods - SGA", "Work In Progress - SGA"]) == "Finished Goods - SGA"
	assert home([]) is None


def test_stock_on_hand_adds_each_item_up_and_puts_what_is_low_or_short_first():
	rows = _pure(INVENTORY / "stock.py", "rows", flt=lambda v: float(v or 0))
	items = {
		"A": {"item_name": "Anchor", "item_group": "Fixings", "stock_uom": "Nos"},
		"B": {"item_name": "Bolt", "item_group": "Fixings", "stock_uom": "Nos"},
		"C": {"item_name": "Clip", "item_group": "Fixings", "stock_uom": "Nos"},
		"D": {"item_name": "Door", "item_group": "Products", "stock_uom": "Nos"},
	}
	bins = [
		{"item_code": "A", "warehouse": "Stores", "actual_qty": 50, "projected_qty": 50, "stock_value": 100},
		{"item_code": "A", "warehouse": "Van", "actual_qty": 5, "projected_qty": 5, "stock_value": 10},
		{"item_code": "B", "warehouse": "Stores", "actual_qty": 4, "projected_qty": 4, "stock_value": 8},
		{"item_code": "C", "warehouse": "Stores", "actual_qty": 0, "projected_qty": 0},
		{"item_code": "D", "warehouse": "Stores", "actual_qty": 2, "reserved_qty": 5, "projected_qty": -3, "stock_value": 900},
		{"item_code": "Z", "warehouse": "Stores", "actual_qty": 9},
	]
	said = rows(bins, [{"parent": "B", "warehouse": "Stores", "warehouse_reorder_level": 10}], items)
	assert [one["item"] for one in said] == ["B", "D", "A"], "low first, then short, an empty item and one the reader may not see left out"
	anchor = said[-1]
	assert (anchor["on_hand"], anchor["worth"], anchor["places"]) == (55, 110, 2)
	assert said[0]["low_in"] == ["Stores"] and said[1]["free"] == -3


def test_home_tells_its_story_through_frappe():
	"""Home's Overview reads every figure through frappe.get_list, so permissions
	and record access hold, and draws with frappe-ui's charts alone."""
	story = (INVENTORY / "story.py").read_text(encoding="utf-8")
	assert "frappe.db.sql" not in story and "frappe.qb" not in story
	assert "@frappe.read_only()" in story and "stock_ageing import execute" in story
	page = (tree.APP.parent / "frontend" / "src" / "home" / "InventoryStory.vue").read_text(encoding="utf-8")
	assert 'from "frappe-ui/charts"' in page
	for chart in ("AreaChart", "BarChart", "DonutChart", "FunnelChart", "HeatmapChart", "SankeyChart", "ScatterChart"):
		assert f"<{chart}" in page, chart
	home = (tree.APP.parent / "frontend" / "src" / "home" / "InventoryHome.vue").read_text(encoding="utf-8")
	assert "<NumberCard" in home and "sparkline" in home
