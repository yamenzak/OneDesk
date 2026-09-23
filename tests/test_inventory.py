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
	labels = [item["label"] for item in rail["items"]]
	assert rail["items"][labels.index("Setup") + 1]["link_to"] == "Inventory Check"
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
	assert '"Item": "public/js/item.js"' in (tree.APP / "hooks.py").read_text()
	assert "onedesk.one_inventory.item.said" in (tree.APP / "public" / "js" / "item.js").read_text()


def test_how_many_to_order_is_erpnexts_rule():
	quantity = _pure(tree.APP / "one_inventory" / "order.py", "quantity", flt=lambda v: float(v or 0))
	assert quantity(40, 100, 30) == 100, "the reorder quantity"
	assert quantity(40, 5, 10) == 30, "or back up to the level, if that is more"


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


def test_a_row_on_a_draft_order_is_off_the_list():
	source = (tree.APP / "one_inventory" / "order.py").read_text(encoding="utf-8")
	assert "doc.docstatus = 0" in source and "on_draft" in source


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
	assert '"Item": {"validate": "onedesk.one_inventory.assets.fixed_item"}' in hooks
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
	assert '"Asset": "public/js/asset.js"' in hooks
	assert "_equipment(doc)" in (tree.APP / "one_hr" / "employee.py").read_text()


def test_a_schedule_with_an_end_date_is_due_until_the_end():
	from datetime import date, timedelta

	import ast

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
	assert '"Asset Maintenance": {"validate": "onedesk.one_inventory.maintenance.due"}' in hooks
	todos = (tree.APP / "one_task" / "calendar.py").read_text()
	assert '["reference_type", "not in", ["Task", "Asset Maintenance"]]' in todos
