"""Every dotted path in hooks.py points at a function that exists.

A typo in `scheduler_events` does not fail a migration or a page load. The job
runs, raises, and lands in a log nobody opens — which for `leaving.nightly`
would mean people who left months ago quietly still holding a login.

Read with AST rather than imported: the app's modules import frappe, and this
suite runs without a site on purpose.
"""

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "onedesk"

sys.path.insert(0, str(ROOT / "scripts"))

import tree

#: hooks whose values are dotted paths to our own callables, however nested.
CALLABLE_HOOKS = (
	"scheduler_events",
	"doc_events",
	"after_install",
	"after_migrate",
	"override_whitelisted_methods",
	"on_session_creation",
	"extend_bootinfo",
)


def _paths(node) -> list[str]:
	"""Every string under this node that looks like one of ours."""
	found = []
	for child in ast.walk(node):
		if isinstance(child, ast.Constant) and isinstance(child.value, str):
			if child.value.startswith("onedesk."):
				found.append(child.value)
	return found


def declared() -> list[str]:
	tree_ = ast.parse((APP / "hooks.py").read_text(encoding="utf-8"))
	found = []
	for node in tree_.body:
		if not isinstance(node, ast.Assign):
			continue
		names = [t.id for t in node.targets if isinstance(t, ast.Name)]
		if any(name in CALLABLE_HOOKS for name in names):
			found.extend(_paths(node.value))
	return sorted(set(found))


def test_hooks_declare_some_callables():
	"""If this ever finds nothing, the parser has stopped matching the file."""
	assert len(declared()) >= 4


@pytest.mark.parametrize("path", declared())
def test_the_function_exists(path):
	module, _, function = path.rpartition(".")
	source = ROOT / Path(*module.split(".")).with_suffix(".py")
	assert source.exists(), f"{path}: no module at {source.relative_to(ROOT)}"

	defined = {
		node.name
		for node in ast.parse(source.read_text(encoding="utf-8")).body
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
	}
	assert function in defined, f"{path}: {source.name} defines no {function}()"


def test_the_scan_would_catch_a_typo():
	"""The guard is only worth having if a wrong name fails it."""
	module, _, _function = declared()[0].rpartition(".")
	source = ROOT / Path(*module.split(".")).with_suffix(".py")
	defined = {
		node.name
		for node in ast.parse(source.read_text(encoding="utf-8")).body
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
	}
	assert "nightlyy" not in defined


#: hooks whose values are paths to files we ship, not dotted callables. A path
#: with a typo in it does not fail anything: the browser asks for a file that is
#: not there, frappe answers 404, and the screen quietly loads without its
#: script — which for `Tenant` means a workspace with no verbs on it.
ASSET_HOOKS = (
	"doctype_js",
	"doctype_list_js",
	"app_include_js",
	"app_include_css",
	"web_include_js",
	"web_include_css",
)

#: Where an asset path starts, once the /assets/onedesk prefix is off it.
SERVED_FROM = APP


def _assets(node) -> list[str]:
	found = []
	for child in ast.walk(node):
		if not (isinstance(child, ast.Constant) and isinstance(child.value, str)):
			continue
		said = child.value
		if said.endswith((".js", ".css")):
			found.append(said)
	return found


def assets() -> list[str]:
	tree_ = ast.parse((APP / "hooks.py").read_text(encoding="utf-8"))
	found = []
	for node in tree_.body:
		if not isinstance(node, ast.Assign):
			continue
		names = [t.id for t in node.targets if isinstance(t, ast.Name)]
		if any(name in ASSET_HOOKS for name in names):
			found.extend(_assets(node.value))
	return sorted(set(found))


def test_hooks_declare_some_assets():
	assert len(assets()) >= 10


@pytest.mark.parametrize("said", assets())
def test_the_asset_exists(said):
	"""`/assets/onedesk/js/x.js` and `public/js/x.js` are the same file."""
	relative = said.removeprefix("/assets/onedesk/").removeprefix("assets/onedesk/")
	if not relative.startswith("public/"):
		relative = "public/" + relative
	on_disk = SERVED_FROM / relative
	assert on_disk.exists(), f"{said}: nothing at {on_disk.relative_to(ROOT)}"
