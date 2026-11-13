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

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

ROLES = tree.APP / "one" / "roles.py"
READS_IT = {tree.APP / "one" / "boot.py"}


def _administrator() -> str:
	for node in tree.walked(ROLES):
		if isinstance(node, ast.Assign) and node.targets[0].id == "ADMINISTRATOR":
			return node.value.value
	raise AssertionError("roles.ADMINISTRATOR is gone")


def _code(path: Path) -> str:
	"""The file's texts and bytes but its docstrings: the only place a name
	with a space in it can be in code."""
	docs = {
		id(node.body[0].value)
		for node in tree.walked(path)
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node)
	}
	return "\n".join(
		str(node.value)
		for node in tree.walked(path)
		if isinstance(node, ast.Constant) and isinstance(node.value, str | bytes) and id(node) not in docs
	)


def test_the_role_is_not_frappes_own():
	"""Frappe ships Workspace Manager, for editing the desk's sidebar pages."""
	assert _administrator() == "Workspace Administrator"


def test_no_code_waits_for_system_manager():
	waiting = [
		path.relative_to(tree.ROOT)
		for path in tree.scoped(tree.APP.rglob("*.py"))
		if path not in READS_IT and "System Manager" in _code(path)
	]
	assert not waiting, f"{waiting} gate on a role nobody on a workspace holds"


def test_no_screen_waits_for_system_manager():
	waiting = [
		path.relative_to(tree.ROOT)
		for path in tree.scoped((tree.APP / "public" / "js").rglob("*"))
		if path.suffix in (".js", ".vue") and 'has_role("System Manager")' in path.read_text(encoding="utf-8")
	]
	assert not waiting, f"{waiting} draw a control for a role nobody holds"


def test_what_a_workspace_administers_is_granted_to_its_administrator():
	role = _administrator()
	for doctype in ("ai_knowledge",):
		held = json.loads((tree.APP / "one_ai" / "doctype" / doctype / f"{doctype}.json").read_text())
		assert any(p["role"] == role for p in held["permissions"]), doctype
	account = json.loads(
		(tree.APP / "account_center" / "doctype" / "workspace_account" / "workspace_account.json").read_text()
	)
	assert any(p["role"] == role for p in account["permissions"])


def test_the_role_exists_before_anything_runs():
	said = tree.hooks()
	for hook in ("after_sync", "after_migrate"):
		first = said.split(f"{hook} = [", 1)[1].split(",", 1)[0].strip()
		assert first == '"onedesk.one.roles.ensure"', f"{hook} starts with {first}"


def test_every_operator_verb_is_gated():
	"""Both gates, on every whitelisted method, without exception.

	`_may` is `require_admin` plus `only_for`. A verb that forgot it would be a
	workspace anybody with a desk login could archive.
	"""
	source = (tree.APP / "one_admin" / "operator.py").read_text(encoding="utf-8")
	for node in ast.parse(source).body:
		if not isinstance(node, ast.FunctionDef):
			continue
		whitelisted = any(
			isinstance(one, ast.Attribute) and one.attr == "whitelist" for one in node.decorator_list
		)
		if not whitelisted:
			continue
		calls = {
			one.func.id
			for one in ast.walk(node)
			if isinstance(one, ast.Call) and isinstance(one.func, ast.Name)
		}
		assert "_may" in calls, f"{node.name} is whitelisted and does not call _may()"


def test_nobody_on_a_workspace_is_given_frappes_flow_or_studio():
	"""frappe's Flow and Studio run code nobody checked and AI on the site's own
	keys (one/atlas.py, FLOW and FRAPPE_STUDIO); they stay off a workspace only
	while none of One's files hands out their roles."""
	given = [
		path.relative_to(tree.APP)
		for path in tree.scoped(tree.APP.rglob("*"))
		if path.suffix in (".py", ".json")
		and path.is_file()
		and ('"Flow User"' in (text := path.read_text(encoding="utf-8", errors="ignore")) or '"Studio User"' in text)
	]
	assert not given, given
