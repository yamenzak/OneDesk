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


def _vue() -> list[Path]:
	return sorted(SRC.rglob("*.vue"))


def test_every_island_is_declared_built_and_mounted():
	entries = _entries()
	assert entries, "no islands built"
	# frappe's hook for naming them is gone; a line in it would name nothing.
	assert "ui_islands" not in HOOKS
	for name, source in entries.items():
		assert name.startswith("onedesk."), name
		entry = (FRONTEND / source).read_text(encoding="utf-8")
		# Every island mounts through the kit, so `__` and the mount contract are
		# the same everywhere.
		assert 'from "../kit"' in entry and "screen(" in entry, name
		# And a desk page mounts it through onedesk.island_page, which keeps the head.
		pages = [
			path
			for path in tree.APP.glob("*/page/*/*.js")
			if f'island: "{name}"' in path.read_text(encoding="utf-8")
		]
		assert pages, f"no desk page mounts {name}"
		for page in pages:
			assert "onedesk.island_page(" in page.read_text(encoding="utf-8"), page


def test_bench_build_builds_the_islands():
	root = json.loads((tree.ROOT / "package.json").read_text())
	assert root["scripts"]["build"] == "yarn --cwd frontend build"
	assert "frontend install --frozen-lockfile" in root["scripts"]["postinstall"]
	frontend = json.loads((FRONTEND / "package.json").read_text())
	assert frontend["scripts"]["build"] == "node build-islands.mjs --production"
	# One frappe-ui for every island, pinned: an upgrade is a decision.
	assert re.fullmatch(r"\d+\.\d+\.\d+", frontend["dependencies"]["frappe-ui"])
	assert frontend["dependencies"]["@framework/ui"] == "link:../../frappe/ui"
	assert (FRONTEND / "yarn.lock").exists()


def test_an_island_is_frappe_ui_and_nothing_of_its_own():
	"""A screen is frappe-ui's components laid out with its tokens. No style of
	its own, no colour of its own, no part from anywhere else."""
	allowed = re.compile(r'^(vue|frappe-ui(/[\w-]+)?|@framework/ui(/[\w/-]+)?|\.{1,2}/[\w./-]+)$')
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
	for path in [*SRC.rglob("*.vue"), *SRC.rglob("*.js")]:
		source = path.read_text(encoding="utf-8")
		name = path.relative_to(SRC)
		assert not re.search(r"(?<![\w-])rounded(-(sm|md|lg|xl|2xl))?(?![\w-])", source), f"{name} uses Tailwind's corners; use rounded-1 to rounded-7"
		assert not re.search(r"\b(bg|ring|border)-surface-white\b", source), f"{name} uses surface-white; use surface-base or surface-elevation-1"
		assert 'from "@framework/ui"' not in source, f"{name} imports all of @framework/ui; import the part"


def test_only_the_kit_reaches_into_desk():
	"""Desk's words, formats, calls, routes and realtime come through one
	bridge, kit/desk.js, so an island never redoes what desk does."""
	for path in [*SRC.rglob("*.vue"), *SRC.rglob("*.js")]:
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
	for path in _vue():
		template = re.search(r"<template>(.*)</template>", path.read_text(encoding="utf-8"), re.S).group(1)
		# Text between tags, outside {{ }}, is a word nobody translates.
		for text in re.findall(r">([^<>{}]+)<", template):
			words = text.strip()
			assert not re.search(r"[A-Za-z]{2,}", words), f"{path.name} says {words!r} untranslated"
