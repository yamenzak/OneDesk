"""Reports and dashboards (one/reports.py): a workspace saves Report Builder
reports only, its charts and cards count records or read a report and run no
code, a report by mail runs as whoever set it up, and a saved report goes in
its app's sidebar through frappe's own layers. These read the code that says
so."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "reports.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_guards_are_hooked():
	for method in ("report_kept", "placed", "removed", "chart_kept", "mail_kept"):
		assert f'"onedesk.one.reports.{method}"' in HOOKS, method
	assert '"onedesk.one.reports.settle"' in HOOKS


def test_a_workspace_saves_report_builder_reports_only():
	kept = _body("report_kept")
	assert 'doc.report_type != "Report Builder"' in kept and "frappe.throw" in kept


def test_a_chart_or_card_runs_no_code():
	kept = _body("chart_kept")
	assert 'kind == "Custom"' in kept and "frappe.throw" in kept
	assert 'frappe.has_permission(counted, "read")' in kept


def test_a_report_by_mail_runs_as_whoever_set_it_up():
	assert "doc.user = frappe.session.user" in _body("mail_kept")


def test_a_saved_report_goes_through_frappes_layers():
	placed = _body("placed")
	assert "_layer(module, user)" in placed and "roles.administers(doc.owner)" in placed
	assert 'link_type == "Report" and row.link_to == doc.name' in _body("removed")
	assert "build_entity_module_map" in _body("_module")


def test_a_layers_report_link_is_drawn():
	assert "reports.reported(" in (tree.APP / "one" / "boot.py").read_text()
	assert 'delete_keys("user:*:has_role:Report")' in _body("_redrawn")
