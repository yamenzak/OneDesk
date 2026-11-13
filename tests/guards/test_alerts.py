"""Every alert is the form's card: soft grey, the colour only in a round icon,
the fix as an outline button. On the desk it is drawn by onedesk.alert (or
frappe's set_intro, which head.js marks the same way), in an island by the
kit's OneAlert; desk.css styles all of them as one. A box of our own, tinted
amber or red with its own icon and its own link, is how the same warning came
out three different ways on three screens, so these fail on one.

An icon beside text in a note sits at the start of the row, next to its
words. frappe gives every `.icon` `margin: 0 auto`, and in a flex row an auto
margin takes the free space, so a rule that moves an icon only up or down
(`margin-top: 2px`) leaves both side margins on auto, and a short note comes
out with its icon floating in the middle and its words pushed to the far side.
A rule of ours that sets an icon's margin sets all four sides."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK_JS = ROOT / "onedesk" / "public" / "js"
DESK_CSS = ROOT / "onedesk" / "public" / "css"
ISLANDS = ROOT / "frontend" / "src"
NOT_THE_DESK = ("portal", "sheet/", "one_print", "print_format")
NOTE_CLASS = r"[\w-]*(note|notice|alert|warn|warning|banner|callout)[\w-]*"
TINT = r"(red|amber|orange|yellow|green|blue)-[12]"
NOT_ALERTS = {".one-ai-mic--on": "the microphone button, lit while it listens"}


def _files(base: Path, *suffixes: str):
	for path in sorted(base.rglob("*")):
		rel = path.relative_to(ROOT).as_posix()
		if path.suffix in suffixes and "node_modules" not in path.parts and not any(part in rel for part in NOT_THE_DESK):
			yield rel, path.read_text(errors="ignore")


def _tinted_notes(css: str) -> list[str]:
	css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
	return [
		" ".join(selector.split())
		for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
		if " ".join(selector.split()) not in NOT_ALERTS
		and re.search(rf"background[^;]*--surface-{TINT}", body)
		and re.search(r"(^|;)\s*color[^;]*--ink-(red|amber|orange|yellow|green|blue)", body)
	]


def _icons_in_notes(js: str) -> list[str]:
	return [
		match.group(0)[:80]
		for match in re.finditer(rf'class="(?![^"]*one-alert-icon)[^"]*\b{NOTE_CLASS}[^"]*">\s*\$\{{\s*frappe\.utils\.icon\(', js)
	]


def _tinted_boxes(vue: str) -> list[str]:
	return [
		match.group(1)[:80]
		for match in re.finditer(r'<div\b[^>]*\bclass="([^"]*)"', vue)
		if re.search(rf"\bbg-surface-{TINT}\b", match.group(1))
		and re.search(r"\brounded(-\d)?(?![\w-])", match.group(1))
		and re.search(r"\btext-ink-(red|amber|orange|yellow|green|blue)-", match.group(1))
	]


def _imports_alert(text: str) -> bool:
	return bool(re.search(r"import\s*\{[^}]*\bAlert\b[^}]*\}\s*from\s*[\"']frappe-ui[\"']", text))


def test_islands_draw_alerts_with_one_alert():
	bad = [rel for rel, text in _files(ISLANDS, ".vue", ".js") if _imports_alert(text)]
	assert not bad, "frappe-ui's Alert is a different card from the desk's; use the kit's OneAlert:\n" + "\n".join(bad)


def test_no_tinted_note_of_our_own():
	bad = [f"{rel}: {selector}" for rel, text in _files(DESK_CSS, ".css") for selector in _tinted_notes(text)]
	bad += [f"{rel}: {box}" for rel, text in _files(ISLANDS, ".vue") for box in _tinted_boxes(text)]
	assert not bad, "A note tinted by hand; draw it with onedesk.alert or OneAlert:\n" + "\n".join(bad)


def test_no_icon_dropped_into_a_note():
	bad = [f"{rel}: {hit}" for rel, text in _files(DESK_JS, ".js") for hit in _icons_in_notes(text)]
	assert not bad, "A note built by hand with its own icon; use onedesk.alert:\n" + "\n".join(bad)


def test_the_scans_would_catch_one():
	assert _tinted_notes(".rb .rb-unread { background: var(--surface-amber-2); color: var(--ink-amber-8); }")
	assert not _tinted_notes(".rb .rb-row { background: var(--surface-amber-2); color: var(--ink-gray-8); }")
	assert _icons_in_notes('`<div class="oms-note">${frappe.utils.icon("info", "sm")}`')
	assert not _icons_in_notes('`<span class="one-alert-icon">${frappe.utils.icon(icon, "sm")}`')
	assert _tinted_boxes('<div v-if="x" class="rounded-3 bg-surface-red-1 px-2 text-ink-red-7">')
	assert not _tinted_boxes('<div class="rounded-full bg-surface-red-2 text-ink-red-7">')
	assert _imports_alert('import { Button, Alert } from "frappe-ui"')
	assert not _imports_alert('import OneAlert from "../kit/OneAlert.vue"')


FRAPPE_ICONS = ROOT.parent / "frappe" / "frappe" / "public" / "scss" / "common" / "icons.scss"
SOURCES = (ROOT / "onedesk" / "public", ROOT / "frontend" / "src")
SUFFIXES = (".css", ".scss", ".less", ".vue")
UP_OR_DOWN = {"margin-top", "margin-bottom", "margin-block", "margin-block-start", "margin-block-end"}
SIDES = {"margin", "margin-inline", "margin-left", "margin-right", "margin-inline-start", "margin-inline-end"}
RULE = re.compile(r"(?<![^{}])([^{}]+)\{([^{}]*)\}")
"""A selector and its body. Only a brace or the text's start can begin one, so
looking only there finds the same rules without trying every letter."""
ICON = re.compile(r"\.icon(?![\w-])(:[\w-]+(\([^)]*\))?)*\s*$")


def _rules(text: str):
	text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
	line, read = 1, 0
	for match in RULE.finditer(text):
		line, read = line + text.count("\n", read, match.start()), match.start()
		yield line, match.group(1).strip(), match.group(2)


def _lopsided(text: str) -> list[str]:
	found = []
	for line, selector, body in _rules(text):
		if not any(ICON.search(part.strip()) for part in selector.split(",")):
			continue
		props = set(re.findall(r"(?:^|;)\s*([\w-]+)\s*:", body))
		if props & UP_OR_DOWN and not props & SIDES:
			found.append(f"{line}: {' '.join(selector.split())}")
	return found


def _centres_icons(scss: str) -> bool:
	return bool(re.search(r"\.icon\s*\{[^}]*margin:\s*0 auto", scss))


def test_frappe_still_centres_icons():
	assert _centres_icons(FRAPPE_ICONS.read_text()), (
		"frappe no longer gives .icon `margin: 0 auto`; this guard's reason is gone, so revisit it"
	)


def test_an_icon_margin_sets_its_sides():
	bad = [
		f"{path.relative_to(ROOT)}:{where}"
		for base in SOURCES
		for path in sorted(base.rglob("*"))
		if path.suffix in SUFFIXES and "node_modules" not in path.parts and "dist" not in path.parts
		for where in _lopsided(path.read_text(errors="ignore"))
	]
	assert not bad, (
		"These set an icon's top or bottom margin and leave its sides on frappe's `auto`, "
		"which pushes the icon away from its words. Write `margin: <top> 0 0`:\n" + "\n".join(bad)
	)


def test_the_margin_scan_would_catch_one():
	assert _lopsided(".x .note .icon {\n\tmargin-top: 2px;\n}")
	assert _lopsided(".x svg.icon:first-child { margin-bottom: 1px }")
	assert not _lopsided(".x .note .icon { margin: 2px 0 0; }")
	assert not _lopsided(".x .icon-sm { margin-top: 2px; }")
	assert _centres_icons(".icon {\n\tmargin: 0 auto;\n}")
	assert not _centres_icons(".icon {\n\tmargin: 0;\n}")
