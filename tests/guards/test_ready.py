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


# How the next version is written: before production 1.0.0 is brought up to
# date, from it a version is added (docs/READY.md, Before production).
NEXT = '<major|minor|fix> "<title>"' if ready.PRODUCTION else "release"


def test_every_change_to_a_module_is_a_version():
	"""The newest version's fingerprint is the module's, so nothing it ships
	changes without a new version (docs/READY.md, Versions and What's New)."""
	for module, spec in ready.MODULES.items():
		found = ready.versions(module)
		assert found, f"{module} has no version: python3 scripts/version.py {spec['folder']} major {module}"
		newest = found[0]
		assert newest["fingerprint"] == ready.fingerprint(module), (
			f"{module} changed since {newest['version']}: "
			f'python3 scripts/version.py {spec["folder"]} {NEXT}, and say what changed'
		)


def test_before_production_every_module_is_at_1_0_0():
	"""Until One is declared ready for production, a module has one version,
	1.0.0, brought up to date as it changes; and One is declared ready only
	when every module is (docs/READY.md, Before production)."""
	if ready.PRODUCTION:
		left = [module for module, spec in ready.MODULES.items() if not spec.get("ready")]
		assert not left, f"One is declared ready for production, but these modules aren't: {left}"
		return
	for module, spec in ready.MODULES.items():
		found = [one["version"] for one in ready.versions(module)]
		assert found == ["1.0.0"], f"{module} is at {found}; before production it stays at 1.0.0: python3 scripts/version.py {spec['folder']} release"


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
			f'python3 scripts/version.py {spec["folder"]} {NEXT}, and say what changed'
		)
		for newer, older in zip(found, found[1:]):
			if "legal" in older and newer.get("legal") != older["legal"]:
				assert AGREEMENTS.search(newer["body"]), f"{module} {newer['version']} changes the agreements without saying which"
				assert newer["kind"] != "fix", f"{module} {newer['version']} changes the agreements, so it is at least a minor (docs/READY.md, Which number moves)"


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
	subject fits the bell's line."""
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


# What only AccessCenter and NotificationCenter draw (docs/READY.md,
# mechanisms 14 and 15): the role matrix and a person's notification choices.
CENTERS = {
	"AccessCenter": re.compile(r"onedesk\.roles\.(?:draw|pick|create|edit)\(|role_matrix\.js"),
	"NotificationCenter": re.compile(r"notification_center\.(?:choose|set_type)|email_notification_types|one_allow_(?:email|push)"),
}


def test_a_module_leaves_roles_and_notifications_to_their_centers():
	"""Who may do what and how people hear of things are found from what a
	module declares, and drawn once (docs/READY.md, mechanisms 14 and 15):
	a ready module's screens draw neither, and ControlCenter offers both."""
	for module in ready.MODULES:
		for path in ready.files(module):
			if path.suffix not in (".js", ".vue"):
				continue
			text = path.read_text(encoding="utf-8")
			for center, drawn in CENTERS.items():
				hit = drawn.search(text)
				assert not hit, f"{path.relative_to(ROOT)} draws what {center} shows ({hit.group(0)}); ControlCenter opens {center}"
	kit = (ROOT / "onedesk" / "public" / "js" / "module_settings.js").read_text(encoding="utf-8")
	assert "onedesk.access.open({ module })" in kit and "onedesk.notification_center.open({ module })" in kit, (
		"ControlCenter no longer offers AccessCenter and NotificationCenter on its own"
	)


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


WINDOW_MARKS = ("onedesk/public/js/window/frame.js", "onedesk/public/js/window/nav_tree.js")


def test_a_module_ships_a_tour_of_its_screen():
	"""A ready module declares its tours in its own tour.py (docs/READY.md,
	mechanism 10), one for each area of its screen: each has a key, a mark
	`at` that says the area is on screen, and steps, each pointing at a
	`data-tour` mark its screen or the window draws, never a class, saying it
	in a heading of five words or fewer and one sentence."""
	import ast

	marks = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in WINDOW_MARKS)
	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "tour.py"
		assert path.exists(), f"{module} ships no tour: write {path.relative_to(ROOT)}"
		tree = ast.parse(path.read_text(encoding="utf-8"))
		named = {node.targets[0].id: node.value for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
		assert "TOURS" in named, f"{module}'s tour.py declares no TOURS"
		own = "\n".join(p.read_text(encoding="utf-8") for p in ready.files(module) if p.suffix in (".js", ".vue"))
		keys = []
		for tour in named["TOURS"].elts:
			said = {key.value: value for key, value in zip(tour.keys, tour.values)}
			assert {"key", "at", "steps"} <= set(said), f"{module}'s tour lacks {sorted({'key', 'at', 'steps'} - set(said))}"
			key, at = said["key"].value, said["at"].value
			keys.append(key)
			assert f'data-tour="{at}"' in own + marks, f"{module}'s {key} tour: nothing draws data-tour=\"{at}\""
			steps = named[said["steps"].id] if isinstance(said["steps"], ast.Name) else said["steps"]
			assert steps.elts, f"{module}'s {key} tour has no steps"
			for step in steps.elts:
				one = {k.value: v for k, v in zip(step.keys, step.values)}
				target = one["target"].value
				title, text = one["title"].args[0].value, one["text"].args[0].value
				where = f"{module}'s {key} tour at {target}"
				assert f'data-tour="{target}"' in own + marks, f"{where}: nothing draws data-tour=\"{target}\""
				assert len(title.split()) <= 5, f"{where}: a heading is five words or fewer"
				assert len(re.findall(r"[.!?](?:\s|$)", text)) == 1 and text.endswith("."), f"{where}: one sentence"
		assert len(keys) == len(set(keys)), f"{module} has two tours with one key"


def _changers(folder: Path) -> set[str]:
	"""A module's calls whitelisted for POST alone: the ones that change
	something, as `file.function`."""
	import ast

	found = set()
	for path in folder.glob("*.py"):
		for node in ast.parse(path.read_text(encoding="utf-8")).body:
			if isinstance(node, ast.FunctionDef) and any(
				"whitelist" in ast.unparse(one) and "POST" in ast.unparse(one) for one in node.decorator_list
			):
				found.add(f"{path.stem}.{node.name}")
	return found


def test_a_module_reaches_every_change_through_oneai_or_says_why_not():
	"""Every call of a ready module that changes something (whitelisted for
	POST alone) is a card OneAI suggests, in its ai.py's REACH: the tool is
	hooked, and approving its card makes that very call. Or it is in
	NOT_FOR_AI with the reason in one sentence (docs/READY.md, mechanism 11)."""
	import ast

	hooks = (ROOT / "onedesk" / "hooks.py").read_text(encoding="utf-8")
	approving = (ROOT / "onedesk" / "one_ai" / "proposals.py").read_text(encoding="utf-8")
	for module, spec in ready.MODULES.items():
		folder = ROOT / "onedesk" / spec["folder"]
		path = folder / "ai.py"
		assert path.exists(), f"{module} says nothing of OneAI: write {path.relative_to(ROOT)}"
		source = path.read_text(encoding="utf-8")
		declared = _declared(path)
		reach, refused = declared.get("REACH", {}), declared.get("NOT_FOR_AI", {})
		changers = _changers(folder)
		missing = sorted(changers - set(reach) - set(refused))
		assert not missing, f"{module}: give OneAI a card for these, or say in NOT_FOR_AI why not: {missing}"
		assert not set(reach) & set(refused), f"{module}: in both REACH and NOT_FOR_AI: {sorted(set(reach) & set(refused))}"
		gone = sorted((set(reach) | set(refused)) - changers)
		assert not gone, f"{module}: named but no longer a call that changes something: {gone}"
		tools = {node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
		for call, tool in reach.items():
			assert tool in tools, f"{module}: {call} is reached by {tool}, which its ai.py doesn't have"
			assert f'"onedesk.{spec["folder"]}.ai.{tool}"' in hooks, f"{module}: {tool} isn't one of OneAI's tools"
			assert f"{call}(" in source + approving, f"{module}: approving {tool} never calls {call}"
		for call, why in refused.items():
			assert len(re.findall(r"[.!?](?:\s|$)", why)) == 1 and why.endswith("."), f"{module}: {call}'s reason is one sentence"


def test_the_registry_holds_the_fourteen_points_by_guards_that_exist():
	"""ready.POINTS are the fourteen points of docs/READY.md, in its order and
	by its names; each is held by guards, by a person's look (ready.HAND), or
	both; and every guard it names is a test that exists."""
	said = (ROOT / "docs" / "READY.md").read_text(encoding="utf-8").split("## The fourteen points", 1)[1].split("\n## ", 1)[0]
	titles = re.findall(r"^\d+\. \*\*(.+?)\.\*\*", said, re.M)
	assert titles == [one["title"] for one in ready.POINTS.values()], "ready.POINTS and docs/READY.md name the points alike"
	assert set(ready.HAND) <= set(ready.POINTS)
	for key, point in ready.POINTS.items():
		assert point["guards"] or key in ready.HAND, f"nothing holds {point['title']}"
		for guard in point["guards"]:
			path, name = guard.split("::")
			assert f"\ndef {name}(" in (ROOT / path).read_text(encoding="utf-8"), f"{point['title']}: no test {guard}"


def _git(*args: str) -> subprocess.CompletedProcess:
	return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def test_a_ready_module_was_looked_at_where_no_guard_can():
	"""A module marked ready has a look on every point a guard holds only in
	part (ready.HAND): the day, the commit it was taken at, and who looked.
	A major or minor version after that commit makes the look stale."""
	import datetime

	for module, spec in ready.MODULES.items():
		checked = spec.get("checked", {})
		assert set(checked) <= set(ready.HAND), f"{module}: only ready.HAND points are looked at: {sorted(set(checked) - set(ready.HAND))}"
		if spec.get("ready"):
			left = [ready.POINTS[key]["title"] for key in ready.HAND if key not in checked]
			assert not left, f"{module} is marked ready but nobody has looked at: {left}"
		grown = next((one for one in ready.versions(module) if one["kind"] != "fix"), None)
		since = _git("log", "--diff-filter=A", "--format=%H", "--", str(grown["path"].relative_to(ROOT))).stdout.split() if grown else []
		for key, look in checked.items():
			where = f"{module}'s look at {ready.POINTS[key]['title']}"
			assert look.get("by"), f"{where}: say who looked"
			assert datetime.date.fromisoformat(look["on"]) <= datetime.date.today(), f"{where}: a day not yet come"
			assert _git("cat-file", "-e", f"{look['commit']}^{{commit}}").returncode == 0, f"{where}: no commit {look['commit']}"
			if grown:
				assert since and _git("merge-base", "--is-ancestor", since[-1], look["commit"]).returncode == 0, (
					f"{where}: {grown['version']} came after it, so look again"
				)
