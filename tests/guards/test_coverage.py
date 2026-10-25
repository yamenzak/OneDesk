"""Point 1: what a person can do is done in the demo and read back. Every
whitelisted method of ours, and every tool OneAI is given, is reached by a
check in one_demo/check.py, or counted among those still to cover. The count
only falls: a new feature arrives with its check, and a check written lowers
it. These read the code."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
SUITE = (APP / "one_demo" / "check.py").read_text()

ELSEWHERE = {"one_admin": "the operator's console runs on the admin site"}

STILL = {
	"one": 0,
	"one_ai": 0,
	"one_book": 0,
	"one_calendar": 0,
	"one_crm": 0,
	"one_hr": 0,
	"one_intake": 0,
	"one_inventory": 0,
	"one_legal": 0,
	"one_mail": 0,
	"one_project": 0,
	"one_storage": 0,
	"one_studio": 0,
	"one_task": 0,
}


def _whitelisted() -> dict[str, set[str]]:
	found: dict[str, set[str]] = {}
	for path in sorted(APP.rglob("*.py")):
		parts = path.relative_to(APP).parts
		if len(parts) < 2 or parts[0] in ("one_demo", "patches") or path.name.startswith("test_"):
			continue
		for node in ast.parse(path.read_text()).body:
			if isinstance(node, ast.FunctionDef) and any(
				"whitelist" in ast.unparse(one) for one in node.decorator_list
			):
				found.setdefault(parts[0], set()).add(f"{path.stem}.{node.name}")
	return found


def _tools() -> dict[str, set[str]]:
	"""OneAI's tools, as hooks.py names them, by module."""
	hooks = (APP / "hooks.py").read_text()
	found: dict[str, set[str]] = {}
	for hook in ("one_ai_reads", "one_ai_suggests"):
		block = hooks.split(f"{hook} = [", 1)[1].split("\n]", 1)[0]
		for path in re.findall(r'"onedesk\.([\w.]+)"', block):
			module, *_rest, file, fn = path.split(".")
			found.setdefault(module, set()).add(f"{file}.{fn}")
	return found


def features() -> dict[str, set[str]]:
	"""Every feature a person reaches, by module: `file.function`."""
	found = _whitelisted()
	for module, names in _tools().items():
		found.setdefault(module, set()).update(names)
	return {module: names for module, names in found.items() if module not in ELSEWHERE}


def reached(name: str) -> bool:
	"""A check calls it, as `file.function(`, or through an alias ending in
	the file's name (`mail_ai.function(` for one_mail/ai.py)."""
	return re.search(rf"(?<![A-Za-z0-9]){re.escape(name)}\(", SUITE) is not None


def test_no_module_has_more_left_to_cover_than_it_had():
	left = {module: sorted(one for one in names if not reached(one)) for module, names in features().items()}
	over = {module: len(names) for module, names in left.items() if len(names) > STILL.get(module, 0)}
	assert not over, f"each new feature needs its demo check: {over}, was {STILL}"


def test_the_counts_are_lowered_as_checks_are_written():
	left = {module: sum(1 for one in names if not reached(one)) for module, names in features().items()}
	stale = {
		module: (STILL[module], left.get(module, 0))
		for module in STILL
		if left.get(module, 0) < STILL[module]
	}
	assert not stale, f"lower STILL to what is left (was, now): {stale}"


def test_the_scan_finds_a_call():
	assert reached("template_view.read") and not reached("template_view.nothing_of_the_kind")
	assert "library.copy" in features()["one_project"]
