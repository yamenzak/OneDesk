"""Point 20: a helper every module needs has one home, and a module calls it
rather than keeping its own copy (docs/run/RUN.md, P3.6). The reader's
company is one/company.py's, a read check one/rights.py's `can`, a token's
hash frappe's `sha256_hash`, and the plain `_lt` of a pure file
one/registry/model.py's. These read the code."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402
APP = ROOT / "onedesk"
COMPANY = APP / "one" / "company.py"
LT = APP / "one" / "registry" / "model.py"


def _body(node: ast.FunctionDef) -> list:
	return [
		one
		for one in node.body
		if not (isinstance(one, ast.Expr) and isinstance(one.value, ast.Constant))
		and not isinstance(one, (ast.Import, ast.ImportFrom))
	]


def _returned(node: ast.FunctionDef):
	body = _body(node)
	return body[0].value if len(body) == 1 and isinstance(body[0], ast.Return) else None


def _called(value, name: str) -> bool:
	return isinstance(value, ast.Call) and (
		(isinstance(value.func, ast.Name) and value.func.id == name)
		or (isinstance(value.func, ast.Attribute) and value.func.attr == name)
	)


def _default_company(node, value) -> bool:
	return _called(value, "get_default_company")


def _read_check(node, value) -> bool:
	if not (_called(value, "bool") and len(value.args) == 1 and _called(value.args[0], "has_permission")):
		return False
	asked = value.args[0]
	return len(asked.args) == 2 and not asked.keywords and isinstance(asked.args[1], ast.Constant) and asked.args[1].value == "read"


def _sha256(node, value) -> bool:
	if not (_called(value, "hexdigest") and isinstance(value.func, ast.Attribute)):
		return False
	made = value.func.value
	return (
		_called(made, "sha256")
		and len(made.args) == 1
		and _called(made.args[0], "encode")
		and not made.args[0].args
	)


def _plain_lt(node, value) -> bool:
	return (
		node.name == "_lt"
		and len(node.args.args) == 1
		and isinstance(value, ast.Name)
		and value.id == node.args.args[0].arg
	)


RULES = {
	"returns erpnext.get_default_company(): use one/company.py's reader_company": (_default_company, COMPANY),
	'returns bool(frappe.has_permission(x, "read")): use one/rights.py\'s can': (_read_check, APP / "one" / "rights.py"),
	"returns the sha256 hexdigest of one string: use frappe.utils.sha256_hash": (_sha256, None),
	"defines a plain _lt: import it from one/registry/model.py": (_plain_lt, LT),
}


def copies(source: str, path: Path | None = None) -> list[str]:
	"""Every function in `source` that keeps its own copy of a shared helper."""
	found = []
	for node in tree.nodes(source):
		if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			continue
		value = _returned(node)
		if value is None:
			continue
		for said, (rule, home) in RULES.items():
			if (home is None or path != home) and rule(node, value):
				found.append(f"{node.name} (line {node.lineno}) {said}")
	return found


def _ours():
	return [path for path in sorted(APP.rglob("*.py")) if "node_modules" not in path.parts]


def test_a_shared_helper_is_not_copied():
	found = [f"{path.relative_to(ROOT)}: {one}" for path in _ours() for one in copies(tree.text(path), path)]
	assert not found, found


def test_the_default_company_is_asked_of_one_place():
	"""One function names the reader's company, so the day it changes (a
	company switch, several companies) it changes once."""
	elsewhere = [
		str(path.relative_to(ROOT))
		for path in _ours()
		if path != COMPANY and "get_default_company" in tree.text(path)
	]
	assert not elsewhere, elsewhere


def test_each_rule_catches_its_own_example():
	examples = {
		"get_default_company": "import erpnext\n\ndef _company():\n\treturn erpnext.get_default_company()\n",
		"lazy get_default_company": 'def company():\n\t"""The reader\'s."""\n\tfrom erpnext import get_default_company\n\n\treturn get_default_company()\n',
		"has_permission": 'import frappe\n\ndef _may(doctype):\n\treturn bool(frappe.has_permission(doctype, "read"))\n',
		"sha256": "import hashlib\n\ndef _hash(token):\n\treturn hashlib.sha256(token.encode()).hexdigest()\n",
		"sha256 or empty": 'import hashlib\n\ndef hashed(value):\n\treturn hashlib.sha256((value or "").encode()).hexdigest()\n',
		"_lt": "def _lt(text: str) -> str:\n\treturn text\n",
	}
	for name, source in examples.items():
		assert copies(source), name
	kept = (
		'def can(doctype, ptype="read"):\n\treturn bool(frappe.has_permission(doctype, ptype))\n'
		'def may(doc):\n\treturn bool(frappe.has_permission("Task", "read", doc=doc))\n'
		"def key(sid):\n\treturn hashlib.sha256(sid.encode()).hexdigest()[:16]\n"
		'def label(text):\n\treturn _lt(text)\n'
	)
	assert not copies(kept), copies(kept)
	assert not copies(COMPANY.read_text(encoding="utf-8"), COMPANY)
