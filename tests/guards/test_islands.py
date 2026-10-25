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
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


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


def test_every_island_is_declared_built_and_mounted():
	entries = _entries()
	assert entries, "no islands built"
	assert "ui_islands" not in HOOKS
	for name, source in entries.items():
		assert name.startswith("onedesk."), name
		entry = (FRONTEND / source).read_text(encoding="utf-8")
		assert 'from "../kit"' in entry and "screen(" in entry, name
		pages = [
			path
			for path in tree.APP.glob("*/page/*/*.js")
			if f'island: "{name}"' in path.read_text(encoding="utf-8")
		]
		tabs = [
			path
			for path in (tree.APP / "public" / "js").glob("*.js")
			if f'mount_island("{name}"' in path.read_text(encoding="utf-8")
			and (
				"onedesk.record_tabs.register(" in path.read_text(encoding="utf-8")
				or "onedesk.check.report = " in path.read_text(encoding="utf-8")
			)
		]
		reports = [
			path
			for path in tree.APP.glob("*/report/*/*.js")
			if f'mount_island("{name}"' in path.read_text(encoding="utf-8")
		]
		assert pages or tabs or reports, f"no desk page, record tab or report mounts {name}"
		for page in pages:
			assert "onedesk.island_page(" in page.read_text(encoding="utf-8"), page


def test_bench_build_builds_the_islands():
	root = json.loads((tree.ROOT / "package.json").read_text())
	assert root["scripts"]["build"] == "yarn --cwd frontend build"
	assert "frontend install --frozen-lockfile" in root["scripts"]["postinstall"]
	frontend = json.loads((FRONTEND / "package.json").read_text())
	assert frontend["scripts"]["build"] == "node build-islands.mjs --production && cd portal && vite build"
	assert re.fullmatch(r"\d+\.\d+\.\d+", frontend["dependencies"]["frappe-ui"])
	assert frontend["dependencies"]["@framework/ui"] == "link:../../frappe/ui"
	assert (FRONTEND / "yarn.lock").exists()


def test_an_island_is_frappe_ui_and_nothing_of_its_own():
	"""A screen is frappe-ui's components laid out with its tokens. No style of
	its own, no colour of its own, no part from anywhere else."""
	allowed = re.compile(r'^(vue|vue-router|frappe-ui(/[\w-]+)?|@framework/ui(/[\w/-]+)?|\.{1,2}/[\w./-]+)$')
	for path in _vue():
		source = path.read_text(encoding="utf-8")
		assert "<style" not in source, f"{path.name} styles itself; use frappe-ui's tokens"
		assert not re.search(r"#[0-9a-fA-F]{3,8}\b", source), f"{path.name} names a colour"
		assert not re.search(r"\b(text|bg|border)-\[", source), f"{path.name} names a colour"
		assert not re.search(r'\sstyle="', source), f"{path.name} styles an element"
		for specifier in re.findall(r'from "([^"]+)"', source):
			assert allowed.match(specifier), f"{path.name} imports {specifier}"


def test_an_island_uses_frappe_ui_tokens():
	"""frappe-ui 1.0's tokens are not Tailwind's. A class from Tailwind's own
	scale builds without complaint and draws nothing: corners stay square and
	panels see-through. And `@framework/ui` is imported by its part, because
	the whole of it needs a newer frappe-ui than the one we pin."""
	for path in [*_vue(), *(p for p in SRC.rglob("*.js") if not tree.vendored(p)), *PORTAL.rglob("*.js")]:
		source = path.read_text(encoding="utf-8")
		name = _name(path)
		assert not re.search(r"(?<![\w-])rounded(-(sm|md|lg|xl|2xl))?(?![\w-])", source), f"{name} uses Tailwind's corners; use rounded-1 to rounded-7"
		assert not re.search(r"\b(bg|ring|border)-surface-white\b", source), f"{name} uses surface-white; use surface-base or surface-elevation-1"
		assert 'from "@framework/ui"' not in source, f"{name} imports all of @framework/ui; import the part"


def test_only_the_kit_reaches_into_desk():
	"""Desk's words, formats, calls, routes and realtime come through one
	bridge, kit/desk.js, so an island never redoes what desk does."""
	for path in [p for p in [*SRC.rglob("*.vue"), *SRC.rglob("*.js")] if not tree.vendored(p)]:
		if path.name == "desk.js":
			continue
		source = path.read_text(encoding="utf-8")
		assert "window." not in source, f"{path.relative_to(SRC)} reaches into desk; use the kit"
	desk = (SRC / "kit" / "desk.js").read_text(encoding="utf-8")
	for part in ("xcall", "format_currency", "set_route", "doc_subscribe", "realtime.on"):
		assert part in desk, part


def test_what_an_island_says_is_translated():
	"""Every word on an island goes through desk's `__`, which frappe's own
	extractor reads in .vue files (babel_extractors.csv), so it reaches the POT
	like any other string."""
	for path in sorted([*SRC.rglob("*.vue"), *PORTAL.rglob("*.vue")]):
		template = re.search(r"<template>(.*)</template>", path.read_text(encoding="utf-8"), re.S).group(1)
		for text in re.findall(r">([^<>{}]+)<", template):
			words = text.strip()
			assert not re.search(r"[A-Za-z]{2,}", words), f"{path.name} says {words!r} untranslated"


TICKED = {"task/TaskPage.vue", "task/MyTasks.vue", "project/TaskPanel.vue"}
# Rows picked to act on together, as frappe's list view picks them.
PICKS = {"mail/MailList.vue"}


def test_a_setting_is_a_switch():
	"""Something on or off, a field's Check or a filter, is frappe-ui's Switch
	(set by the user on 2026-10-12). A Checkbox is only a step ticked off,
	or rows picked in a list."""
	for path in _vue():
		name = str(_name(path))
		if name in TICKED | PICKS:
			continue
		assert "<Checkbox" not in path.read_text(encoding="utf-8"), f"{name} draws a checkbox; use frappe-ui's Switch"


def _modelled() -> dict[str, str]:
	"""docs/ISLANDS.md's table: each screen, by its path under frontend/, and
	the app it follows."""
	text = (tree.ROOT / "docs" / "ISLANDS.md").read_text(encoding="utf-8")
	table = text.split("## What each screen follows", 1)[1]
	return dict(re.findall(r"^\| `([^`]+)` \| (.+?) \|$", table, re.M))


def test_a_screen_names_the_app_it_follows():
	"""A screen of our own is drawn after the app people already use for the
	same job (Shopify's inventory, Linear's issues), not invented, and
	docs/ISLANDS.md says which."""
	screens = set()
	for source in _entries().values():
		entry = (FRONTEND / source).read_text(encoding="utf-8")
		for component in re.findall(r'import \w+ from "\.\./([\w/]+\.vue)"', entry):
			screens.add(f"src/{component}")
	assert screens, "no screens found"
	modelled = _modelled()
	assert screens <= set(modelled), f"say in docs/ISLANDS.md what these follow: {sorted(screens - set(modelled))}"
	gone = [path for path in modelled if not (FRONTEND / path).exists()]
	assert not gone, f"docs/ISLANDS.md names screens that are gone: {gone}"
	assert all(len(said) > 10 for said in modelled.values())


BADGE_THEMES = {"gray", "blue", "green", "amber", "red", "violet"}


def test_a_badge_is_a_colour_frappe_ui_has():
	"""frappe-ui's Badge has no orange: a badge given it falls back to gray, so
	a warning reads as nothing. Every colour named for a badge or a status in a
	screen is one Badge draws."""
	wrong = []
	for path in _vue():
		text = path.read_text(encoding="utf-8")
		for colour in re.findall(r'(?<!:)theme="(\w+)"', text) + re.findall(r'\btheme: "(\w+)"', text):
			if colour not in BADGE_THEMES:
				wrong.append(f"{_name(path)}: {colour}")
		if '"orange"' in text and path.name != "PlaceSpot.vue":
			wrong.append(f"{_name(path)}: orange")
	assert not wrong, wrong


def test_a_portal_page_names_the_app_it_follows():
	"""The portal's pages (frontend/portal) are screens too: each has its row
	in docs/ISLANDS.md."""
	portal = FRONTEND / "portal" / "src"
	modelled = _modelled()
	for path in [portal / "App.vue", *sorted((portal / "pages").glob("*.vue"))]:
		assert str(path.relative_to(FRONTEND)) in modelled, f"{path.name} doesn't say which app it follows"


def test_a_dialog_is_drawn_with_frappe_ui_1s_slots():
	"""frappe-ui 1.0's Dialog takes its title as a prop and its body in the
	default slot. The old `options.title` and `#body-content` build without
	complaint and draw an empty box with no title."""
	for path in _vue():
		source = path.read_text(encoding="utf-8")
		assert "#body-content" not in source, f"{_name(path)} fills a slot Dialog no longer has; use the default slot"
		assert ':options="{ title' not in source, f"{_name(path)} titles a Dialog the old way; use :title"
