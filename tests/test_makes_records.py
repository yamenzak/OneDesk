"""Every kind of record One's code makes without a name is declared in
hooks.py `one_makes_records`, so Numbering never lets it be named by hand
(one/numbering.py made_by).

The kinds are read the way the audit that wrote the list read them: every
place a module's code builds a record of a frappe, erpnext or hrms kind, by
`frappe.get_doc({"doctype": ...})`, `frappe.new_doc(...)` or a
`{"doctype": ...}` it saves later. A kind with no screen of its own (a child
table, a Single) or in a module Customize refuses is left out, as Numbering
leaves it out. A new insert of a kind not on the list fails here, naming the
file, until the list names it.
"""

import ast
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent / "onedesk"
APPS = Path("/home/frappe/bench1/apps")

#: Modules that ask OneAI for whatever a record they make still needs, its
#: name included (one_intake/fill.py), so any naming holds for them.
FILLS = ("one_intake",)

#: The three ways the app builds a record of a named kind.
MADE = re.compile(r'(?:get_doc\(\s*\{\s*"doctype":\s*"|new_doc\("|"doctype":\s*")([A-Z][A-Za-z ]+)"')


def _declared() -> dict:
	tree = ast.parse((ROOT / "hooks.py").read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and any(
			isinstance(one, ast.Name) and one.id == "one_makes_records" for one in node.targets
		):
			return ast.literal_eval(node.value)
	return {}


def _refused() -> tuple:
	tree = ast.parse((ROOT / "one" / "customize.py").read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and any(
			isinstance(one, ast.Name) and one.id == "REFUSED_MODULES" for one in node.targets
		):
			return ast.literal_eval(node.value)
	return ()


def _upstream() -> dict:
	"""frappe's, erpnext's and hrms's kinds of record, by name."""
	kinds = {}
	for app in ("frappe", "erpnext", "hrms"):
		for path in (APPS / app / app).glob("**/doctype/*/*.json"):
			if path.stem != path.parent.name:
				continue
			try:
				meta = json.loads(path.read_text())
			except ValueError:
				continue
			if meta.get("doctype") == "DocType" and meta.get("name"):
				kinds[meta["name"]] = meta
	return kinds


def _made(upstream: dict) -> dict:
	"""{kind: {module: first file}} for every upstream kind a module's code makes."""
	refused = _refused()
	made = {}
	for path in ROOT.rglob("*.py"):
		parts = path.relative_to(ROOT).parts
		if len(parts) < 2 or parts[0] in ("tests", "patches", *FILLS) or path.name.startswith("test_"):
			continue
		for kind in MADE.findall(path.read_text()):
			meta = upstream.get(kind)
			if not meta or meta.get("istable") or meta.get("issingle") or meta.get("module") in refused:
				continue
			made.setdefault(kind, {}).setdefault(parts[0], str(path.relative_to(ROOT.parent)))
	return made


@pytest.fixture(scope="module")
def upstream():
	if not APPS.exists():
		pytest.skip("frappe, erpnext and hrms are not checked out beside this app")
	return _upstream()


def test_every_kind_made_is_declared(upstream):
	declared = _declared()
	missing = [
		f"{kind} made by {module} ({where})"
		for kind, modules in sorted(_made(upstream).items())
		for module, where in sorted(modules.items())
		if module not in declared.get(kind, [])
	]
	assert not missing, "Add to hooks.py one_makes_records:\n" + "\n".join(missing)


def test_nothing_declared_is_stale(upstream):
	made = _made(upstream)
	stale = [
		f"{kind}: {module}"
		for kind, modules in sorted(_declared().items())
		for module in modules
		if module not in made.get(kind, {})
	]
	assert not stale, "No longer made, so take out of hooks.py one_makes_records:\n" + "\n".join(stale)
