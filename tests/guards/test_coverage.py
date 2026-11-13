"""Point 1: what a person can do is done in the demo and read back. Every
whitelisted method of ours, and every tool OneAI is given, is reached by a
check in one_demo/check.py, or counted among those still to cover. The count
only falls: a new feature arrives with its check, and a check written lowers
it. These read the code.

A change-mode run (scripts/tree.py) holds the features of the changed files
alone, or all of them when the suite or hooks.py changed, and leaves the
counts' falling to `--all`."""

import ast
import functools
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
sys.path.insert(0, str(ROOT / "scripts"))

import pytest  # noqa: E402
import tree  # noqa: E402

SUITE = tree.suite()

ELSEWHERE = {"one_admin": "the operator's console runs on the admin site"}

STILL = {
	"one": 0,
	"one_ai": 0,
	"one_book": 0,
	"one_calendar": 0,
	"one_crm": 0,
	"one_hr": 0,
	"one_inventory": 0,
	"trust_center": 0,
	"one_mail": 0,
	"one_project": 0,
	"one_cloud": 0,
	"one_studio": 0,
	"one_task": 0,
}


def _whitelisted(paths) -> dict[str, set[str]]:
	found: dict[str, set[str]] = {}
	for path in paths:
		parts = path.relative_to(APP).parts
		if len(parts) < 2 or parts[0] in ("one_demo", "patches") or path.name.startswith("test_"):
			continue
		for node in tree.parsed(path).body:
			if isinstance(node, ast.FunctionDef) and any(
				"whitelist" in ast.unparse(one) for one in node.decorator_list
			):
				found.setdefault(parts[0], set()).add(f"{path.stem}.{node.name}")
	return found


def _tools(judged=lambda _path: True) -> dict[str, set[str]]:
	"""OneAI's tools, as hooks.py names them, by module, of the files
	`judged` keeps."""
	hooks = tree.hooks()
	found: dict[str, set[str]] = {}
	for hook in ("one_ai_reads", "one_ai_suggests"):
		block = hooks.split(f"{hook} = [", 1)[1].split("\n]", 1)[0]
		for path in re.findall(r'"onedesk\.([\w.]+)"', block):
			module, *rest, file, fn = path.split(".")
			if judged(APP.joinpath(module, *rest, f"{file}.py")) or judged(APP.joinpath(module, *rest, file, "__init__.py")):
				found.setdefault(module, set()).add(f"{file}.{fn}")
	return found


@functools.cache
def features(scoped: bool = False) -> dict[str, set[str]]:
	"""Every feature a person reaches, by module: `file.function`; `scoped`,
	only those of the files a change-mode run judges, unless the suite or
	hooks.py is one of them."""
	every = sorted(APP.rglob("*.py"))
	if not scoped or any(tree.judged(path) for path in [*tree.suite_files(), APP / "hooks.py"]):
		found, tools = _whitelisted(every), _tools()
	else:
		found, tools = _whitelisted(tree.scoped(every)), _tools(tree.judged)
	for module, names in tools.items():
		found.setdefault(module, set()).update(names)
	return {module: names for module, names in found.items() if module not in ELSEWHERE}


def reached(name: str) -> bool:
	"""A check calls it, as `file.function(`, or through an alias ending in
	the file's name (`mail_agent.function(` for one_mail/agent.py)."""
	return name in _called()


@functools.cache
def _called() -> frozenset[str]:
	"""Every tail of a dotted name called in the suite that starts after
	something other than a letter or a digit."""
	found = set()
	for called in set(re.findall(r"([\w.]+)\(", SUITE)):
		found.update(called[at:] for at in range(len(called)) if at == 0 or not (called[at - 1].isascii() and called[at - 1].isalnum()))
	return frozenset(found)


def test_no_module_has_more_left_to_cover_than_it_had():
	left = {module: sorted(one for one in names if not reached(one)) for module, names in features(scoped=True).items()}
	over = {module: len(names) for module, names in left.items() if len(names) > STILL.get(module, 0)}
	assert not over, f"each new feature needs its demo check: {over}, was {STILL}"


def test_the_counts_are_lowered_as_checks_are_written():
	"""Whole runs only: a change-mode run sees part of each count."""
	if not tree.whole():
		pytest.skip("the counts fall under --all")
	left = {module: sum(1 for one in names if not reached(one)) for module, names in features().items()}
	stale = {
		module: (STILL[module], left.get(module, 0))
		for module in STILL
		if left.get(module, 0) < STILL[module]
	}
	assert not stale, f"lower STILL to what is left (was, now): {stale}"


def test_the_scan_finds_a_call():
	assert reached("template_view.read") and not reached("template_view.nothing_of_the_kind")
	assert "library.copy" in _whitelisted([APP / "one_project" / "library.py"])["one_project"]
