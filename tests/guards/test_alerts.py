"""Every alert is the form's card: soft grey, the colour only in a round icon,
the fix as an outline button. On the desk it is drawn by onedesk.alert (or
frappe's set_intro, which head.js marks the same way), in an island by the
kit's OneAlert; desk.css styles all of them as one. A box of our own, tinted
amber or red with its own icon and its own link, is how the same warning came
out three different ways on three screens, so these fail on one."""

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


def test_islands_draw_alerts_with_one_alert():
	bad = [
		rel
		for rel, text in _files(ISLANDS, ".vue", ".js")
		if re.search(r"import\s*\{[^}]*\bAlert\b[^}]*\}\s*from\s*[\"']frappe-ui[\"']", text)
	]
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
