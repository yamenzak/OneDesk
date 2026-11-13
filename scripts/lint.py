"""OneLint: One's standard, checked (docs/run/RUN.md, OneLint). Plain, a
change runs what can see it: the guards naming it, its module's tests and the
tests naming its folder, and a guard that judges each file on its own reads
only the changed ones (scripts/tree.py, scoped). `--all` runs everything,
the gate; `--list` and
`--point N` show the rules by the point of docs/STANDARD.md they serve
(tests/guards/registry.py, where every test in tests/guards is a rule or the
proof that one catches its example)."""

import os
import re
import subprocess
import sys
from pathlib import Path

import tree

ROOT = Path(__file__).resolve().parents[1]
GUARDS = ROOT / "tests" / "guards"
SKIP = ["--deselect", "tests/guards/test_generated.py::test_upstream_was_read_recently"]
EVERYTHING = (("tests", "guards"), ("scripts",), ("onedesk", "one", "registry"), ("upstream.json",))
"""A change under one of these, or to a module's manifest (which the registry
reads), can move any rule, so it runs them all."""


def changed() -> list[Path]:
	out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, capture_output=True, text=True).stdout
	return [Path(line[3:].split(" -> ")[-1].strip('"')) for line in out.splitlines()]


def _mentions(path: Path, words: set[str]) -> bool:
	source = path.read_text(encoding="utf-8")
	return any(re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", source) for word in words if len(word) > 2)


def picked(paths: list[Path]) -> list[Path] | None:
	"""The test files to run for these changes, or None for all of them."""
	if not paths or any(path.parts[: len(prefix)] == prefix for path in paths for prefix in EVERYTHING) or any(path.name == "manifest.py" for path in paths):
		return None
	words, folders = set(), set()
	for path in paths:
		words.add(path.stem)
		if path.suffix:
			words.add(path.suffix)
		if len(path.parts) > 2 and path.parts[0] == "onedesk":
			words.add(path.parts[1])
			folders.add(path.parts[1])
	found = [guard for guard in sorted(GUARDS.glob("test_*.py")) if _mentions(guard, words)]
	for folder in sorted(folders):
		found += sorted((ROOT / "onedesk" / folder / "tests").glob("test_*.py"))
		found += [test for test in sorted((ROOT / "tests").glob("test_*.py")) if _mentions(test, {folder})]
	return list(dict.fromkeys(found))


def everything() -> list[str]:
	modules = sorted(str(one.relative_to(ROOT)) for one in (ROOT / "onedesk").glob("*/tests") if any(one.glob("test_*.py")))
	return ["tests", *modules]


def rules(point: int | None = None) -> str:
	"""The standard's points (docs/STANDARD.md) and the rules holding each,
	grouped as the standard groups them."""
	sys.path.insert(0, str(ROOT))
	from onedesk.one import standard
	from tests.guards.registry import GUARDS

	lines = []
	for group in standard.GROUPS:
		shown = [one for one in standard.POINTS.values() if one.group == group and point in (None, one.number)]
		if shown and point is None:
			lines.append(group)
		for one in shown:
			said = ", ".join(word for word, on in (("before live", one.live), ("a look", bool(one.look))) if on)
			lines.append(f"{one.number}. {one.title}" + (f"  ({said})" if said else ""))
			lines += [f"   {guard.id}: {guard.what}  ({guard.runs})" for guard in GUARDS if guard.point == one.number]
			if one.look:
				lines.append(f"   look: {one.look}")
	return "\n".join(lines)


def pytest(targets: list[str], env: dict[str, str] | None = None) -> int:
	"""Run the targets; `env` names the changed files for a change-mode run
	(scripts/tree.py, scoped), which a whole run never has."""
	given = {key: value for key, value in os.environ.items() if key != tree.CHANGED}
	return subprocess.call([sys.executable, "-m", "pytest", "-q", "-n", "auto", "--dist", "loadfile", *targets, *SKIP], cwd=ROOT, env={**given, **(env or {})})


def main(argv: list[str]) -> int:
	if "--list" in argv:
		print(rules())
		return 0
	if "--point" in argv:
		print(rules(int(argv[argv.index("--point") + 1])))
		return 0
	if "--all" in argv:
		return pytest(everything())
	paths = changed()
	found = picked(paths)
	if found == []:
		print("nothing here can see what changed; run --all before the commit")
		return 0
	if found is None:
		print(f"{len(paths)} changed, everything")
		return pytest(everything())
	print(f"{len(paths)} changed, {len(found)} test files, each file judged on its own only where it changed")
	return pytest([str(one.relative_to(ROOT)) for one in found], {tree.CHANGED: os.pathsep.join(str(one) for one in paths)})


if __name__ == "__main__":
	sys.exit(main(sys.argv[1:]))
