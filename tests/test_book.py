"""OneBook: the money — invoices, bills, payments, the bank and the reports —
on ERPNext's own accounting."""

import ast
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

BOOK = tree.APP / "one_book"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")
READY = BOOK / "ready.py"
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


def test_every_report_row_names_a_report_erpnext_or_onebook_ships():
	reports = [item["link_to"] for item in RAIL["items"] if item.get("link_type") == "Report"]
	erpnext = Path("/home/frappe/bench1/apps/erpnext/erpnext")
	if not erpnext.exists():
		return
	shipped = {
		json.loads(p.read_text())["name"]
		for root in (erpnext, BOOK)
		for p in root.glob("**/report/*/*.json")
		if p.parent.name == p.stem
	}
	assert set(reports) <= shipped, set(reports) - shipped


def _load(path: Path, names: tuple, **extra) -> dict:
	space = {
		"getdate": lambda day: day,
		"add_days": lambda day, n: day + timedelta(days=n),
		"add_years": lambda day, n: day.replace(year=day.year + n),
		**extra,
	}
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def _body(path: Path, name: str) -> str:
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} not in {path.name}")


def test_a_missing_fiscal_year_follows_the_last_and_covers_today():
	covering = _load(READY, ("covering",))["covering"]
	assert covering(None, date(2026, 9, 23)) == (date(2026, 1, 1), date(2026, 12, 31))
	assert covering(date(2025, 12, 31), date(2026, 9, 23)) == (date(2026, 1, 1), date(2026, 12, 31))
	# An April year, and a gap of two years: the one holding today, not the next.
	assert covering(date(2025, 3, 31), date(2026, 9, 23)) == (date(2026, 4, 1), date(2027, 3, 31))
	assert covering(date(2023, 12, 31), date(2026, 9, 23)) == (date(2026, 1, 1), date(2026, 12, 31))


def test_a_company_bank_account_wires_the_bank_modes_of_payment():
	assert '"Bank Account": {"on_update": "onedesk.one_book.ready.wired"}' in HOOKS
	assert "wire(" in _body(READY, "wired")
	assert "only_for(FIXERS)" in _body(READY, "fix")


def test_the_books_check_opens_the_setup_group():
	setup = [item["label"] for item in RAIL["items"]]
	at = setup.index("Setup")
	assert RAIL["items"][at + 1]["link_to"] == "Books Check"
