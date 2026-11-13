"""Every dotted path in hooks.py points at a function that exists, and every
asset it names is on disk.

A typo in `scheduler_events` does not fail a migration or a page load. The job
runs, raises, and lands in a log nobody opens — which for `leaving.nightly`
would mean people who left months ago quietly still holding a login.

Read with AST rather than imported: the app's modules import frappe, and this
suite runs without a site on purpose. One test per kind, failing with the
whole list of what is missing.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"

sys.path.insert(0, str(ROOT / "scripts"))

import tree

from onedesk.one import registry
from onedesk.one.registry import hooks as registry_hooks

CALLABLE_HOOKS = (
	"scheduler_events",
	"doc_events",
	"after_sync",
	"after_migrate",
	"override_whitelisted_methods",
	"on_session_creation",
	"extend_bootinfo",
)

ASSET_HOOKS = (
	"doctype_js",
	"doctype_list_js",
	"app_include_js",
	"app_include_css",
	"web_include_js",
	"web_include_css",
)


def _strings(hooks: tuple[str, ...], keep) -> list[str]:
	found = []
	for node in ast.parse(tree.hooks()).body:
		if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in hooks for t in node.targets):
			found += [
				child.value
				for child in ast.walk(node.value)
				if isinstance(child, ast.Constant) and isinstance(child.value, str) and keep(child.value)
			]
	return sorted(set(found))


def declared() -> list[str]:
	found = _strings(CALLABLE_HOOKS, lambda said: said.startswith("onedesk."))
	return sorted(set(found) | set(registry_hooks.settles(install=True)))


def assets() -> list[str]:
	return _strings(ASSET_HOOKS, lambda said: said.endswith((".js", ".css")))


def _named(path: str) -> tuple[str, str, Path]:
	"""A hook's dotted path as frappe reads it, its function and its file."""
	for old, now in registry.moved().items():
		path = path.replace(f"onedesk.{old}.", f"{now}.")
	module, _, function = path.rpartition(".")
	return path, function, ROOT / Path(*module.split(".")).with_suffix(".py")


def missing_function(path: str) -> str | None:
	path, function, source = _named(path)
	if not source.exists():
		return f"{path}: no module at {source.relative_to(ROOT)}"
	defined = {
		node.name
		for node in tree.parsed(source).body
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
	}
	return None if function in defined else f"{path}: {source.name} defines no {function}()"


def missing_asset(said: str) -> str | None:
	"""`/assets/onedesk/js/x.js` and `public/js/x.js` are the same file."""
	relative = said.removeprefix("/assets/onedesk/").removeprefix("assets/onedesk/")
	if not relative.startswith("public/"):
		relative = "public/" + relative
	return None if (APP / relative).exists() else f"{said}: nothing at onedesk/{relative}"


def test_every_function_a_hook_names_exists():
	paths = declared()
	assert len(paths) >= 4, "the parser has stopped matching hooks.py"
	if not tree.judged(APP / "hooks.py"):
		paths = [one for one in paths if tree.judged(_named(one)[2])]
	gone = [said for said in map(missing_function, paths) if said]
	assert not gone, "\n".join(gone)


def test_every_asset_a_hook_names_exists():
	named = assets()
	assert len(named) >= 10, "the parser has stopped matching hooks.py"
	gone = [said for said in map(missing_asset, named) if said]
	assert not gone, "\n".join(gone)


def test_the_scans_would_catch_a_typo():
	"""Each kind fails on a wrong name."""
	assert missing_function(declared()[0] + "y")
	assert missing_function("onedesk.nowhere.at_all")
	assert missing_asset("/assets/onedesk/js/nowhere.js")
	assert missing_asset(assets()[0] + ".gone.js")


def twice(source: str) -> dict[str, list[str]]:
	"""Each hook table of the source that names a key twice, with the keys. Pure."""
	out = {}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict):
			keys = [key.value for key in node.value.keys if isinstance(key, ast.Constant)]
			doubled = sorted({key for key in keys if keys.count(key) > 1})
			if doubled:
				out[node.targets[0].id] = doubled
	return out


def test_no_hook_table_names_a_doctype_twice():
	doubled = twice(tree.hooks())
	assert not doubled, "; ".join(f"{table} names {keys} twice" for table, keys in doubled.items())


def test_the_twice_rule_catches_its_example():
	assert twice('doc_events = {"Note": {}, "Task": {}, "Note": {}}') == {"doc_events": ["Note"]}
	assert twice('doctype_js = {"Note": "a.js", "Task": "b.js"}') == {}
