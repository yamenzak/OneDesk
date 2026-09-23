"""OneBook: the money — invoices, bills, payments, the bank and the reports —
on ERPNext's own accounting."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

BOOK = tree.APP / "one_book"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
RAIL = json.loads((BOOK / "sidebar" / "onebook" / "onebook.json").read_text())


def _items(rail=RAIL):
	return {item["label"]: item for item in rail["items"]}


def test_onebook_is_in_the_dock_instead_of_erpnexts_accounts():
	dock = json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())
	links = [row["link_to"] for row in dock["items"]]
	assert "OneBook" in links and "Accounts" not in links


def test_the_money_is_onebooks_and_the_customer_onecrms():
	items = _items()
	owned = {item["link_to"] for item in RAIL["items"] if item.get("is_default_module") and item["type"] == "Link"}
	assert {"Sales Invoice", "Purchase Invoice", "Payment Entry", "Journal Entry", "Supplier"} <= owned
	assert not items["Customers"]["is_default_module"], "customers are OneCRM's"
	assert "is_return" in items["Invoices"]["filters"] and "is_return" in items["Credit Notes"]["filters"]


def test_every_report_row_names_a_report_erpnext_ships():
	reports = [item["link_to"] for item in RAIL["items"] if item.get("link_type") == "Report"]
	erpnext = Path("/home/frappe/bench1/apps/erpnext/erpnext")
	if not erpnext.exists():
		return
	shipped = {json.loads(p.read_text())["name"] for p in erpnext.glob("**/report/*/*.json") if p.parent.name == p.stem}
	assert set(reports) <= shipped, set(reports) - shipped
