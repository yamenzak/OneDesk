"""The workspace layer is held (one/layer.py, one/customize.py, docs/SHELL.md
decision 6).

These fail when a condition a workspace writes could run rather than compare,
when a workspace could add a field that runs or change what guards a field,
and when Reset could take back more than the workspace made.
"""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

LAYER = tree.APP / "one" / "layer.py"
CUSTOMIZE = (tree.APP / "one" / "customize.py").read_text(encoding="utf-8")
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _layer(*names):
	space = {"re": re}
	for node in ast.parse(LAYER.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in (
			"KINDS",
			"PROPERTIES",
			"_TOKEN",
		):
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_a_condition_compares_and_never_runs():
	plain = _layer("plain")["plain"]
	for said in (
		"",
		"customer",
		"eval:doc.docstatus == 1",
		"eval:doc.status != 'Closed' && doc.grand_total > 1000",
		"eval:!doc.is_return",
		"eval:(doc.a == 1 || doc.b == 'x') && doc.c",
		'eval:doc.kind === "Service"',
	):
		assert plain(said), said
	for said in (
		"eval:frappe.call('x')",
		"eval:doc.name.toUpperCase()",
		"eval:doc.x()",
		"eval:window.location = 'x'",
		"eval:alert(1)",
		"eval:doc['name']",
		"eval:doc.a = 1",
		"eval:`${doc.a}`",
		"eval:'a\\' + alert(1) + \\''",
		"eval:",
		"customer.name",
		"eval:fetch('/api')",
	):
		assert not plain(said), said


def test_a_workspace_adds_only_fields_a_person_types():
	space = _layer()
	kinds = set(space["KINDS"])
	assert not kinds & {
		"HTML",
		"Button",
		"Code",
		"Table",
		"Table MultiSelect",
		"Read Only",
		"Password",
		"Dynamic Link",
	}
	assert {"Data", "Link", "Select", "Check", "Date", "Currency", "Section Break", "Column Break"} <= kinds
	properties = set(space["PROPERTIES"])
	assert not properties & {
		"permlevel",
		"ignore_user_permissions",
		"options",
		"fieldtype",
		"fetch_from",
		"is_virtual",
	}


def test_the_holds_are_on_frappes_own_records():
	for doctype, path in (
		("Custom Field", "onedesk.one.layer.custom_field"),
		("Property Setter", "onedesk.one.layer.property_setter"),
		("Client Script", "onedesk.one.layer.script"),
		("Server Script", "onedesk.one.layer.script"),
	):
		assert f'"{doctype}": {{"validate": "{path}"}}' in HOOKS, doctype
	# Everything the page writes is the workspace's, whoever presses Save.
	assert "frappe.flags.one_workspace_layer = True" in CUSTOMIZE
	assert "System Manager" not in LAYER.read_text(encoding="utf-8").split('"""', 2)[2]


def test_the_page_checks_everything_before_it_writes():
	body = CUSTOMIZE.split("def save(", 1)[1].split("\ndef ", 1)[0]
	assert body.index("_check(doctype, values)") < body.index("_fields(doctype"), (
		"a field alters the table, which commits"
	)
	assert "TimestampMismatchError" in body, "a save against a state somebody changed is refused"
	assert "roles.require()" in CUSTOMIZE.split("def may(", 1)[1].split("\ndef ", 1)[0]


def test_reset_takes_back_only_what_the_workspace_made():
	body = CUSTOMIZE.split("def reset(", 1)[1].split("\n@frappe", 1)[0]
	assert '_ledger(doctype, "Custom Field")' in body and '_ledger(doctype, "Property Setter")' in body
	assert '"custom": 1' in body, "a connection or button of a module's stays"
	# Nothing is taken by what it looks like: a property setter of a module's
	# has no mark of its own, so only the ledger says which are the workspace's.
	assert 'frappe.db.delete("Property Setter", {"doc_type"' not in CUSTOMIZE


def test_a_migrate_keeps_the_workspaces_rows():
	head = (tree.APP / "one" / "head.py").read_text(encoding="utf-8")
	write = head.split("def _write(", 1)[1]
	assert "kept = {table: [row for row in doc.get(table) if row.custom]" in write
