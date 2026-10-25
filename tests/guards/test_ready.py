"""A module on its way to ready keeps to its folder (docs/READY.md, A
module's folder): every file of it is in one of its places, and nothing
outside them is named for it unless onedesk/one/ready.py says why."""

import re
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


TECHNICAL = re.compile(
	r"`|\.py\b|\.js\b|\.vue\b|\bcommit\b|\bfunction\b|\bendpoint\b|\bAPI\b|\bdoctype\b|\bfrappe\b|\berpnext\b|\bhooks?\b",
	re.I,
)
PICTURE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def test_every_change_to_a_module_is_a_version():
	"""The newest version's fingerprint is the module's, so nothing it ships
	changes without a new version (docs/READY.md, Versions and What's New)."""
	for module, spec in ready.MODULES.items():
		found = ready.versions(module)
		assert found, f"{module} has no version: python3 scripts/version.py {spec['folder']} major {module}"
		newest = found[0]
		assert newest["fingerprint"] == ready.fingerprint(module), (
			f"{module} changed since {newest['version']}: "
			f'python3 scripts/version.py {spec["folder"]} <major|minor|fix> "<title>", and say what changed'
		)


def test_versions_follow_one_another():
	for module in ready.MODULES:
		found = list(reversed(ready.versions(module)))
		assert found[0]["version"] == "1.0.0", f"{module} starts at 1.0.0"
		for before, after in zip(found, found[1:]):
			major, minor, fix = ready.number(before["version"])
			expected = {
				"major": (major + 1, 0, 0),
				"minor": (major, minor + 1, 0),
				"fix": (major, minor, fix + 1),
			}[after["kind"]]
			assert ready.number(after["version"]) == expected, f"{module} {after['version']} is no {after['kind']} after {before['version']}"


def test_a_version_is_written_for_the_people_using_it():
	"""In English, for the people who use the module: what they can do now and
	what changed for them, never a file, a function or a commit. A title is a
	heading; a picture sits beside the entry."""
	import datetime

	for module in ready.MODULES:
		for one in ready.versions(module):
			where = f"{module} {one['version']}"
			assert one["kind"] in ready.KINDS, where
			datetime.date.fromisoformat(one["date"])
			assert 0 < len(one["title"].split()) <= 5, f"{where}: a title is five words or fewer"
			body = one["body"]
			assert body and "Say here what people can do now" not in body, f"{where} says nothing yet"
			hit = TECHNICAL.search(body)
			assert not hit, f"{where} reads like a commit: …{body[max(hit.start() - 30, 0) : hit.end() + 30]}…"
			for picture in PICTURE.findall(body):
				assert (one["path"].parent / picture).exists(), f"{where}: no {picture}"
