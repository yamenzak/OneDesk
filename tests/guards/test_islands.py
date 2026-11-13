"""Islands: OneDesk's bespoke screens, drawn with frappe-ui inside desk pages
(docs/ISLANDS.md). These guards keep every island, in every app, built the
same way, so the screens read as one product and stay desk's."""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

FRONTEND = tree.ROOT / "frontend"
SRC = FRONTEND / "src"
HOOKS = tree.hooks()


def _entries() -> dict:
	"""The build's entries, by island name: frappe names an island by its entry
	(ui/island/decisions/0014), so the entry is the declaration."""
	build = (FRONTEND / "build-islands.mjs").read_text(encoding="utf-8")
	block = re.search(r"ISLANDS = \{(.*?)\};", build, re.S).group(1)
	return dict(re.findall(r'"([\w.]+)":\s*"([^"]+)"', block))


PORTAL = FRONTEND / "portal" / "src"


def _name(path: Path) -> Path:
	return path.relative_to(SRC if path.is_relative_to(SRC) else FRONTEND)


def _vue() -> list[Path]:
	"""Every screen: the islands, and the portal, a frappe-ui app of its own."""
	return sorted(p for p in [*SRC.rglob("*.vue"), *PORTAL.rglob("*.vue")] if not tree.vendored(p))


def _texts(paths) -> dict[str, str]:
	return {str(path): path.read_text(encoding="utf-8") for path in paths}


def island_problems(name: str, entry: str, pages: dict[str, str], scripts: list[str], reports: list[str], parts: list[str], manifests: list[str]) -> list[str]:
	"""What is wrong with one island: its name, its entry, nothing mounting it
	(a desk page, a record tab or form, a report, a part OneInterface's
	renderer draws on every record of a kind, or a list view a manifest
	names), or a page mounting it outside `island_page`. Pure."""
	out = []
	if not name.startswith("onedesk."):
		out.append(f"{name} is not named onedesk.*")
	if not ('from "../kit"' in entry and "screen(" in entry):
		out.append(f"{name}'s entry is not a kit screen")
	mounting = [page for page, text in pages.items() if f'island: "{name}"' in text]
	tabs = [
		text
		for text in scripts
		if f'mount_island("{name}"' in text
		and ("onedesk.record_tabs.register(" in text or "onedesk.check.report = " in text or "frappe.ui.form.on(" in text)
	]
	reported = [text for text in reports if f'mount_island("{name}"' in text]
	drawn = [text for text in parts if f'mount_island("{name}"' in text]
	views = any(f'"island": "{name}"' in text for text in manifests)
	if not (mounting or tabs or reported or drawn or views):
		out.append(f"no desk page, record tab, form field, report, list view or OneInterface part mounts {name}")
	return out + [page for page in mounting if "onedesk.island_page(" not in pages[page]]


def test_every_island_is_declared_built_and_mounted():
	entries = _entries()
	assert entries, "no islands built"
	assert "ui_islands" not in HOOKS
	public = tree.APP / "public" / "js"
	pages = _texts(tree.APP.glob("*/page/*/*.js"))
	scripts = list(_texts([*public.glob("*.js"), *public.glob("*/*.js")]).values())
	reports = list(_texts(tree.APP.glob("*/report/*/*.js")).values())
	parts = list(_texts((public / "one_interface").glob("*.js")).values())
	manifests = list(_texts(tree.APP.glob("*/manifest.py")).values())
	for name, source in entries.items():
		entry = (FRONTEND / source).read_text(encoding="utf-8")
		found = island_problems(name, entry, pages, scripts, reports, parts, manifests)
		assert not found, found


def build_problems(root: dict, frontend: dict) -> list[str]:
	"""What in the two package.json files keeps `bench build` from building
	the islands on the frappe-ui we pin. Pure."""
	out = []
	if root["scripts"].get("build") != "yarn --cwd frontend build":
		out.append("the app's build does not build frontend/")
	if "frontend install --frozen-lockfile" not in root["scripts"].get("postinstall", ""):
		out.append("installing the app does not install frontend/ from its lockfile")
	if frontend["scripts"].get("build") != "node build-islands.mjs --production && cd portal && vite build":
		out.append("frontend's build is not the islands and the portal")
	if not re.fullmatch(r"\d+\.\d+\.\d+", frontend["dependencies"].get("frappe-ui", "")):
		out.append("frappe-ui is not pinned")
	if frontend["dependencies"].get("@framework/ui") != "link:../../frappe/ui":
		out.append("@framework/ui is not frappe's own")
	return out


def test_bench_build_builds_the_islands():
	root = json.loads((tree.ROOT / "package.json").read_text())
	frontend = json.loads((FRONTEND / "package.json").read_text())
	assert not build_problems(root, frontend), build_problems(root, frontend)
	assert (FRONTEND / "yarn.lock").exists()


ALLOWED = re.compile(r'^(vue|vue-router|frappe-ui(/[\w-]+)?|@framework/ui(/[\w/-]+)?|\.{1,2}/[\w./-]+)$')


def own_parts(source: str) -> list[str]:
	"""What a screen draws of its own: a style, a colour, an inline style or
	a part imported from outside frappe-ui. Pure."""
	out = []
	if "<style" in source:
		out.append("styles itself; use frappe-ui's tokens")
	if re.search(r"#[0-9a-fA-F]{3,8}\b", source) or re.search(r"\b(text|bg|border)-\[", source):
		out.append("names a colour")
	if re.search(r'\sstyle="', source):
		out.append("styles an element")
	return out + [f"imports {specifier}" for specifier in re.findall(r'from "([^"]+)"', source) if not ALLOWED.match(specifier)]


def test_an_island_is_frappe_ui_and_nothing_of_its_own():
	"""A screen is frappe-ui's components laid out with its tokens. No style of
	its own, no colour of its own, no part from anywhere else."""
	for path in _vue():
		found = own_parts(path.read_text(encoding="utf-8"))
		assert not found, f"{path.name} {found[0]}"


def tailwind_tokens(source: str) -> list[str]:
	"""Tailwind's own tokens in a screen, which frappe-ui 1.0 does not draw,
	and the whole of `@framework/ui` imported at once. Pure."""
	out = []
	if re.search(r"(?<![\w-])rounded(-(sm|md|lg|xl|2xl))?(?![\w-])", source):
		out.append("uses Tailwind's corners; use rounded-1 to rounded-7")
	if re.search(r"\b(bg|ring|border)-surface-white\b", source):
		out.append("uses surface-white; use surface-base or surface-elevation-1")
	if 'from "@framework/ui"' in source:
		out.append("imports all of @framework/ui; import the part")
	return out


def test_an_island_uses_frappe_ui_tokens():
	"""frappe-ui 1.0's tokens are not Tailwind's. A class from Tailwind's own
	scale builds without complaint and draws nothing: corners stay square and
	panels see-through. And `@framework/ui` is imported by its part, because
	the whole of it needs a newer frappe-ui than the one we pin."""
	for path in [*_vue(), *(p for p in SRC.rglob("*.js") if not tree.vendored(p)), *PORTAL.rglob("*.js")]:
		found = tailwind_tokens(path.read_text(encoding="utf-8"))
		assert not found, f"{_name(path)} {found[0]}"


BRIDGE = ("xcall", "format_currency", "set_route", "doc_subscribe", "realtime.on")


def bridge_problems(sources: dict[str, str], desk: str) -> list[str]:
	"""The screens (by name) that reach into desk past the kit, and what the
	kit's bridge, kit/desk.js, no longer carries. Pure."""
	out = [name for name, source in sources.items() if Path(name).name != "desk.js" and "window." in source]
	return out + [part for part in BRIDGE if part not in desk]


def test_only_the_kit_reaches_into_desk():
	"""Desk's words, formats, calls, routes and realtime come through one
	bridge, kit/desk.js, so an island never redoes what desk does."""
	sources = {str(path.relative_to(SRC)): path.read_text(encoding="utf-8") for path in [p for p in [*SRC.rglob("*.vue"), *SRC.rglob("*.js")] if not tree.vendored(p)] if path.name != "desk.js"}
	found = bridge_problems(sources, (SRC / "kit" / "desk.js").read_text(encoding="utf-8"))
	assert not found, f"these reach into desk past the kit, or the kit lacks them: {found}"


def untranslated(source: str) -> list[str]:
	"""The words a screen's template says without desk's `__`. Pure."""
	template = re.search(r"<template>(.*)</template>", source, re.S).group(1)
	return [text.strip() for text in re.findall(r">([^<>{}]+)<", template) if re.search(r"[A-Za-z]{2,}", text.strip())]


def test_what_an_island_says_is_translated():
	"""Every word on an island goes through desk's `__`, which frappe's own
	extractor reads in .vue files (babel_extractors.csv), so it reaches the POT
	like any other string."""
	for path in sorted([*SRC.rglob("*.vue"), *PORTAL.rglob("*.vue")]):
		found = untranslated(path.read_text(encoding="utf-8"))
		assert not found, f"{path.name} says {found[0]!r} untranslated"


TICKED = {"project/TaskPanel.vue"}
PICKS = {"mail/MailList.vue", "cloud/CloudItems.vue"}
"""Rows picked to act on together, as frappe's list view picks them."""


def draws_a_checkbox(name: str, source: str) -> bool:
	"""Whether a screen draws a Checkbox where a Switch belongs: anywhere but a
	step ticked off (TICKED) or rows picked in a list (PICKS). Pure."""
	return name not in TICKED | PICKS and "<Checkbox" in source


def test_a_setting_is_a_switch():
	"""Something on or off, a field's Check or a filter, is frappe-ui's Switch
	(set by the user on 2026-10-12). A Checkbox is only a step ticked off,
	or rows picked in a list."""
	for path in _vue():
		name = str(_name(path))
		assert not draws_a_checkbox(name, path.read_text(encoding="utf-8")), f"{name} draws a checkbox; use frappe-ui's Switch"


def modelled_in(text: str) -> dict[str, str]:
	"""docs/ISLANDS.md's table, read from its text: each screen, by its path
	under frontend/, and the app it follows. Pure."""
	table = text.split("## What each screen follows", 1)[1]
	return dict(re.findall(r"^\| `([^`]+)` \| (.+?) \|$", table, re.M))


def _modelled() -> dict[str, str]:
	return modelled_in((tree.ROOT / "docs" / "ISLANDS.md").read_text(encoding="utf-8"))


def screens_of(entries: list[str]) -> set[str]:
	"""The screens the islands' entries import, by their path under frontend/.
	Pure."""
	return {f"src/{component}" for entry in entries for component in re.findall(r'import \w+ from "\.\./([\w/]+\.vue)"', entry)}


def unmodelled(screens: set[str], modelled: dict[str, str]) -> list[str]:
	"""The screens docs/ISLANDS.md does not say an app for, and the ones it
	says too little of. Pure."""
	return sorted(screens - set(modelled)) + [path for path, said in modelled.items() if len(said) <= 10]


def test_a_screen_names_the_app_it_follows():
	"""A screen of our own is drawn after the app people already use for the
	same job (Shopify's inventory, Linear's issues), not invented, and
	docs/ISLANDS.md says which."""
	screens = screens_of([(FRONTEND / source).read_text(encoding="utf-8") for source in _entries().values()])
	assert screens, "no screens found"
	modelled = _modelled()
	assert not unmodelled(screens, modelled), f"say in docs/ISLANDS.md what these follow: {unmodelled(screens, modelled)}"
	gone = [path for path in modelled if not (FRONTEND / path).exists()]
	assert not gone, f"docs/ISLANDS.md names screens that are gone: {gone}"


BADGE_THEMES = {"gray", "blue", "green", "amber", "red", "violet"}


def wrong_badges(name: str, text: str) -> list[str]:
	"""The colours a screen names for a badge or a status that frappe-ui's
	Badge does not draw. Pure."""
	wrong = [colour for colour in re.findall(r'(?<!:)theme="(\w+)"', text) + re.findall(r'\btheme: "(\w+)"', text) if colour not in BADGE_THEMES]
	if '"orange"' in text and Path(name).name != "PlaceSpot.vue":
		wrong.append("orange")
	return wrong


def test_a_badge_is_a_colour_frappe_ui_has():
	"""frappe-ui's Badge has no orange: a badge given it falls back to gray, so
	a warning reads as nothing. Every colour named for a badge or a status in a
	screen is one Badge draws."""
	wrong = [f"{_name(path)}: {colour}" for path in _vue() for colour in wrong_badges(str(path), path.read_text(encoding="utf-8"))]
	assert not wrong, wrong


def test_a_portal_page_names_the_app_it_follows():
	"""The portal's pages (frontend/portal) are screens too: each has its row
	in docs/ISLANDS.md."""
	portal = FRONTEND / "portal" / "src"
	pages = {str(path.relative_to(FRONTEND)) for path in [portal / "App.vue", *sorted((portal / "pages").glob("*.vue"))]}
	found = sorted(pages - set(_modelled()))
	assert not found, f"these don't say which app they follow: {found}"


def old_dialog(source: str) -> list[str]:
	"""A Dialog filled or titled as frappe-ui before 1.0 had it. Pure."""
	out = []
	if "#body-content" in source:
		out.append("fills a slot Dialog no longer has; use the default slot")
	if ':options="{ title' in source:
		out.append("titles a Dialog the old way; use :title")
	return out


def test_a_dialog_is_drawn_with_frappe_ui_1s_slots():
	"""frappe-ui 1.0's Dialog takes its title as a prop and its body in the
	default slot. The old `options.title` and `#body-content` build without
	complaint and draw an empty box with no title."""
	for path in _vue():
		found = old_dialog(path.read_text(encoding="utf-8"))
		assert not found, f"{_name(path)} {found[0]}"


def test_the_island_rules_catch_their_examples():
	page = 'onedesk.island_page(wrapper, { island: "onedesk.stock" });'
	assert not island_problems("onedesk.stock", 'import { screen } from "../kit"; screen(Stock);', {"stock.js": page}, [], [], [], [])
	assert island_problems("stock", "mount(Stock)", {"stock.js": 'island: "stock"'}, [], [], [], []) == [
		"stock is not named onedesk.*",
		"stock's entry is not a kit screen",
		"stock.js",
	]
	assert island_problems("onedesk.lost", 'from "../kit"; screen(Lost)', {}, ['mount_island("onedesk.lost")'], [], [], [])[-1].startswith("no desk page")
	good = ({"build": "yarn --cwd frontend build", "postinstall": "yarn --cwd frontend install --frozen-lockfile"}, {"build": "node build-islands.mjs --production && cd portal && vite build"})
	deps = {"frappe-ui": "1.0.3", "@framework/ui": "link:../../frappe/ui"}
	assert not build_problems({"scripts": good[0]}, {"scripts": good[1], "dependencies": deps})
	assert build_problems({"scripts": {}}, {"scripts": good[1], "dependencies": {**deps, "frappe-ui": "^1.0"}}) == [
		"the app's build does not build frontend/",
		"installing the app does not install frontend/ from its lockfile",
		"frappe-ui is not pinned",
	]
	assert own_parts('<div style="color: #f00"></div><style></style>\nimport x from "lodash"') == [
		"styles itself; use frappe-ui's tokens",
		"names a colour",
		"styles an element",
		"imports lodash",
	]
	assert not own_parts('<Button class="bg-surface-gray-2" />\nimport { Button } from "frappe-ui"')
	assert tailwind_tokens('<div class="rounded-lg bg-surface-white" />\nimport { a } from "@framework/ui"') == [
		"uses Tailwind's corners; use rounded-1 to rounded-7",
		"uses surface-white; use surface-base or surface-elevation-1",
		"imports all of @framework/ui; import the part",
	]
	assert not tailwind_tokens('<div class="rounded-3 bg-surface-base" />')
	assert bridge_problems({"stock/Stock.vue": "window.frappe.call()", "kit/desk.js": "window.frappe"}, "xcall") == ["stock/Stock.vue", *BRIDGE[1:]]
	assert not bridge_problems({"stock/Stock.vue": "desk.call()"}, " ".join(BRIDGE))
	assert untranslated("<template><p>Stock</p><p>{{ __('Stock') }}</p></template>") == ["Stock"]
	assert draws_a_checkbox("stock/Stock.vue", "<Checkbox v-model='on' />")
	assert not draws_a_checkbox("mail/MailList.vue", "<Checkbox />")
	modelled = modelled_in("# x\n## What each screen follows\n\n| `src/stock/Stock.vue` | Shopify's inventory |\n| `src/a/A.vue` | Linear |\n")
	assert modelled == {"src/stock/Stock.vue": "Shopify's inventory", "src/a/A.vue": "Linear"}
	assert screens_of(['import Stock from "../stock/Stock.vue"', 'import Mail from "../mail/Mail.vue"']) == {"src/stock/Stock.vue", "src/mail/Mail.vue"}
	assert unmodelled({"src/stock/Stock.vue", "src/mail/Mail.vue"}, modelled) == ["src/mail/Mail.vue", "src/a/A.vue"]
	assert wrong_badges("x/Stock.vue", '<Badge theme="orange" /> { theme: "teal" }') == ["orange", "teal", "orange"]
	assert not wrong_badges("x/Stock.vue", '<Badge theme="amber" :theme="colour" />')
	assert old_dialog('<Dialog :options="{ title: x }"><template #body-content /></Dialog>') == [
		"fills a slot Dialog no longer has; use the default slot",
		"titles a Dialog the old way; use :title",
	]
	assert not old_dialog('<Dialog :title="x"><p /></Dialog>')
