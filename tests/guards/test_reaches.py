"""Two things that reach sites only through steps no test runs: a demo
check reads names from our modules (point 1), and frappe syncs a JSON to a
site only when its `modified` moves (point 8). Each fails here instead of on
a site."""

import ast
import json
import subprocess
import sys
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402

APP = ROOT / "onedesk"
SYNCED = ("doctype", "page", "report", "sidebar", "workspace", "print_format", "notification", "number_card", "dashboard_chart", "module_onboarding", "onboarding_step", "web_form")


@cache
def _top_names(path: Path) -> set[str]:
	names = set()
	for node in tree.parsed(path).body:
		if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
			names.add(node.name)
		elif isinstance(node, ast.Assign | ast.AnnAssign):
			for target in node.targets if isinstance(node, ast.Assign) else [node.target]:
				names |= {one.id for one in ast.walk(target) if isinstance(one, ast.Name)}
		elif isinstance(node, ast.ImportFrom | ast.Import):
			names |= {(one.asname or one.name).split(".")[0] for one in node.names}
	return names


def _module_file(dotted: str) -> Path | None:
	"""A module of ours that is a file, not a package (whose attributes may be
	its submodules)."""
	found = ROOT / (dotted.replace(".", "/") + ".py")
	return found if found.exists() else None


def _aliases(nodes) -> dict[str, Path]:
	found = {}
	for node in nodes:
		if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("onedesk"):
			for one in node.names:
				module = _module_file(f"{node.module}.{one.name}")
				if module:
					found[one.asname or one.name] = module
	return found


def missing_names(source: str) -> list[str]:
	"""Every `alias.NAME` read where alias is one of our modules imported by
	name (`from onedesk.x import mod`, or `as alias`), in the file or the
	function reading it, and NAME is not at that module's top level. An alias
	the function also assigns is a variable, not the module. Pure but for
	reading our files."""
	top = _aliases(tree.syntax(source).body)
	wrong = []
	scopes = [node for node in tree.nodes(source) if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)]
	for scope in scopes:
		inside = tuple(ast.walk(scope))
		aliases = {**top, **_aliases(inside)}
		shadowed = {node.id for node in inside if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
		shadowed |= {arg.arg for node in inside if isinstance(node, ast.arguments) for arg in (*node.args, *node.kwonlyargs)}
		for node in inside:
			if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id in aliases and node.value.id not in shadowed:
				if node.attr not in _top_names(aliases[node.value.id]):
					wrong.append(f"{node.value.id}.{node.attr} (line {node.lineno})")
	return sorted(set(wrong))


def test_a_check_reads_only_names_that_are_there():
	"""Checks run only on a demo site, never under pytest, so a helper moved
	from under one breaks it unseen (P3.6 moved story.MONTHS and home.FEW).
	A change-mode run reads the checks changed or reading a changed module."""
	found = {}
	for path in [*APP.glob("*/checks.py"), APP / "one_demo" / "check.py"]:
		if not tree.judged(path) and not any(tree.judged(one) for one in _aliases(tree.walked(path)).values()):
			continue
		wrong = missing_names(tree.text(path))
		if wrong:
			found[str(path.relative_to(ROOT))] = wrong
	assert not found, f"a check reads a name its module no longer has: {found}"


def test_the_check_names_rule_catches_its_example():
	assert missing_names("from onedesk.one import story\n\ndef c():\n\treturn story.NOWHERE_AT_ALL\n") == ["story.NOWHERE_AT_ALL (line 4)"]


def _git(*args: str) -> str:
	done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
	return done.stdout if done.returncode == 0 else ""


def _synced(path: str) -> bool:
	parts = path.split("/")
	return path.endswith(".json") and parts[0] == "onedesk" and len(parts) >= 4 and (parts[2] in SYNCED or parts[2] == "custom")


def stale(base: str) -> list[str]:
	"""Synced JSON changed since `base` whose `modified` did not move."""
	wrong = []
	for path in _git("diff", "--name-only", "--diff-filter=M", base, "--").split():
		if not _synced(path):
			continue
		try:
			before, after = json.loads(_git("show", f"{base}:{path}") or "null"), json.loads((ROOT / path).read_text())
		except (ValueError, OSError):
			continue
		if unmoved(before, after):
			wrong.append(path)
	return wrong


def unmoved(before, after) -> bool:
	"""Whether a synced JSON changed and kept its `modified`. Pure."""
	return isinstance(before, dict) and isinstance(after, dict) and before.get("modified") == after.get("modified") and before != after


def test_the_modified_rule_catches_its_example():
	before = {"name": "Task", "label": "Task", "modified": "2026-11-01 10:00:00"}
	assert _synced("onedesk/one_task/doctype/task/task.json") and not _synced("onedesk/one_task/manifest.json")
	assert unmoved(before, {**before, "label": "To do"})
	assert not unmoved(before, {**before, "label": "To do", "modified": "2026-11-13 10:00:00"})
	assert not unmoved(before, dict(before))


def test_a_changed_synced_json_moves_its_modified():
	"""frappe syncs a doctype, page, sidebar or report to a site only when its
	`modified` is newer than the site's: the P2 renames changed titles without
	moving it, and sites kept the old words. Compared with where this branch
	left main."""
	base = _git("merge-base", "HEAD", "upstream/main").strip()
	if not base:
		return
	assert not stale(base), f"move `modified` in these, or sites never see the change: {stale(base)}"
