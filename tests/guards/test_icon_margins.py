"""An icon beside text in a note sits at the start of the row, next to its
words. frappe gives every `.icon` `margin: 0 auto`, and in a flex row an auto
margin takes the free space, so a rule that moves an icon only up or down
(`margin-top: 2px`) leaves both side margins on auto, and a short note comes
out with its icon floating in the middle and its words pushed to the far side.
A rule of ours that sets an icon's margin sets all four sides."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRAPPE_ICONS = ROOT.parent / "frappe" / "frappe" / "public" / "scss" / "common" / "icons.scss"
SOURCES = (ROOT / "onedesk" / "public", ROOT / "frontend" / "src")
SUFFIXES = (".css", ".scss", ".less", ".vue")
UP_OR_DOWN = {"margin-top", "margin-bottom", "margin-block", "margin-block-start", "margin-block-end"}
SIDES = {"margin", "margin-inline", "margin-left", "margin-right", "margin-inline-start", "margin-inline-end"}
ICON = re.compile(r"\.icon(?![\w-])(:[\w-]+(\([^)]*\))?)*\s*$")


def _rules(text: str):
	text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
	for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", text):
		yield text[: match.start()].count("\n") + 1, match.group(1).strip(), match.group(2)


def _lopsided(text: str) -> list[str]:
	found = []
	for line, selector, body in _rules(text):
		if not any(ICON.search(part.strip()) for part in selector.split(",")):
			continue
		props = set(re.findall(r"(?:^|;)\s*([\w-]+)\s*:", body))
		if props & UP_OR_DOWN and not props & SIDES:
			found.append(f"{line}: {' '.join(selector.split())}")
	return found


def test_frappe_still_centres_icons():
	assert re.search(r"\.icon\s*\{[^}]*margin:\s*0 auto", FRAPPE_ICONS.read_text()), (
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


def test_the_scan_would_catch_one():
	assert _lopsided(".x .note .icon {\n\tmargin-top: 2px;\n}")
	assert _lopsided(".x svg.icon:first-child { margin-bottom: 1px }")
	assert not _lopsided(".x .note .icon { margin: 2px 0 0; }")
	assert not _lopsided(".x .icon-sm { margin-top: 2px; }")
