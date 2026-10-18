"""A doctype class we put in place of frappe's, erpnext's or hrms's
(override_doctype_class) still takes every argument upstream calls each of its
methods with. Frappe added `template_content` to Notification.send_an_email
and our Rule's two-argument version failed every email notification into the
Error Log, which nothing else noticed."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
APPS = Path("/home/frappe/bench1/apps")


def _overrides() -> dict[str, str]:
	tree = ast.parse((ROOT / "onedesk" / "hooks.py").read_text())
	for node in tree.body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "override_doctype_class":
			return ast.literal_eval(node.value)
	return {}


def _class(path: Path, name: str | None = None) -> ast.ClassDef | None:
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.ClassDef) and (name is None or node.name == name):
			return node
	return None


def _theirs(doctype: str) -> ast.ClassDef | None:
	scrub = doctype.lower().replace(" ", "_")
	for path in APPS.glob(f"*/*/*/doctype/{scrub}/{scrub}.py"):
		if "onedesk" not in path.parts:
			return _class(path)
	return None


def _accepts(fn: ast.FunctionDef) -> tuple[set, bool]:
	args = fn.args
	names = {one.arg for one in args.posonlyargs + args.args + args.kwonlyargs}
	return names, bool(args.vararg or args.kwarg)


def test_an_overridden_doctype_class_takes_what_upstream_passes():
	if not (APPS / "frappe").exists():
		pytest.skip("frappe is not checked out beside this app")
	wrong = []
	for doctype, dotted in _overrides().items():
		module, name = dotted.rsplit(".", 1)
		ours = _class(ROOT / Path(*module.split(".")).with_suffix(".py"), name)
		theirs = _theirs(doctype)
		assert ours is not None, dotted
		if theirs is None:
			continue
		upstream = {fn.name: fn for fn in theirs.body if isinstance(fn, ast.FunctionDef)}
		for fn in ours.body:
			if not isinstance(fn, ast.FunctionDef) or fn.name not in upstream:
				continue
			takes, open_ = _accepts(fn)
			needs, _ = _accepts(upstream[fn.name])
			if not open_ and needs - takes:
				wrong.append(f"{dotted}.{fn.name} does not take {sorted(needs - takes)}")
	assert not wrong, "\n".join(wrong)
