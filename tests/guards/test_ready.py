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


def test_every_help_page_is_listed_and_every_link_lands():
	"""Help shows a module's pages in the order ready.MODULES gives, so every
	page of its docs/ is listed there, and a version's Read More names only
	pages that are."""
	for module, spec in ready.MODULES.items():
		listed = [page for page, _icon in spec.get("help", ())]
		pages = sorted(path.stem for path in (ROOT / "onedesk" / spec["folder"] / "docs").glob("*.md"))
		assert sorted(listed) == pages, f"{module}'s help lists {sorted(listed)}, its docs/ has {pages}"
		for one in ready.versions(module):
			stray = [page for page in one["docs"] if page not in listed]
			assert not stray, f"{module} {one['version']} reads more in {stray}, which is no help page"


CODE = re.compile(r"`[^`]*(?:\.(?:py|js|vue|css|json)\b|[a-z_]+\.[a-z_]+\b|\b[a-z]+_[a-z_]+\b)[^`]*`")


def test_a_help_page_names_no_code():
	"""Help is read by the people using the module, so a page names what they
	see and never the file or function behind it; AGENTS.md keeps those.
	An address, a keyboard key or a search word in backticks is fine."""
	for module, spec in ready.MODULES.items():
		for path in sorted((ROOT / "onedesk" / spec["folder"] / "docs").glob("*.md")):
			for number, line in enumerate(path.read_text().splitlines(), 1):
				for found in CODE.findall(line):
					if "@" in found or "{" in found:
						continue
					raise AssertionError(f"{path.relative_to(ROOT)}:{number} names code {found}; say it plainly and keep the name in AGENTS.md")


LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def test_a_help_page_is_headed_pictured_and_linked_soundly():
	"""Help is read in sections, so each heading is five words or fewer like
	any other (docs/WORDING.md); a picture it shows sits beside it, and a link
	to another page opens one that Help lists."""
	for module, spec in ready.MODULES.items():
		listed = {page for page, _icon in spec.get("help", ())}
		for page in ready.help_pages(module):
			where = f"{module} {page['id']}"
			assert 0 < len(page["title"].split()) <= 5, f"{where}: the title is five words or fewer"
			for line in page["body"].splitlines():
				if line.startswith("#"):
					assert len(line.lstrip("# ").split()) <= 5, f"{where}: {line} is more than five words"
			for picture in PICTURE.findall(page["body"]):
				assert (page["path"].parent / picture).exists(), f"{where}: no {picture}"
			for target in LINK.findall(page["body"]):
				assert "://" in target or target.split("#")[0] in listed, f"{where} links to {target}, which is no help page"


def test_a_module_has_one_settings_dialog_and_one_foot():
	"""Every module's settings are drawn by onedesk.module_settings and its
	foot by windowModuleFoot (docs/READY.md, mechanism 5), so they look and
	behave alike: the mark and Help atop the settings, tabs left out by role,
	and Settings, Help and the version at the foot."""
	for module, spec in ready.MODULES.items():
		code = {path: path.read_text(encoding="utf-8") for path in ready.files(module) if path.suffix in (".js", ".vue")}
		own = [str(path.relative_to(ROOT)) for path, text in code.items() if "new frappe.ui.SettingsDialog" in text]
		assert not own, f"{module} draws its own settings dialog in {own}; use onedesk.module_settings.open"
		loose = [str(path.relative_to(ROOT)) for path, text in code.items() if "windowFootAction(" in text]
		assert not loose, f"{module} draws its own foot in {loose}; use windowModuleFoot"
		assert any("onedesk.module_settings.open(" in text for text in code.values()), f"{module} has no settings dialog"
		assert any("windowModuleFoot(" in text for text in code.values()), f"{module} has no foot"


AGREEMENTS = re.compile(r"\bagree|\bpolicy\b|\bterms\b|\baddendum\b|\bsubprocessors?\b", re.I)


def test_a_change_to_what_a_module_agrees_on_is_said():
	"""A version records what its module adds to the agreements (one_legal
	`stamp`), so changing a clause or a company it sends data to is a new
	version, and that version tells the people using it which agreement moved
	(docs/READY.md, mechanism 6)."""
	for module, spec in ready.MODULES.items():
		found = ready.versions(module)
		assert found[0].get("legal") == ready.legal(module), (
			f"{module} changed what it adds to the agreements since {found[0]['version']}: "
			f'python3 scripts/version.py {spec["folder"]} <major|minor|fix> "<title>", and say what changed'
		)
		for newer, older in zip(found, found[1:]):
			if "legal" in older and newer.get("legal") != older["legal"]:
				assert AGREEMENTS.search(newer["body"]), f"{module} {newer['version']} changes the agreements without saying which"


def _declared(path: Path) -> dict:
	"""A module's abilities.py read without importing it: its top-level
	names that are plain values."""
	import ast

	found = {}
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
			try:
				found[node.targets[0].id] = ast.literal_eval(node.value)
			except ValueError:
				found[node.targets[0].id] = node.value
	return found


def test_a_module_ships_its_roles():
	"""A module's roles come from its own abilities.py (docs/READY.md,
	mechanism 7): named by the one_abilities hook, its DEFAULTS give every
	role it ships a value for each ability and are what migrate makes the
	roles from, and its Help shows them ({roles}), so the page says what
	ships."""
	hooks = (ROOT / "onedesk" / "hooks.py").read_text(encoding="utf-8")
	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "abilities.py"
		assert path.exists(), f"{module} ships no roles: write {path.relative_to(ROOT)}"
		assert f'"onedesk.{spec["folder"]}.abilities"' in hooks, f"one_abilities in hooks.py doesn't name {module}'s"
		said = _declared(path)
		assert said.get("APP") == module, f"{module}'s abilities.py says APP = {said.get('APP')}"
		abilities = said["ABILITIES"]
		keys = set()
		for one in getattr(abilities, "elts", []):
			for key, value in zip(one.keys, one.values):
				if getattr(key, "value", None) == "key":
					keys.add(value.value)
		assert keys, f"{module} declares no abilities"
		defaults = said.get("DEFAULTS") or {}
		assert said.get("EVERYONE") in defaults, f"{module}'s DEFAULTS don't name the role everyone holds"
		for role, values in defaults.items():
			assert set(values) <= keys, f"{module}'s {role} names abilities it doesn't declare: {set(values) - keys}"
		pages = [page["body"] for page in ready.help_pages(module)]
		assert any("{roles}" in body for body in pages), f"{module}'s Help doesn't show what its roles start with ({{roles}})"
	fixtures = (ROOT / "onedesk" / "fixtures").glob("role.json")
	assert not list(fixtures), "a module's roles are made from its abilities.py, not a fixture"


SHARES = re.compile(
	r"frappe\.share\.(?:add|add_docshare|remove|set_permission)\b|\badd_docshare\(|new_doc\(\s*[\"']DocShare|[\"']doctype[\"']\s*:\s*[\"']DocShare"
)


def test_a_module_grants_through_abilities_alone():
	"""One person given more on one record than their role says is one idea:
	abilities.grant, a share frappe answers (docs/READY.md, mechanism 7). A
	module writes no share of its own."""
	for module in ready.MODULES:
		for path in ready.files(module):
			if path.suffix == ".py" and "tests" not in path.parts:
				hit = SHARES.search(path.read_text(encoding="utf-8"))
				assert not hit, f"{path.relative_to(ROOT)} writes a share itself ({hit.group(0)}); use abilities.grant"


def test_a_module_says_how_and_from_whom_it_tells_people():
	"""Every kind of notification a ready module sends names each channel,
	on or why not, and its sender, system or workspace (docs/READY.md,
	mechanism 8), in place of the email, push and from_one flags. Its
	subject fits the bell's line, and its Help lists what it sends
	({notifications})."""
	import runpy

	layout = runpy.run_path(str(ROOT / "onedesk" / "notifications" / "layout.py"))
	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "notifications.py"
		assert path.exists(), f"{module} says nothing of what it sends: write {path.relative_to(ROOT)}, TYPES = [] if it sends nothing"
		types = runpy.run_path(str(path))["TYPES"]
		for one in types:
			where = f"{module} {one['name']}"
			channels = one.get("channels") or {}
			assert tuple(channels) == layout["CHANNELS"] or set(channels) == set(layout["CHANNELS"]), f"{where} names its channels {sorted(channels)}, not {layout['CHANNELS']}"
			for channel, said in channels.items():
				assert said is True or (isinstance(said, str) and said.endswith(".")), f"{where}: {channel} is True or a sentence saying why not"
			assert one.get("sender") in layout["SENDERS"], f"{where}'s sender is one of {layout['SENDERS']}"
			loose = {"email", "push", "from_one"} & set(one)
			assert not loose, f"{where} says {sorted(loose)}; its channels and sender say that"
			line = re.sub(r"\{\w+\}", "x" * 20, one["subject"])
			assert len(line) <= layout["BELL_LINE"], f"{where}'s subject is longer than the bell's line"
		if types:
			pages = [page["body"] for page in ready.help_pages(module)]
			assert any("{notifications}" in body for body in pages), f"{module}'s Help doesn't list what it sends ({{notifications}})"


def test_a_module_says_what_setting_it_up_takes():
	"""A ready module declares its setup steps in its own setup.py
	(docs/READY.md, mechanism 9): each with a key, a title, what it is for,
	the ability it needs and the settings tab that does it; one with fields
	saves them, and one that can't be left for later is rare enough to be
	said."""
	import ast

	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "setup.py"
		assert path.exists(), f"{module} says nothing of setting it up: write {path.relative_to(ROOT)}, STEPS = [] if it needs nothing"
		tree = ast.parse(path.read_text(encoding="utf-8"))
		steps = next(node.value for node in tree.body if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "STEPS")
		code = "\n".join(p.read_text(encoding="utf-8") for p in ready.files(module) if p.suffix == ".js")
		for step in steps.elts:
			keys = {key.value: value for key, value in zip(step.keys, step.values)}
			where = f"{module} {getattr(keys.get('key'), 'value', '?')}"
			assert {"key", "title", "about", "needs", "tab"} <= set(keys), f"{where} lacks {sorted({'key', 'title', 'about', 'needs', 'tab'} - set(keys))}"
			assert f'id: "{keys["tab"].value}"' in code, f"{where} names a tab, {keys['tab'].value}, its settings don't have"
			if "fields" in keys:
				assert "save" in keys, f"{where} has fields and nothing saves them"
