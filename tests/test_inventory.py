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
	shipped = {json.loads(p.read_text())["name"] for p in erpnext.glob("**/report/*/*.json") if p.parent.name == p.stem}
	assert set(reports) <= shipped, set(reports) - shipped
