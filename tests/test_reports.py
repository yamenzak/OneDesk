"""Reports and dashboards (one_studio/reports.py): a workspace saves Report Builder
reports only, its charts and cards count records or read a report and run no
code, a report by mail runs as whoever set it up, and a saved report goes in
its app's sidebar through frappe's own layers. The demo checks each; these
read the wiring."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one_studio" / "reports.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_guards_are_hooked():
	for method in ("report_kept", "placed", "removed", "chart_kept", "mail_kept"):
		assert f'"onedesk.one_studio.reports.{method}"' in HOOKS, method
	assert '"onedesk.one.access.settle"' in HOOKS


def test_a_chart_or_card_runs_no_code():
	kept = _body("chart_kept")
	assert 'frappe.has_permission(counted, "read")' in kept


def test_a_saved_report_goes_through_frappes_layers():
	assert "build_entity_module_map" in _body("_module")


def test_a_layers_report_link_is_drawn():
	assert "reports.reported(" in (tree.APP / "one" / "boot.py").read_text()
	assert 'delete_keys("user:*:has_role:Report")' in _body("_redrawn")


def _anchored():
	space = {}
	exec("def anchored(" + _body("anchored"), space)
	return space["anchored"]


def test_a_shipped_row_goes_where_the_app_ships_it():
	anchored = _anchored()
	shipped = ["items", "stock-on-hand", "receipts", "more", "pick", "packing", "trips", "landed"]
	rows = ["items", "receipts", "more", "pick", "landed", "yours", "van", "stock-on-hand", "packing", "trips"]
	named = {"items", "receipts", "more", "pick", "landed", "yours", "van"}
	got = anchored(rows, shipped, named, lambda one: one)
	assert got == ["items", "stock-on-hand", "receipts", "more", "pick", "packing", "trips", "landed", "yours", "van"]
	assert anchored(got[::-1], shipped, set(got), lambda one: one) == got[::-1]


def _pure(name):
	space = {}
	exec(f"def {name}(" + _body(name), space)
	return space[name]


def test_a_layer_nobody_rearranged_follows_the_apps_new_order():
	rebased, untouched = _pure("rebased"), _pure("untouched")
	added = lambda one: one in ("yours", "van")  # noqa: E731
	before = ["items", "buying", "to-order", "orders", "requests", "suppliers", "more", "quotes"]
	rows = ["items", "buying", "to-order", "orders", "blanket", "requests", "suppliers", "more", "quotes", "yours", "van"]
	assert untouched(rows, before, lambda one: one, added)
	assert untouched(rows, None, lambda one: one, added), "a layer older than the kept order"
	now = ["items", "buying", "to-order", "requests", "quotes", "orders", "blanket", "suppliers", "more"]
	assert rebased(rows, now, lambda one: one, added) == [*now, "yours", "van"]
	moved = ["items", "buying", "suppliers", "to-order", "orders", "requests", "more", "quotes", "yours", "van"]
	assert not untouched(moved, before, lambda one: one, added)
	mid = ["items", "mine", "buying", "to-order"]
	assert rebased(mid, ["buying", "to-order", "items"], lambda one: one, lambda one: one == "mine") == ["buying", "to-order", "items", "mine"]
	grouped = ["assets", "asset", "yours", "van", "reports", "upkeep"]
	now = ["assets", "asset", "upkeep", "reports"]
	children = {"asset", "upkeep", "van"}
	assert rebased(grouped, now, lambda one: one, lambda one: one in ("yours", "van"), lambda one: one in children) == [
		"assets", "asset", "upkeep", "yours", "van", "reports"
	]


def test_layers_are_settled_on_migrate():
	assert '"onedesk.one_studio.reports.settle"' in HOOKS
