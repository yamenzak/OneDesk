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
