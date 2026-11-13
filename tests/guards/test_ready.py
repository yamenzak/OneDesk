"""A module on its way to ready keeps to its folder (docs/READY.md, A
module's folder): every file of it is in one of its places, and nothing
outside them is named for it unless onedesk/one/ready.py says why."""

import ast
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from onedesk.one import ready, registry, standard  # noqa: E402
from onedesk.one.registry.model import CENTRE_KEYS  # noqa: E402
from tests.guards.registry import GUARDS  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402


def _tracked() -> list[str]:
	return subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()


def _one_sentence(said: str) -> bool:
	return said.endswith(".") and len(re.findall(r"[.!?](?:\s|$)", said)) == 1


def stray_named(tracked: list[str], placed: dict, names: dict, shared) -> list[str]:
	"""The files named for a module outside its places; a file in another
	module's places is that module's, whatever it is named. Pure."""
	anywhere = tuple(prefix for prefixes in placed.values() for prefix in prefixes)
	stray = []
	for module, inside in placed.items():
		for path in tracked:
			named = any(name in path.lower() for name in names[module])
			elsewhere = path.startswith(anywhere) and not path.startswith(inside)
			if named and not path.startswith(inside) and not elsewhere and not shared(path):
				stray.append(f"  {module}: {path}")
	return stray


def test_nothing_outside_a_module_is_named_for_it():
	placed = {module: tuple(str(place.relative_to(ROOT)) + "/" for place in ready.places(module)) for module in ready.MODULES}
	stray = stray_named(_tracked(), placed, {module: spec["names"] for module, spec in ready.MODULES.items()}, ready.shared)
	assert not stray, "Move it into the module's places, or say in ready.SHARED why it is shared:\n" + "\n".join(stray)


def loose_at_top(tracked: list[str], shared) -> list[str]:
	"""The scripts and styles at the top of public/js or public/css not shared. Pure."""
	return [path for path in tracked if re.fullmatch(r"onedesk/public/(js|css)/[^/]+\.(js|css)", path) and not shared(path)]


def test_the_top_of_public_holds_only_what_is_shared():
	"""A module's scripts and styles are in its public/js/<folder>/ and
	public/css/<folder>/; the top of each holds only the desk's own, each
	in ready.SHARED with why (docs/run/RUN.md, Folders)."""
	stray = loose_at_top(_tracked(), ready.shared)
	assert not stray, "Move it into its module's folder under public/, or say in ready.SHARED why it is shared:\n  " + "\n  ".join(stray)


WRITTEN = {"AGENTS.md", "SCRATCHPAD.md"}


def unwritten_markdown(markdown: list[Path]) -> list[str]:
	"""Given a module's Markdown, relative to its folder: AGENTS.md or
	SCRATCHPAD.md missing, and any other outside help/ and updates/. Pure."""
	wrong = [f"no {name}" for name in sorted(WRITTEN) if Path(name) not in markdown]
	return wrong + [str(inside) for inside in markdown if inside.parts[0] not in ("help", "updates") and str(inside) not in WRITTEN]


def test_a_module_writes_only_agents_scratchpad_and_docs():
	"""A module on its way to ready holds AGENTS.md, SCRATCHPAD.md, help/ and updates/
	and no other Markdown (docs/READY.md, A module's folder)."""
	stray = []
	for spec in ready.MODULES.values():
		folder = ROOT / "onedesk" / spec["folder"]
		stray += [f"{spec['folder']}: {one}" for one in unwritten_markdown([path.relative_to(folder) for path in folder.rglob("*.md")])]
	assert not stray, f"no other Markdown in a module: {stray}"


TECHNICAL = re.compile(
	r"`|\.py\b|\.js\b|\.vue\b|\bcommit\b|\bfunction\b|\bendpoint\b|\bAPI\b|\bdoctype\b|\bfrappe\b|\berpnext\b|\bhooks?\b",
	re.I,
)
PICTURE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def unversioned(module: str, folder: str, found: list[dict], fingerprint: str) -> str | None:
	"""What to run when a module has no version, or changed since its newest. Pure."""
	if not found:
		return f"{module} has no version: python3 scripts/version.py {folder} major {module}"
	if found[0]["fingerprint"] != fingerprint:
		return f'{module} changed since {found[0]["version"]}: python3 scripts/version.py {folder} <major|minor|fix> "<title>", and say what changed'
	return None


def test_every_change_to_a_module_is_a_version():
	"""The newest version's fingerprint is the module's, so nothing it ships
	changes without a new version (docs/READY.md, Versions and What's New)."""
	for module, spec in ready.MODULES.items():
		said = unversioned(module, spec["folder"], ready.versions(module), ready.fingerprint(module))
		assert not said, said


def not_ready(production: bool, modules: dict) -> list[str]:
	"""The modules not ready while One is declared ready for production. Pure."""
	return [module for module, spec in modules.items() if not spec.get("ready")] if production else []


def test_one_is_ready_for_production_only_when_every_module_is():
	"""docs/READY.md, Before production."""
	left = not_ready(ready.PRODUCTION, ready.MODULES)
	assert not left, f"One is declared ready for production, but these modules aren't: {left}"


def out_of_order(module: str, found: list[dict]) -> list[str]:
	"""Given a module's versions newest first: one not starting at 1.0.0 or
	not the next of its kind after the one before. Pure."""
	found = list(reversed(found))
	if found[0]["version"] != "1.0.0":
		return [f"{module} starts at 1.0.0"]
	wrong = []
	for before, after in zip(found, found[1:]):
		major, minor, fix = ready.number(before["version"])
		expected = {
			"major": (major + 1, 0, 0),
			"minor": (major, minor + 1, 0),
			"fix": (major, minor, fix + 1),
			"internal": (major, minor, fix + 1),
		}[after["kind"]]
		if ready.number(after["version"]) != expected:
			wrong.append(f"{module} {after['version']} is no {after['kind']} after {before['version']}")
	return wrong


def test_versions_follow_one_another():
	wrong = [one for module in ready.MODULES for one in out_of_order(module, ready.versions(module))]
	assert not wrong, wrong


def badly_written(where: str, one: dict, exists) -> list[str]:
	"""What keeps a version from being written for the people using it:
	its kind, its date, a long title, an empty or technical body, a missing
	picture (`exists` says whether a path is there). Pure."""
	if one["kind"] not in ready.KINDS:
		return [where]
	wrong = []
	try:
		datetime.date.fromisoformat(one["date"])
	except (TypeError, ValueError):
		wrong.append(f"{where}: {one['date']} is no date")
	if not 0 < len(one["title"].split()) <= 5:
		wrong.append(f"{where}: a title is five words or fewer")
	body = one["body"]
	if not body or "Say here what people can do now" in body:
		return [*wrong, f"{where} says nothing yet"]
	hit = TECHNICAL.search(body) if one["kind"] in ready.SHOWN else None
	if hit:
		wrong.append(f"{where} reads like a commit: …{body[max(hit.start() - 30, 0) : hit.end() + 30]}…")
	wrong += [f"{where}: no {picture}" for picture in PICTURE.findall(body) if not exists(one["path"].parent / picture)]
	return wrong


def test_a_version_is_written_for_the_people_using_it():
	"""In English, for the people who use the module: what they can do now and
	what changed for them, never a file, a function or a commit. A title is a
	heading; a picture sits beside the entry."""
	wrong = [said for module in ready.MODULES for one in ready.versions(module) for said in badly_written(f"{module} {one['version']}", one, Path.exists)]
	assert not wrong, wrong


def unlisted_help(module: str, listed: list[str], pages: list[str], versions: list[dict]) -> list[str]:
	"""Help pages a module's list and its help/ disagree on, and a version
	reading more in a page that is not listed. Pure."""
	wrong = [] if sorted(listed) == sorted(pages) else [f"{module}'s help lists {sorted(listed)}, its help/ has {sorted(pages)}"]
	for one in versions:
		stray = [page for page in one["docs"] if page not in listed]
		if stray:
			wrong.append(f"{module} {one['version']} reads more in {stray}, which is no help page")
	return wrong


def test_every_help_page_is_listed_and_every_link_lands():
	"""Help shows a module's pages in the order ready.MODULES gives, so every
	page of its help/ is listed there, and a version's Read More names only
	pages that are."""
	for module, spec in ready.MODULES.items():
		listed = [page for page, _icon in spec.get("help", ())]
		pages = [path.stem for path in (ROOT / "onedesk" / spec["folder"] / "help").glob("*.md")]
		wrong = unlisted_help(module, listed, pages, ready.versions(module))
		assert not wrong, wrong


CODE = re.compile(r"`[^`]*(?:\.(?:py|js|vue|css|json)\b|[a-z_]+\.[a-z_]+\b|\b[a-z]+_[a-z_]+\b)[^`]*`")


def code_named(text: str) -> list[tuple[int, str]]:
	"""Each line of a help page naming code, with what it names; an address,
	a keyboard key or a search word in backticks is fine. Pure."""
	return [(number, found) for number, line in enumerate(text.splitlines(), 1) for found in CODE.findall(line) if "@" not in found and "{" not in found]


def test_a_help_page_names_no_code():
	"""Help is read by the people using the module, so a page names what they
	see and never the file or function behind it; AGENTS.md keeps those.
	An address, a keyboard key or a search word in backticks is fine."""
	for module, spec in ready.MODULES.items():
		for path in sorted((ROOT / "onedesk" / spec["folder"] / "help").glob("*.md")):
			named = code_named(path.read_text())
			assert not named, f"{path.relative_to(ROOT)}:{named[0][0]} names code {named[0][1]}; say it plainly and keep the name in AGENTS.md"


LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def badly_headed(where: str, page: dict, listed: set, exists) -> list[str]:
	"""A help page's long title or heading, missing picture, or link to a
	page Help does not list. Pure."""
	wrong = [] if 0 < len(page["title"].split()) <= 5 else [f"{where}: the title is five words or fewer"]
	wrong += [f"{where}: {line} is more than five words" for line in page["body"].splitlines() if line.startswith("#") and len(line.lstrip("# ").split()) > 5]
	wrong += [f"{where}: no {picture}" for picture in PICTURE.findall(page["body"]) if not exists(page["path"].parent / picture)]
	return wrong + [f"{where} links to {target}, which is no help page" for target in LINK.findall(page["body"]) if "://" not in target and target.split("#")[0] not in listed]


def test_a_help_page_is_headed_pictured_and_linked_soundly():
	"""Help is read in sections, so each heading is five words or fewer like
	any other (docs/WORDING.md); a picture it shows sits beside it, and a link
	to another page opens one that Help lists."""
	wrong = []
	for module, spec in ready.MODULES.items():
		listed = {page for page, _icon in spec.get("help", ())}
		for page in ready.help_pages(module):
			wrong += badly_headed(f"{module} {page['id']}", page, listed, Path.exists)
	assert not wrong, wrong


FOOT = ("module_foot(", "foot_action(", "interfaceModuleFoot(", "interfaceFootAction(", "$foot_action =", "class=\"one-interface-foot-action", "class=\"one-drawer-foot")
"""What drawing a module's foot looks like, which only
one_interface/nav_tree.js does."""


def own_settings(module: str, spec: dict, code: dict, rail: str | None) -> list[str]:
	"""A module drawing its own settings dialog or foot, or without either:
	its foot is drawn under its rail (its manifest's `sidebar`) by
	one_interface/nav_tree.js and nothing else. One with no window says why
	in a sentence. `code` is its scripts' text by name. Pure."""
	if spec.get("windowless"):
		return [] if _one_sentence(spec["windowless"]) else [f"{module}: why it has no window, in one sentence"]
	wrong = []
	own = [name for name, text in code.items() if "new frappe.ui.SettingsDialog" in text or "new onedesk.Centre(" in text]
	if own:
		wrong.append(f"{module} draws its own settings dialog in {own}; declare its part with onedesk.centers.part")
	loose = [name for name, text in code.items() if any(one in text for one in FOOT)]
	if loose:
		wrong.append(f"{module} draws its own foot in {loose}; one_interface/nav_tree.js draws every module's")
	if not any('onedesk.centers.part("settings"' in text or "onedesk.centers.declare(" in text for text in code.values()):
		wrong.append(f"{module} has no settings dialog")
	if not rail:
		wrong.append(f"{module} has no rail, so no foot")
	return wrong


def feet_drawn(sources: dict[str, str]) -> list[str]:
	"""The scripts, by name, that draw a module's foot besides
	one_interface/nav_tree.js; frame.js only places it. Pure."""
	return sorted(name for name, text in sources.items() if not name.endswith(("one_interface/nav_tree.js", "one_interface/frame.js")) and any(one in text for one in FOOT))


def test_one_place_draws_the_foot():
	"""docs/READY.md, mechanism 5: every module's foot (Help, the tour and
	its version) is drawn by onedesk.interface.foot, on the rail and in a
	phone's drawer alike, so no copy of it drifts."""
	js = ROOT / "onedesk" / "public" / "js"
	src = ROOT / "frontend" / "src"
	sources = {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in [*js.rglob("*.js"), *src.rglob("*.js"), *src.rglob("*.vue")] if "node_modules" not in path.parts}
	found = feet_drawn(sources)
	assert not found, found


def test_a_module_has_one_settings_dialog_and_one_foot():
	"""Every module's settings are its part of ControlCenter, in the centre
	frame (one_interface/centre.js), opened from the top bar's tray, and its
	foot is drawn under its rail by one_interface/nav_tree.js (docs/READY.md,
	mechanism 5), so they look and behave alike: the mark and Help atop the
	settings, tabs left out by role, and Help, the tour and the version at
	the foot. A module with no window,
	whose screen is a centre the others open, says why instead."""
	wrong = []
	for module, spec in ready.MODULES.items():
		code = {} if spec.get("windowless") else {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in ready.files(module) if path.suffix in (".js", ".vue")}
		wrong += own_settings(module, spec, code, registry.get(spec["folder"]).sidebar)
	assert not wrong, wrong


FOUND = ("access", "notifications", "ai", "shortcuts", "trust")
"""The centres a module's ControlCenter finds and opens on the module."""


def centres_misplaced(keys: tuple[str, ...], centre: str, rail: list[dict], frame: str) -> list[str]:
	"""Given the registry's centre keys, the centre frame's script, One's
	rail and the window's scripts: a centre One's rail does not open, one a
	module's ControlCenter does not find, or one the window opens. Pure."""
	wrong = [] if len(keys) == 10 else [f"ten centres, not {keys}"]
	opened = {re.search(r"center=(\w+)", row.get("url") or "").group(1) for row in rail if "center=" in (row.get("url") or "")}
	if opened != set(keys):
		wrong.append(f"One's rail opens {sorted(opened)}, not {sorted(keys)}")
	found = centre.split("onedesk.centers.found = ", 1)[1].split("\n};", 1)[0]
	wrong += [f"a module's ControlCenter doesn't find {one}" for one in FOUND if f'opens("{one}")' not in found]
	return wrong + [f"the window opens {one} by name: the tray offers every centre from the registry" for one in ("access", "trust", "ai") if f'onedesk.centers.open("{one}"' in frame]


def test_every_centre_opens_from_ones_rail_and_from_each_modules_settings():
	"""docs/READY.md, mechanism 18: the whole of each centre from One's rail,
	a module's part from its Settings, and nothing else in the frame."""
	js = ROOT / "onedesk" / "public" / "js"
	centre = (js / "one_interface" / "centre.js").read_text(encoding="utf-8")
	rail = json.loads((ROOT / "onedesk" / "one" / "sidebar" / "one" / "one.json").read_text())["items"]
	frame = (js / "one_interface" / "chrome.js").read_text(encoding="utf-8") + (js / "one_interface" / "nav_tree.js").read_text(encoding="utf-8")
	wrong = centres_misplaced(CENTRE_KEYS, centre, rail, frame)
	assert not wrong, wrong


def centres_typed(sources: dict[str, str], keys, readers: dict[str, str]) -> list[str]:
	"""The scripts, by name, that type a list of centres (three of their keys
	or more in one list) rather than reading the registry, and the readers
	(OneHub's tiles, the tray) that do not take them from
	onedesk.centers.reachable. Pure."""
	out = []
	for name, text in sources.items():
		if any(len(set(re.findall(r'"(\w+)"', listed)) & set(keys)) >= 3 for listed in re.findall(r"\[([^\[\]]*)\]", text)):
			out.append(name)
	return sorted(out) + [f"{name} does not take the centres from onedesk.centers.reachable" for name, text in readers.items() if "centers.reachable()" not in text]


def test_onehub_and_the_tray_offer_the_registrys_centres():
	"""OneHub's tiles, the top bar's tray and Ctrl+K offer the centres the
	registry declares (frappe.boot.one_centres) that One's rail opens for the
	reader, so a new centre needs no list to be added to."""
	js = ROOT / "onedesk" / "public" / "js"
	src = ROOT / "frontend" / "src"
	sources = {str(path.relative_to(ROOT)): path.read_text(encoding="utf-8") for path in [*js.rglob("*.js"), *src.rglob("*.js"), *src.rglob("*.vue")] if "node_modules" not in path.parts}
	centre = (js / "one_interface" / "centre.js").read_text(encoding="utf-8")
	readers = {
		"one/Hub.vue": (src / "one" / "Hub.vue").read_text(encoding="utf-8"),
		"onedesk.centers.tray": centre.split("onedesk.centers.tray = ", 1)[1].split("\n};", 1)[0],
	}
	found = centres_typed(sources, CENTRE_KEYS, readers)
	assert not found, found


AGREEMENTS =re.compile(r"\bagree|\bpolicy\b|\bterms\b|\baddendum\b|\bsubprocessors?\b", re.I)


def legal_unsaid(module: str, folder: str, found: list[dict], legal: str) -> list[str]:
	"""Given a module's versions newest first and what it adds to the
	agreements now: a change to those since its newest version, or a version
	moving them without saying which or as a fix. Pure."""
	wrong = []
	if found[0].get("legal") != legal:
		wrong.append(
			f"{module} changed what it adds to the agreements since {found[0]['version']}: "
			f'python3 scripts/version.py {folder} <major|minor|fix> "<title>", and say what changed'
		)
	for newer, older in zip(found, found[1:]):
		if "legal" in older and newer.get("legal") != older["legal"]:
			if not AGREEMENTS.search(newer["body"]):
				wrong.append(f"{module} {newer['version']} changes the agreements without saying which")
			if newer["kind"] in ("fix", "internal"):
				wrong.append(f"{module} {newer['version']} changes the agreements, so it is at least a minor (docs/READY.md, Which number moves)")
	return wrong


def test_a_change_to_what_a_module_agrees_on_is_said():
	"""A version records what its module adds to the agreements (trust_center
	`stamp`), so changing a clause or a company it sends data to is a new
	version, and that version tells the people using it which agreement moved
	(docs/READY.md, mechanism 6)."""
	wrong = [one for module, spec in ready.MODULES.items() for one in legal_unsaid(module, spec["folder"], ready.versions(module), ready.legal(module))]
	assert not wrong, wrong


def _declared_in(source: str) -> dict:
	"""A module file's top-level names that are plain values, read without
	importing it; the rest are left as their nodes."""
	found = {}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
			try:
				found[node.targets[0].id] = tree.literal(node.value)
			except ValueError:
				found[node.targets[0].id] = node.value
	return found


def _declared(path: Path) -> dict:
	"""A module's access.py or agent.py read without importing it."""
	return _declared_in(path.read_text(encoding="utf-8"))


def roles_wrong(module: str, folder: str, said: dict, hooks: str, help_bodies: list[str]) -> list[str]:
	"""Given what a module's access.py declares: not named by one_abilities,
	another APP, no abilities, DEFAULTS missing the role everyone holds or
	naming an ability not declared, or Help not showing {roles}. Pure."""
	wrong = [] if f'"onedesk.{folder}.access"' in hooks else [f"one_abilities in hooks.py doesn't name {module}'s"]
	if said.get("APP") != module:
		wrong.append(f"{module}'s access.py says APP = {said.get('APP')}")
	keys = set()
	for one in getattr(said["ABILITIES"], "elts", []):
		for key, value in zip(one.keys, one.values):
			if getattr(key, "value", None) == "key":
				keys.add(value.value)
	if not keys:
		wrong.append(f"{module} declares no abilities")
	defaults = said.get("DEFAULTS") or {}
	if (said.get("EVERYONE") or said.get("USER")) not in defaults:
		wrong.append(f"{module}'s DEFAULTS don't name the role everyone, or every user, holds")
	wrong += [f"{module}'s {role} names abilities it doesn't declare: {set(values) - keys}" for role, values in defaults.items() if not set(values) <= keys]
	if not any("{roles}" in body for body in help_bodies):
		wrong.append(f"{module}'s Help doesn't show what its roles start with ({{roles}})")
	return wrong


def engine_wrong(module: str, said: str, has_access: bool) -> list[str]:
	"""A module that is the frame the others are drawn in has no records and
	is given to nobody: it says why in one sentence and ships no roles. Pure."""
	wrong = [] if _one_sentence(said) else [f"{module}: why it ships no roles, in one sentence"]
	return wrong + ([f"{module} is an engine and ships no roles"] if has_access else [])


def test_a_module_ships_its_roles():
	"""A module's roles come from its own access.py (docs/READY.md,
	mechanism 7): named by the one_abilities hook, its DEFAULTS give every
	role it ships a value for each ability and are what migrate makes the
	roles from, and its Help shows them ({roles}), so the page says what
	ships."""
	hooks = tree.hooks()
	wrong = []
	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "access.py"
		if spec.get("engine"):
			wrong += engine_wrong(module, spec["engine"], path.exists())
		elif not path.exists():
			wrong.append(f"{module} ships no roles: write {path.relative_to(ROOT)}")
		else:
			wrong += roles_wrong(module, spec["folder"], _declared(path), hooks, [page["body"] for page in ready.help_pages(module)])
	assert not wrong, wrong
	fixtures = (ROOT / "onedesk" / "fixtures").glob("role.json")
	assert not list(fixtures), "a module's roles are made from its access.py, not a fixture"


SHARES = re.compile(
	r"frappe\.share\.(?:add|add_docshare|remove|set_permission)\b|\badd_docshare\(|new_doc\(\s*[\"']DocShare|[\"']doctype[\"']\s*:\s*[\"']DocShare"
)


def writes_share(source: str) -> str | None:
	"""The share a source writes itself, if it writes one. Pure."""
	hit = SHARES.search(source)
	return hit.group(0) if hit else None


def test_a_module_grants_through_abilities_alone():
	"""One person given more on one record than their role says is one idea:
	rights.grant, a share frappe answers (docs/READY.md, mechanism 7). A
	module writes no share of its own."""
	for module in ready.MODULES:
		for path in tree.scoped(ready.files(module)):
			if path.suffix == ".py" and "tests" not in path.parts:
				hit = writes_share(path.read_text(encoding="utf-8"))
				assert not hit, f"{path.relative_to(ROOT)} writes a share itself ({hit}); use rights.grant"


def badly_told(module: str, types: list[dict], layout: dict) -> list[str]:
	"""A notification type not naming each channel, on or why not, or its
	sender, still using the old flags, or with a subject past the bell's
	line; a mail its app writes itself (mailed_by) has no subject of ours. Pure."""
	wrong = []
	for one in types:
		where = f"{module} {one['name']}"
		channels = one.get("channels") or {}
		if not (tuple(channels) == layout["CHANNELS"] or set(channels) == set(layout["CHANNELS"])):
			wrong.append(f"{where} names its channels {sorted(channels)}, not {layout['CHANNELS']}")
		wrong += [f"{where}: {channel} is True or a sentence saying why not" for channel, said in channels.items() if not (said is True or (isinstance(said, str) and said.endswith(".")))]
		if one.get("sender") not in layout["SENDERS"]:
			wrong.append(f"{where}'s sender is one of {layout['SENDERS']}")
		loose = {"email", "push", "from_one"} & set(one)
		if loose:
			wrong.append(f"{where} says {sorted(loose)}; its channels and sender say that")
		if len(re.sub(r"\{\w+\}", "x" * 20, one.get("subject", ""))) > layout["BELL_LINE"]:
			wrong.append(f"{where}'s subject is longer than the bell's line")
	return wrong


def test_a_module_says_how_and_from_whom_it_tells_people():
	"""Every kind of notification a ready module sends names each channel,
	on or why not, and its sender, system or workspace (docs/READY.md,
	mechanism 8), in place of the email, push and from_one flags. Its
	subject fits the bell's line."""
	import runpy

	layout = runpy.run_path(str(ROOT / "onedesk" / "notifications" / "layout.py"))
	wrong = []
	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "notifications.py"
		if not path.exists():
			wrong.append(f"{module} says nothing of what it sends: write {path.relative_to(ROOT)}, TYPES = [] if it sends nothing")
			continue
		wrong += badly_told(module, runpy.run_path(str(path))["TYPES"], layout)
	assert not wrong, wrong


DRAWN_BY = {"access_center.js", "role_matrix.js", "notification_center.js"}
"""The files that draw what only AccessCenter and NotificationCenter draw
(docs/READY.md, mechanisms 14 and 15): the role matrix and a person's
notification choices. They are One's."""
CENTERS = {
	"AccessCenter": re.compile(r"onedesk\.roles\.(?:draw|pick|create|edit)\(|role_matrix\.js"),
	"NotificationCenter": re.compile(r"notification_center\.(?:choose|set_type)|email_notification_types|one_allow_(?:email|push)"),
}


def centres_drawn(text: str) -> list[tuple[str, str]]:
	"""Each centre a script draws part of, with what it draws. Pure."""
	return [(center, hit.group(0)) for center, drawn in CENTERS.items() if (hit := drawn.search(text))]


def centres_unoffered(centre: str) -> bool:
	"""Whether the centre frame no longer finds AccessCenter and NotificationCenter for a module. Pure."""
	return not ('opens("access")' in centre and 'opens("notifications")' in centre)


def test_a_module_leaves_roles_and_notifications_to_their_centers():
	"""Who may do what and how people hear of things are found from what a
	module declares, and drawn once (docs/READY.md, mechanisms 14 and 15):
	a ready module's screens draw neither, and ControlCenter offers both."""
	for module in ready.MODULES:
		for path in tree.scoped(ready.files(module)):
			if path.suffix not in (".js", ".vue") or (module == "One" and path.name in DRAWN_BY):
				continue
			drawn = centres_drawn(path.read_text(encoding="utf-8"))
			assert not drawn, f"{path.relative_to(ROOT)} draws what {drawn[0][0]} shows ({drawn[0][1]}); ControlCenter opens {drawn[0][0]}"
	centre = (ROOT / "onedesk" / "public" / "js" / "one_interface" / "centre.js").read_text(encoding="utf-8")
	assert not centres_unoffered(centre), "ControlCenter no longer offers AccessCenter and NotificationCenter on its own"


AI_DRAWN = re.compile(r"one_ai\.center\.(?:set_tier|set_on|set_job)|one_ai_tier|chosen_model|ai_models")
"""What only AICenter draws (docs/READY.md, mechanism 16): the tier, a
module's OneAI switches, and the model or words a job is given."""
DOOR = re.compile(r"\bgateway\.(?:talk|call|embed|see|hear|speak)\(|from onedesk\.one_admin import gateway|one_admin\.gateway import")


def draws_ai(text: str) -> str | None:
	"""What of AICenter's a script draws, if it draws any. Pure."""
	hit = AI_DRAWN.search(text)
	return hit.group(0) if hit else None


def opens_the_door(text: str) -> str | None:
	"""How a source reaches the gateway, if it does. Pure."""
	hit = DOOR.search(text)
	return hit.group(0) if hit else None


def test_only_aicenter_draws_oneais_settings_and_only_oneai_reaches_the_gateway():
	"""OneAI's settings are drawn once, in AICenter, from what each module
	declares; a module's screens open it, and only one_ai and the operator's
	door call the gateway (docs/AICENTER.md, stage 3)."""
	center = ROOT / "onedesk" / "public" / "js" / "one_ai" / "ai_center.js"
	for path in tree.scoped((ROOT / "onedesk").rglob("*")):
		if path.suffix not in (".js", ".vue") or path == center or "node_modules" in path.parts:
			continue
		hit = draws_ai(path.read_text(encoding="utf-8", errors="ignore"))
		assert not hit, f"{path.relative_to(ROOT)} draws what AICenter shows ({hit}); open onedesk.ai_center instead"
	centre = (ROOT / "onedesk" / "public" / "js" / "one_interface" / "centre.js").read_text(encoding="utf-8")
	assert 'opens("ai")' in centre, "ControlCenter no longer offers AICenter on its own"
	for path in tree.scoped((ROOT / "onedesk").rglob("*.py")):
		if path.parts[-2] in ("one_admin", "one_ai") or "one_admin" in path.parts or "one_ai" in path.parts:
			continue
		hit = opens_the_door(path.read_text(encoding="utf-8"))
		assert not hit, f"{path.relative_to(ROOT)} reaches the gateway ({hit}); ask one_ai, which asks the account"


def setup_wrong(module: str, source: str, code: str) -> list[str]:
	"""Given a module's setup.py and its scripts: a step without a key, a
	title, what it is for, the ability it needs and its tab, naming a tab its
	settings don't have, or with fields nothing saves. Pure."""
	steps = next(node.value for node in ast.parse(source).body if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "STEPS")
	wrong = []
	for step in steps.elts:
		keys = {key.value: value for key, value in zip(step.keys, step.values)}
		where = f"{module} {getattr(keys.get('key'), 'value', '?')}"
		lacking = {"key", "title", "about", "needs", "tab"} - set(keys)
		if lacking:
			wrong.append(f"{where} lacks {sorted(lacking)}")
			continue
		if f'id: "{keys["tab"].value}"' not in code:
			wrong.append(f"{where} names a tab, {keys['tab'].value}, its settings don't have")
		if "fields" in keys and "save" not in keys:
			wrong.append(f"{where} has fields and nothing saves them")
	return wrong


def test_a_module_says_what_setting_it_up_takes():
	"""A ready module declares its setup steps in its own setup.py
	(docs/READY.md, mechanism 9): each with a key, a title, what it is for,
	the ability it needs and the settings tab that does it; one with fields
	saves them, and one that can't be left for later is rare enough to be
	said."""
	wrong = []
	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "setup.py"
		if not path.exists():
			wrong.append(f"{module} says nothing of setting it up: write {path.relative_to(ROOT)}, STEPS = [] if it needs nothing")
			continue
		code = "\n".join(p.read_text(encoding="utf-8") for p in ready.files(module) if p.suffix == ".js")
		wrong += setup_wrong(module, path.read_text(encoding="utf-8"), code)
	assert not wrong, wrong


WINDOW_MARKS = ("onedesk/public/js/one_interface/frame.js", "onedesk/public/js/one_interface/nav_tree.js", "onedesk/public/js/one_interface/look.js", "onedesk/public/js/one_interface/form.js", "onedesk/public/js/one_interface/centre.js")


RECORDS = {
	doctype.lower().replace(" ", "-")
	for spec in ready.MODULES.values()
	for doctype in (spec.get("interface") or {})
}


def _draws(mark: str, code: str) -> bool:
	"""A mark is drawn as written, bound to the one element that carries it
	(`:data-tour="first ? 'mark' : undefined"`), such as a list's first row, or
	set on an element frappe draws (`.attr("data-tour", "mark")`, or
	`.dataset.tour`); a record's head is `record-<its doctype>` for every
	record type the registry dresses (look.js)."""
	return (
		f'data-tour="{mark}"' in code
		or f'.attr("data-tour", "{mark}")' in code
		or f'.dataset.tour = "{mark}"' in code
		or bool(re.search(rf"data-tour=\"[^\"]*'{re.escape(mark)}'", code))
		or (mark.startswith("record-") and "dataset.tour = `record-${" in code and mark[len("record-") :] in RECORDS)
	)


def tour_wrong(module: str, source: str, code: str) -> list[str]:
	"""Given a module's tour.py and the scripts that may draw its marks: no
	TOURS, a tour without a key, a mark or steps, a mark nothing draws, a
	long heading, a step that is not one sentence, two tours with one key. Pure."""
	named = {node.targets[0].id: node.value for node in ast.parse(source).body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
	if "TOURS" not in named:
		return [f"{module}'s tour.py declares no TOURS"]
	wrong, keys = [], []
	for tour in named["TOURS"].elts:
		said = {key.value: value for key, value in zip(tour.keys, tour.values)}
		lacking = {"key", "at", "steps"} - set(said)
		if lacking:
			wrong.append(f"{module}'s tour lacks {sorted(lacking)}")
			continue
		key, at = said["key"].value, said["at"].value
		keys.append(key)
		if not _draws(at, code):
			wrong.append(f"{module}'s {key} tour: nothing draws data-tour=\"{at}\"")
		steps = named[said["steps"].id] if isinstance(said["steps"], ast.Name) else said["steps"]
		if not steps.elts:
			wrong.append(f"{module}'s {key} tour has no steps")
		for step in steps.elts:
			one = {k.value: v for k, v in zip(step.keys, step.values)}
			target = one["target"].value
			title, text = one["title"].args[0].value, one["text"].args[0].value
			where = f"{module}'s {key} tour at {target}"
			if not _draws(target, code):
				wrong.append(f"{where}: nothing draws data-tour=\"{target}\"")
			if len(title.split()) > 5:
				wrong.append(f"{where}: a heading is five words or fewer")
			if not _one_sentence(text):
				wrong.append(f"{where}: one sentence")
	return wrong + ([f"{module} has two tours with one key"] if len(keys) != len(set(keys)) else [])


def test_a_module_ships_a_tour_of_its_screen():
	"""A ready module declares its tours in its own tour.py (docs/READY.md,
	mechanism 10), one for each area of its screen: each has a key, a mark
	`at` that says the area is on screen, and steps, each pointing at a
	`data-tour` mark its screen, the window or the docs dialog draws, never a class, saying it
	in a heading of five words or fewer and one sentence."""
	marks = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in WINDOW_MARKS)
	wrong = []
	for module, spec in ready.MODULES.items():
		path = ROOT / "onedesk" / spec["folder"] / "tour.py"
		if not path.exists():
			wrong.append(f"{module} ships no tour: write {path.relative_to(ROOT)}")
			continue
		own = "\n".join(p.read_text(encoding="utf-8") for p in ready.files(module) if p.suffix in (".js", ".vue"))
		wrong += tour_wrong(module, path.read_text(encoding="utf-8"), own + marks)
	assert not wrong, wrong


def _changers(module: str) -> set[str]:
	"""A module's calls whitelisted for POST alone: the ones that change
	something, as `file.function`, in its own files (not the engines
	ready.SHARED names)."""
	folder = ROOT / "onedesk" / ready.MODULES[module]["folder"]
	found = set()
	for path in (one for one in folder.glob("*.py") if one.is_file() and not ready.shared(str(one.relative_to(ROOT)))):
		for node in tree.parsed(path).body:
			if isinstance(node, ast.FunctionDef) and any(
				"whitelist" in ast.unparse(one) and "POST" in ast.unparse(one) for one in node.decorator_list
			):
				found.add(f"{path.stem}.{node.name}")
	return found


def unreached(module: str, folder: str, source: str, changers: set, hooks: str, approving: str) -> list[str]:
	"""Given a module's agent.py and its calls that change something: one
	neither in REACH nor NOT_FOR_AI, one in both or in either but no longer
	a change, a card whose tool is missing, unhooked or never makes its call,
	a reason not in one sentence. Pure."""
	declared = _declared_in(source)
	reach, refused = declared.get("REACH", {}), declared.get("NOT_FOR_AI", {})
	wrong = []
	missing = sorted(changers - set(reach) - set(refused))
	if missing:
		wrong.append(f"{module}: give OneAI a card for these, or say in NOT_FOR_AI why not: {missing}")
	if set(reach) & set(refused):
		wrong.append(f"{module}: in both REACH and NOT_FOR_AI: {sorted(set(reach) & set(refused))}")
	gone = sorted((set(reach) | set(refused)) - changers)
	if gone:
		wrong.append(f"{module}: named but no longer a call that changes something: {gone}")
	tools = {node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
	for call, tool in reach.items():
		if tool not in tools:
			wrong.append(f"{module}: {call} is reached by {tool}, which its agent.py doesn't have")
		if f'"onedesk.{folder}.agent.{tool}"' not in hooks:
			wrong.append(f"{module}: {tool} isn't one of OneAI's tools")
		if f"{call}(" not in source + approving:
			wrong.append(f"{module}: approving {tool} never calls {call}")
	return wrong + [f"{module}: {call}'s reason is one sentence" for call, why in refused.items() if not _one_sentence(why)]


def test_a_module_reaches_every_change_through_oneai_or_says_why_not():
	"""Every call of a ready module that changes something (whitelisted for
	POST alone) is a card OneAI suggests, in its agent.py's REACH: the tool is
	hooked, and approving its card makes that very call. Or it is in
	NOT_FOR_AI with the reason in one sentence (docs/READY.md, mechanism 11).
	A change-mode run reads the modules with a changed file of their own,
	or all of them when hooks.py or one_ai/proposals.py changed."""
	hooks = tree.hooks()
	approving = (ROOT / "onedesk" / "one_ai" / "proposals.py").read_text(encoding="utf-8")
	every = tree.judged(ROOT / "onedesk" / "hooks.py") or tree.judged(ROOT / "onedesk" / "one_ai" / "proposals.py")
	wrong = []
	for module, spec in ready.MODULES.items():
		folder = ROOT / "onedesk" / spec["folder"]
		if not every and not tree.scoped(folder.glob("*.py")):
			continue
		path = folder / "agent.py"
		if not path.exists():
			wrong.append(f"{module} says nothing of OneAI: write {path.relative_to(ROOT)}")
			continue
		wrong += unreached(module, spec["folder"], path.read_text(encoding="utf-8"), _changers(module), hooks, approving)
	assert not wrong, wrong


def points_misread(points: list, read: dict, hand: dict, guards) -> list[str]:
	"""Given the standard's points held before live: ready.POINTS not them
	in order, a look on a point not among them, or a point nothing holds. Pure."""
	live = [point for point in points if point.live]
	wrong = [] if [(point.key, point.title) for point in live] == [(key, one["title"]) for key, one in read.items()] else ["ready.POINTS is not the standard's points held before live"]
	if not set(hand) <= set(read):
		wrong.append("a look is on a point held before live")
	ruled = {guard.point for guard in guards}
	return wrong + [f"nothing holds {point.title}" for point in live if point.number not in ruled and not point.look]


def test_the_points_held_before_live_are_the_standards():
	"""ready.POINTS and ready.HAND are readings of the standard
	(onedesk/one/standard.py): the points a module is held to before live, in
	its order, and the looks no rule settles; each is held by a rule of
	tests/guards/registry.py, a look, or both."""
	wrong = points_misread(list(standard.POINTS.values()), ready.POINTS, ready.HAND, GUARDS)
	assert not wrong, wrong


def _git(*args: str) -> subprocess.CompletedProcess:
	return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def unlooked(module: str, marked: bool, looks: dict, hand: dict, points: dict) -> list[str]:
	"""A look on a point not in ready.HAND, one not saying who looked, and
	for a module marked ready a HAND point nobody has looked at. Pure."""
	strange = set(looks) - set(hand)
	wrong = [f"{module}: only ready.HAND points are looked at: {sorted(strange)}"] if strange else []
	wrong += [f"{module} {look['version']}: say who looked (looked_by)" for look in looks.values() if not look["by"]]
	left = [points[key]["title"] for key in hand if key not in looks] if marked else []
	if left:
		wrong.append(f"{module} is marked ready, but since its last major or minor version nobody has looked at: {left} (python3 scripts/close.py --looked)")
	return wrong


def test_a_ready_module_was_looked_at_where_no_guard_can():
	"""A module marked ready has a look on every point a guard holds only in
	part (ready.HAND), written in a version's front matter (`looked:` and
	`looked_by:`) no older than its newest major or minor version, which makes
	a look stale."""
	wrong = [one for module, spec in ready.MODULES.items() for one in unlooked(module, bool(spec.get("ready")), ready.looks(module), ready.HAND, ready.POINTS)]
	assert not wrong, wrong


def test_the_folder_and_version_rules_catch_their_examples():
	placed = {"OneHR": ("onedesk/one_hr/",), "OneCRM": ("onedesk/one_crm/",)}
	names = {"OneHR": ["one_hr", "leave"], "OneCRM": ["one_crm"]}
	tracked = ["onedesk/public/js/leave_list.js", "onedesk/one_crm/leave.py", "onedesk/one_hr/leave.py", "onedesk/public/js/shared.js"]
	assert stray_named(tracked, placed, names, lambda _path: False) == ["  OneHR: onedesk/public/js/leave_list.js"]
	assert stray_named(tracked, placed, names, lambda path: path.endswith("leave_list.js")) == []
	assert loose_at_top(tracked, lambda path: path.endswith("shared.js")) == ["onedesk/public/js/leave_list.js"]
	assert unwritten_markdown([Path("AGENTS.md"), Path("help/leave.md"), Path("PLAN.md")]) == ["no SCRATCHPAD.md", "PLAN.md"]
	assert unwritten_markdown([Path("AGENTS.md"), Path("SCRATCHPAD.md"), Path("updates/1.0.0.md")]) == []
	assert unversioned("OneHR", "one_hr", [], "abc").startswith("OneHR has no version")
	assert unversioned("OneHR", "one_hr", [{"fingerprint": "old", "version": "1.0.0"}], "abc").startswith("OneHR changed since 1.0.0")
	assert unversioned("OneHR", "one_hr", [{"fingerprint": "abc", "version": "1.0.0"}], "abc") is None
	assert not_ready(True, {"OneHR": {"ready": True}, "OneCRM": {}}) == ["OneCRM"]
	assert not_ready(False, {"OneCRM": {}}) == []
	assert out_of_order("OneHR", [{"version": "1.2.0", "kind": "minor"}, {"version": "1.0.0", "kind": "major"}]) == ["OneHR 1.2.0 is no minor after 1.0.0"]
	assert out_of_order("OneHR", [{"version": "1.1.0", "kind": "minor"}, {"version": "1.0.0", "kind": "major"}]) == []
	assert out_of_order("OneHR", [{"version": "0.1.0", "kind": "major"}]) == ["OneHR starts at 1.0.0"]
	version = {"kind": "minor", "date": "2026-11-13", "title": "Leave in half days", "body": "You can ask for half a day.", "path": Path("updates/1.1.0.md")}
	assert badly_written("OneHR 1.1.0", version, lambda _path: True) == []
	technical = {**version, "title": "A much longer title than five words", "body": "Fixed `leave.py`. ![](gone.png)"}
	assert badly_written("OneHR 1.1.0", technical, lambda _path: False) == [
		"OneHR 1.1.0: a title is five words or fewer",
		"OneHR 1.1.0 reads like a commit: …Fixed `leave.py`. ![](gone.png)…",
		"OneHR 1.1.0: no gone.png",
	]
	assert unlisted_help("OneHR", ["leave"], ["leave", "pay"], [{"version": "1.1.0", "docs": ["gone"]}]) == [
		"OneHR's help lists ['leave'], its help/ has ['leave', 'pay']",
		"OneHR 1.1.0 reads more in ['gone'], which is no help page",
	]
	assert code_named("Open Leave.\nIt is `leave_list.js`, or press `Ctrl` or mail `a@b.co`.") == [(2, "`leave_list.js`")]
	page = {"title": "Asking for leave", "body": "## A heading far longer than five words\n![](gone.png) [Pay](pay) [Leave](leave#days) [Web](https://x.io)", "path": Path("help/leave.md")}
	assert badly_headed("OneHR leave", page, {"leave"}, lambda _path: False) == [
		"OneHR leave: ## A heading far longer than five words is more than five words",
		"OneHR leave: no gone.png",
		"OneHR leave links to pay, which is no help page",
	]
	found = [{"legal": "b", "version": "1.1.0", "kind": "fix", "body": "Quicker."}, {"legal": "a", "version": "1.0.0", "kind": "major", "body": ""}]
	assert legal_unsaid("OneHR", "one_hr", found, "c") == [
		'OneHR changed what it adds to the agreements since 1.1.0: python3 scripts/version.py one_hr <major|minor|fix> "<title>", and say what changed',
		"OneHR 1.1.0 changes the agreements without saying which",
		"OneHR 1.1.0 changes the agreements, so it is at least a minor (docs/READY.md, Which number moves)",
	]
	assert legal_unsaid("OneHR", "one_hr", [{**found[0], "kind": "minor", "body": "The terms say more."}, found[1]], "b") == []


def test_the_declaration_rules_catch_their_examples():
	code = {"a.js": 'onedesk.centers.part("settings", "OneHR");'}
	assert own_settings("OneHR", {}, code, "OneHR") == []
	assert own_settings("OneHR", {}, {"a.js": "new frappe.ui.SettingsDialog(); win.module_foot({ module })"}, None) == [
		"OneHR draws its own settings dialog in ['a.js']; declare its part with onedesk.centers.part",
		"OneHR draws its own foot in ['a.js']; one_interface/nav_tree.js draws every module's",
		"OneHR has no settings dialog",
		"OneHR has no rail, so no foot",
	]
	assert own_settings("OneHR", {"windowless": "It has none. Truly."}, {}, None) == ["OneHR: why it has no window, in one sentence"]
	assert feet_drawn({"public/js/one_interface/nav_tree.js": "win.$foot_action = 1", "public/js/one_hr/hr.js": "win.module_foot({})", "a.vue": "x"}) == ["public/js/one_hr/hr.js"]
	keys = ("help", "settings", "account")
	assert centres_typed({"a.js": 'open(["help", "account"])', "b.vue": 'const TILES = ["help", "settings", "account"];'}, keys, {"Hub.vue": "centers.reachable()", "tray": "boot.one_centres"}) == [
		"b.vue",
		"tray does not take the centres from onedesk.centers.reachable",
	]
	names = tuple(f"c{n}" for n in range(10))
	centre = "onedesk.centers.found = (module) => {" + " ".join(f'opens("{one}")' for one in FOUND) + "\n};"
	rail = [{"url": f"/app/one?center={name}"} for name in names]
	assert centres_misplaced(names, centre, rail, "") == []
	assert centres_misplaced(names, centre.replace('opens("ai")', ""), rail[1:], 'onedesk.centers.open("trust", {})') == [
		f"One's rail opens {sorted(names[1:])}, not {sorted(names)}",
		"a module's ControlCenter doesn't find ai",
		"the window opens trust by name: the tray offers every centre from the registry",
	]
	assert centres_unoffered('opens("access")') and not centres_unoffered('opens("access") opens("notifications")')
	access = 'APP = "OneHR"\nABILITIES = [{"key": "approve", "label": _("Approve")}]\nEVERYONE = "Employee"\nDEFAULTS = {"Employee": {"approve": 0, "pay": 1}}\n'
	said = _declared_in(access)
	assert roles_wrong("OneHR", "one_hr", said, "", ["No roles here."]) == [
		"one_abilities in hooks.py doesn't name OneHR's",
		"OneHR's Employee names abilities it doesn't declare: {'pay'}",
		"OneHR's Help doesn't show what its roles start with ({roles})",
	]
	assert roles_wrong("OneHR", "one_hr", {**said, "DEFAULTS": {"Employee": {"approve": 0}}}, '"onedesk.one_hr.access"', ["{roles}"]) == []
	assert engine_wrong("One", "It is the frame.", True) == ["One is an engine and ships no roles"]
	assert writes_share("frappe.share.add('Leave', name, user)") == "frappe.share.add"
	assert writes_share("rights.grant('Leave', name, user)") is None
	layout = {"CHANNELS": ("bell", "email", "push"), "SENDERS": ("system", "workspace"), "BELL_LINE": 30}
	good = {"name": "Approved", "channels": {"bell": True, "email": True, "push": "Nobody waits on it."}, "sender": "system", "subject": "Approved {name}"}
	assert badly_told("OneHR", [good], layout) == []
	bad = {"name": "Approved", "channels": {"bell": "no"}, "sender": "me", "email": 1, "subject": "Approved for {name} and {other}"}
	assert badly_told("OneHR", [bad], layout) == [
		"OneHR Approved names its channels ['bell'], not ('bell', 'email', 'push')",
		"OneHR Approved: bell is True or a sentence saying why not",
		"OneHR Approved's sender is one of ('system', 'workspace')",
		"OneHR Approved says ['email']; its channels and sender say that",
		"OneHR Approved's subject is longer than the bell's line",
	]
	assert centres_drawn("onedesk.roles.draw(wrapper)") == [("AccessCenter", "onedesk.roles.draw(")]
	assert centres_drawn("onedesk.access.open({ module })") == []
	assert draws_ai("frappe.call('onedesk.one_ai.center.set_tier')") == "one_ai.center.set_tier"
	assert opens_the_door("from onedesk.one_admin import gateway") == "from onedesk.one_admin import gateway"
	assert draws_ai("onedesk.ai_center.open({ module })") is None and opens_the_door("one_ai.ask(x)") is None


def test_the_setup_tour_and_oneai_rules_catch_their_examples():
	setup = 'STEPS = [{"key": "pay", "title": "Pay", "about": "x", "needs": "y", "tab": "payroll", "fields": []}, {"key": "half"}]'
	assert setup_wrong("OneHR", setup, 'id: "leave"') == [
		"OneHR pay names a tab, payroll, its settings don't have",
		"OneHR pay has fields and nothing saves them",
		"OneHR half lacks ['about', 'needs', 'tab', 'title']",
	]
	assert setup_wrong("OneHR", setup.replace(', {"key": "half"}', "").replace('"fields": []', '"fields": [], "save": "x"'), 'id: "payroll"') == []
	tour = 'TOURS = [{"key": "list", "at": "leave-list", "steps": STEPS}]\nSTEPS = [{"target": "leave-new", "title": _("Ask for leave"), "text": _("Ask here.")}]'
	assert tour_wrong("OneHR", tour, 'data-tour="leave-list" data-tour="leave-new"') == []
	assert tour_wrong("OneHR", tour.replace("Ask here.", "Ask here. Then wait."), 'data-tour="leave-list"') == [
		"OneHR's list tour at leave-new: nothing draws data-tour=\"leave-new\"",
		"OneHR's list tour at leave-new: one sentence",
	]
	assert tour_wrong("OneHR", "STEPS = []", "") == ["OneHR's tour.py declares no TOURS"]
	agent = 'REACH = {"leave.approve": "approve_leave"}\nNOT_FOR_AI = {"leave.pay": "Money. Twice."}\ndef approve_leave():\n\tleave.approve(x)\n'
	hooks = '"onedesk.one_hr.agent.approve_leave"'
	assert unreached("OneHR", "one_hr", agent, {"leave.approve", "leave.pay", "leave.cancel"}, hooks, "") == [
		"OneHR: give OneAI a card for these, or say in NOT_FOR_AI why not: ['leave.cancel']",
		"OneHR: leave.pay's reason is one sentence",
	]
	assert unreached("OneHR", "one_hr", agent.replace("Money. Twice.", "Money."), {"leave.approve", "leave.pay"}, hooks, "") == []
	assert unreached("OneHR", "one_hr", agent, {"leave.pay"}, "", "")[:2] == [
		"OneHR: named but no longer a call that changes something: ['leave.approve']",
		"OneHR: approve_leave isn't one of OneAI's tools",
	]


def test_the_standard_rules_catch_their_examples():
	from collections import namedtuple

	Point = namedtuple("Point", "key number title live look")
	Rule = namedtuple("Rule", "point")
	points = [Point("works", 1, "It works", True, ""), Point("reads", 2, "It reads", True, "a look"), Point("later", 3, "Later", False, "")]
	read = {"works": {"title": "It works"}, "reads": {"title": "It reads"}}
	assert points_misread(points, read, {"reads": "a look"}, [Rule(1)]) == []
	assert points_misread(points, {"works": {"title": "It works"}}, {"later": "x"}, []) == [
		"ready.POINTS is not the standard's points held before live",
		"a look is on a point held before live",
		"nothing holds It works",
	]
	hand = {"reads": "a look"}
	titles = {"reads": {"title": "It reads"}}
	assert unlooked("OneHR", True, {"reads": {"by": "Yamen", "version": "1.1.0"}}, hand, titles) == []
	assert unlooked("OneHR", True, {"works": {"by": "", "version": "1.1.0"}}, hand, titles) == [
		"OneHR: only ready.HAND points are looked at: ['works']",
		"OneHR 1.1.0: say who looked (looked_by)",
		"OneHR is marked ready, but since its last major or minor version nobody has looked at: ['It reads'] (python3 scripts/close.py --looked)",
	]
	assert unlooked("OneHR", False, {}, hand, titles) == []
