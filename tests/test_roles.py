"""Nobody on a workspace is given System Manager, so nothing may wait for it.

A gate written as `only_for("System Manager")` is a door with no key: the
person running the workspace holds Workspace Administrator, and the check would
refuse them for ever. The one place the role is still read is the apps screen,
where it hides frappe's own Framework tile from everybody — which is the point.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ROLES = tree.APP / "one" / "roles.py"
HOOKS = tree.APP / "hooks.py"
#: Where reading System Manager is right, and why.
READS_IT = {tree.APP / "one" / "boot.py"}


def _administrator() -> str:
	for node in ast.walk(ast.parse(ROLES.read_text(encoding="utf-8"))):
		if isinstance(node, ast.Assign) and node.targets[0].id == "ADMINISTRATOR":
			return node.value.value
	raise AssertionError("roles.ADMINISTRATOR is gone")


def _code(path: Path) -> str:
	body = ast.parse(path.read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node):
			node.body = node.body[1:]
	return ast.unparse(body)


def test_the_role_is_not_frappes_own():
	"""Frappe ships Workspace Manager, for editing the desk's sidebar pages."""
	assert _administrator() == "Workspace Administrator"


def test_no_code_waits_for_system_manager():
	waiting = [
		path.relative_to(tree.ROOT)
		for path in tree.APP.rglob("*.py")
		if path not in READS_IT and "System Manager" in _code(path)
	]
	assert not waiting, f"{waiting} gate on a role nobody on a workspace holds"


def test_no_screen_waits_for_system_manager():
	waiting = [
		path.relative_to(tree.ROOT)
		for path in (tree.APP / "public" / "js").rglob("*")
		if path.suffix in (".js", ".vue") and "has_role(\"System Manager\")" in path.read_text(encoding="utf-8")
	]
	assert not waiting, f"{waiting} draw a control for a role nobody holds"


def test_what_a_workspace_administers_is_granted_to_its_administrator():
	role = _administrator()
	for doctype in ("ai_action_setting", "ai_action"):
		held = json.loads((tree.APP / "one_ai" / "doctype" / doctype / f"{doctype}.json").read_text())
		assert any(p["role"] == role for p in held["permissions"]), doctype
	account = json.loads(
		(tree.APP / "one" / "doctype" / "workspace_account" / "workspace_account.json").read_text()
	)
	assert any(p["role"] == role for p in account["permissions"])


def test_the_role_exists_before_anything_runs():
	said = HOOKS.read_text(encoding="utf-8")
	for hook in ("after_install", "after_migrate"):
		first = said.split(f"{hook} = [", 1)[1].split(",", 1)[0].strip()
		assert first == '"onedesk.one.roles.ensure"', f"{hook} starts with {first}"
