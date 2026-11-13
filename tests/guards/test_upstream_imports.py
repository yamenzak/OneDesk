"""Point 17: every name One imports from frappe, erpnext or hrms is still
there. ERPNext moves a function now and then (make_customer went from
lead.py to lead/mapper.py), and an import inside a function fails only when
that function runs. These read the code against the bench's checkout."""

import ast
import re
import sys
from functools import cache
from pathlib import Path

import pytest
from tests.bench import APPS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402
UPSTREAM = ("frappe", "erpnext", "hrms")


def _source(module: str) -> Path | None:
	base = APPS / module.split(".")[0] / Path(*module.split("."))
	for path in (base.with_suffix(".py"), base / "__init__.py"):
		if path.exists():
			return path
	return None


def _by_eye(text: str) -> set[str]:
	"""Top-level names read off the text, for files newer than this python."""
	names = {one for pair in re.findall(r"^(?:async def|def|class|type) (\w+)|^(\w+)\s*[:=]", text, flags=re.M) for one in pair if one}
	for imported in re.findall(r"^(?:from \S+ )?import \(?([\w ,.\n]+?)\)?$", text, flags=re.M):
		names |= {part.split(" as ")[-1].strip().split(".")[0] for part in imported.split(",") if part.strip()}
	return names


@cache
def _defines(module: str) -> frozenset[str]:
	"""The names a module defines at its top level, and what it imports with `*`."""
	path = _source(module)
	if not path:
		return frozenset()
	text = path.read_text()
	names = _by_eye(text)
	try:
		body = ast.parse(text).body
	except SyntaxError:
		body = []
	for node in body:
		for inner in ast.walk(node) if isinstance(node, ast.If | ast.Try) else [node]:
			if isinstance(inner, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
				names.add(inner.name)
			elif isinstance(inner, ast.Assign):
				names |= {target.id for target in inner.targets if isinstance(target, ast.Name)}
			elif isinstance(inner, ast.AnnAssign) and isinstance(inner.target, ast.Name):
				names.add(inner.target.id)
			elif isinstance(inner, ast.Import | ast.ImportFrom):
				names |= {(alias.asname or alias.name).split(".")[0] for alias in inner.names}
	for star in re.findall(r"^from (\S+) import \*", text, flags=re.M):
		names |= _defines(star) if _source(star) else {"*"}
	return frozenset(names)


def _imports():
	for path in tree.scoped(sorted((ROOT / "onedesk").rglob("*.py"))):
		for node in tree.walked(path):
			if isinstance(node, ast.ImportFrom) and node.level == 0 and (node.module or "").split(".")[0] in UPSTREAM:
				yield path, node.lineno, node.module, [alias.name for alias in node.names]
			elif isinstance(node, ast.Import):
				for alias in node.names:
					if alias.name.split(".")[0] in UPSTREAM and "." in alias.name:
						yield path, node.lineno, alias.name, []


def test_every_upstream_import_is_still_there():
	if not (APPS / "erpnext").is_dir():
		pytest.skip("no bench checkout here")
	stale = []
	for path, line, module, names in _imports():
		where = f"{path.relative_to(ROOT)}:{line}"
		if not _source(module):
			stale.append(f"{where} {module}")
			continue
		for name in names:
			known = _defines(module)
			if name != "*" and "*" not in known and name not in known and not _source(f"{module}.{name}"):
				stale.append(f"{where} {module}.{name}")
	assert not stale, stale


def test_the_scan_would_catch_a_moved_function():
	if not (APPS / "erpnext").is_dir():
		pytest.skip("no bench checkout here")
	assert "make_customer" in _defines("erpnext.crm.doctype.lead.mapper")
	assert "make_customer" not in _defines("erpnext.crm.doctype.lead.lead")
