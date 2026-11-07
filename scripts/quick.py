"""The guards that can see this change, in parallel: the loop while working.

    python3 scripts/quick.py            # guards that name what changed
    python3 scripts/quick.py --all      # every test, in parallel: the gate

`--all` runs `tests/` and each module's own `tests/` folder (onedesk/<module>/
tests), which need no site; a doctype's test_*.py beside its JSON does, and
is left to bench.

A guard is picked when its source names a changed file's stem, its module's
folder, or its kind of file (a CSS change picks every guard that reads
`.css`). Nothing changed, or a change to a guard or to scripts/, picks them
all. This is for the loop, not the gate: run `--all` once before the commit,
since a guard can read a file it never names.
"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDS = ROOT / "tests" / "guards"
SKIP = ["--deselect", "tests/guards/test_generated.py::test_upstream_was_read_recently"]


def changed() -> list[Path]:
	out = subprocess.run(
		["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, capture_output=True, text=True
	).stdout
	return [Path(line[3:].split(" -> ")[-1].strip('"')) for line in out.splitlines()]


def picked(paths: list[Path]) -> list[Path] | None:
	"""The guard files to run, or None for all of them."""
	if not paths or any(
		path.parts[:2] == ("tests", "guards") or path.parts[0] == "scripts" for path in paths
	):
		return None
	words = set()
	for path in paths:
		words.add(path.stem)
		if path.suffix:
			words.add(path.suffix)
		if len(path.parts) > 2 and path.parts[0] == "onedesk":
			words.add(path.parts[1])
	found = []
	for guard in sorted(GUARDS.glob("test_*.py")):
		source = guard.read_text(encoding="utf-8")
		if any(
			re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", source) for word in words if len(word) > 2
		):
			found.append(guard)
	return found


def main() -> int:
	if "--all" in sys.argv:
		modules = sorted(str(one.relative_to(ROOT)) for one in (ROOT / "onedesk").glob("*/tests") if any(one.glob("test_*.py")))
		return subprocess.call([sys.executable, "-m", "pytest", "-q", "-n", "auto", "tests", *modules, *SKIP], cwd=ROOT)
	paths = changed()
	guards = picked(paths)
	targets = [str(one.relative_to(ROOT)) for one in guards] if guards is not None else ["tests/guards"]
	if guards == []:
		print("no guard names what changed; run --all before the commit")
		return 0
	print(f"{len(paths)} changed, {'all' if guards is None else len(guards)} guard files")
	return subprocess.call([sys.executable, "-m", "pytest", "-q", "-n", "auto", *targets, *SKIP], cwd=ROOT)


if __name__ == "__main__":
	sys.exit(main())
