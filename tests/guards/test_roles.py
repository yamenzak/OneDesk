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
READS_IT = {tree.APP / "one" / "boot.py", tree.APP / "one" / "registry" / "agents.py"}


def administrator(source: str) -> str | None:
	"""roles.py's ADMINISTRATOR, read from its source. Pure."""
	for node in tree.nodes(source):
		if isinstance(node, ast.Assign) and node.targets[0].id == "ADMINISTRATOR":
			return node.value.value
	return None


def _administrator() -> str:
	found = administrator(tree.text(ROLES))
	assert found, "roles.ADMINISTRATOR is gone"
	return found


def code(source: str) -> str:
	"""The source's texts and bytes but its docstrings: the only place a name
	with a space in it can be in code. Pure."""
	walked = tree.nodes(source)
	docs = {
		id(node.body[0].value)
		for node in walked
		if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)) and ast.get_docstring(node)
	}
	return "\n".join(
		str(node.value)
		for node in walked
		if isinstance(node, ast.Constant) and isinstance(node.value, str | bytes) and id(node) not in docs
	)


def waits_in_code(source: str) -> bool:
	"""Whether Python code names System Manager outside its docstrings. Pure."""
	return "System Manager" in code(source)


def waits_on_screen(source: str) -> bool:
	"""Whether a desk script draws a control only System Manager sees. Pure."""
	return 'has_role("System Manager")' in source


def granted(doctype: dict, role: str) -> bool:
	"""Whether a doctype's permissions give `role` a row. Pure."""
	return any(p["role"] == role for p in doctype["permissions"])


def first_hooked(hooks: str, hook: str) -> str:
	"""The first function a hook's list in hooks.py names. Pure."""
	return hooks.split(f"{hook} = [", 1)[1].split(",", 1)[0].strip()


def ungated(source: str) -> list[str]:
	"""The whitelisted functions of operator.py's source that do not call `_may`. Pure."""
	out = []
	for node in ast.parse(source).body:
		if not isinstance(node, ast.FunctionDef):
			continue
		marks = [one.func if isinstance(one, ast.Call) else one for one in node.decorator_list]
		if not any(isinstance(one, ast.Attribute) and one.attr == "whitelist" for one in marks):
			continue
		calls = {one.func.id for one in ast.walk(node) if isinstance(one, ast.Call) and isinstance(one.func, ast.Name)}
		if "_may" not in calls:
			out.append(node.name)
	return out


def hands_out_flow_or_studio(text: str) -> bool:
	"""Whether a file gives frappe's Flow or Studio role. Pure."""
	return '"Flow User"' in text or '"Studio User"' in text


def test_the_role_is_not_frappes_own():
	"""Frappe ships Workspace Manager, for editing the desk's sidebar pages."""
	assert _administrator() == "Workspace Administrator"


def test_no_code_waits_for_system_manager():
	waiting = [
		path.relative_to(tree.ROOT)
		for path in tree.scoped(tree.APP.rglob("*.py"))
		if path not in READS_IT and waits_in_code(tree.text(path))
	]
	assert not waiting, f"{waiting} gate on a role nobody on a workspace holds"


def test_no_screen_waits_for_system_manager():
	waiting = [
		path.relative_to(tree.ROOT)
		for path in tree.scoped((tree.APP / "public" / "js").rglob("*"))
		if path.suffix in (".js", ".vue") and waits_on_screen(path.read_text(encoding="utf-8"))
	]
	assert not waiting, f"{waiting} draw a control for a role nobody holds"


def test_what_a_workspace_administers_is_granted_to_its_administrator():
	role = _administrator()
	for doctype in ("ai_knowledge",):
		held = json.loads((tree.APP / "one_ai" / "doctype" / doctype / f"{doctype}.json").read_text())
		assert granted(held, role), doctype
	account = json.loads(
		(tree.APP / "account_center" / "doctype" / "workspace_account" / "workspace_account.json").read_text()
	)
	assert granted(account, role)


def test_the_role_exists_before_anything_runs():
	said = tree.hooks()
	for hook in ("after_sync", "after_migrate"):
		first = first_hooked(said, hook)
		assert first == '"onedesk.one.roles.ensure"', f"{hook} starts with {first}"


def test_every_operator_verb_is_gated():
	"""Both gates, on every whitelisted method, without exception.

	`_may` is `require_admin` plus `only_for`. A verb that forgot it would be a
	workspace anybody with a desk login could archive.
	"""
	found = ungated((tree.APP / "one_admin" / "operator.py").read_text(encoding="utf-8"))
	assert not found, f"{found} are whitelisted and do not call _may()"


def test_nobody_on_a_workspace_is_given_frappes_flow_or_studio():
	"""frappe's Flow and Studio run code nobody checked and AI on the site's own
	keys (one/atlas.py, FLOW and FRAPPE_STUDIO); they stay off a workspace only
	while none of One's files hands out their roles."""
	given = [
		path.relative_to(tree.APP)
		for path in tree.scoped(tree.APP.rglob("*"))
		if path.suffix in (".py", ".json") and path.is_file() and hands_out_flow_or_studio(path.read_text(encoding="utf-8", errors="ignore"))
	]
	assert not given, given


def test_the_role_rules_catch_their_examples():
	assert administrator('ADMINISTRATOR = "Workspace Manager"\n') == "Workspace Manager"
	assert administrator("OTHER = 1\n") is None
	assert waits_in_code('frappe.only_for("System Manager")\n')
	assert not waits_in_code('def f():\n\t"""Not for System Manager."""\n')
	assert waits_on_screen('if (frappe.user.has_role("System Manager")) {}')
	assert not waits_on_screen('if (frappe.user.has_role("Workspace Administrator")) {}')
	assert not granted({"permissions": [{"role": "System Manager"}]}, "Workspace Administrator")
	assert granted({"permissions": [{"role": "Workspace Administrator"}]}, "Workspace Administrator")
	hooks = 'after_sync = ["onedesk.one.install.run", "onedesk.one.roles.ensure"]\n'
	assert first_hooked(hooks, "after_sync") == '"onedesk.one.install.run"'
	operator = "@frappe.whitelist()\ndef archive(name):\n\tpass\n\n@frappe.whitelist()\ndef keep(name):\n\t_may()\n"
	assert ungated(operator) == ["archive"]
	assert hands_out_flow_or_studio('{"role": "Flow User"}')
	assert not hands_out_flow_or_studio('{"role": "Workspace Administrator"}')
