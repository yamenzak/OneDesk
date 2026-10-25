"""A module on its way to ready keeps to its folder (docs/READY.md, A
module's folder): every file of it is in one of its places, and nothing
outside them is named for it unless onedesk/one/ready.py says why."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from onedesk.one import ready  # noqa: E402


def _tracked() -> list[str]:
	return subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()


def test_nothing_of_a_module_is_left_outside():
	left = {module: files for module, files in ready.OUTSIDE.items() if files}
	assert not left, f"move these into the module's places, then empty OUTSIDE: {left}"


def test_nothing_outside_a_module_is_named_for_it():
	tracked = _tracked()
	stray = []
	for module, spec in ready.MODULES.items():
		inside = [str(place.relative_to(ROOT)) + "/" for place in ready.places(module)]
		for path in tracked:
			named = any(name in path.lower() for name in spec["names"])
			if named and not path.startswith(tuple(inside)) and path not in ready.SHARED:
				stray.append(f"  {module}: {path}")
	assert not stray, "Move it into the module's places, or say in ready.SHARED why it is shared:\n" + "\n".join(stray)


WRITTEN = {"AGENTS.md", "SCRATCHPAD.md"}


def test_a_module_writes_only_agents_scratchpad_and_docs():
	"""A module on its way to ready holds AGENTS.md, SCRATCHPAD.md and docs/
	and no other Markdown (docs/READY.md, A module's folder)."""
	stray = []
	for spec in ready.MODULES.values():
		folder = ROOT / "onedesk" / spec["folder"]
		assert (folder / "AGENTS.md").exists() and (folder / "SCRATCHPAD.md").exists(), spec["folder"]
		for path in folder.rglob("*.md"):
			inside = path.relative_to(folder)
			if inside.parts[0] != "docs" and str(inside) not in WRITTEN:
				stray.append(str(path.relative_to(ROOT)))
	assert not stray, f"no other Markdown in a module: {stray}"
