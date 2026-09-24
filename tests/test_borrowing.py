"""If the framework ships it, we do not write our own.

A named list, not a heuristic: "is this a reimplementation" is a judgement, and
a judgement belongs somewhere a person has to edit on purpose. Adding a rule
here is how we record that we looked.
"""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

#: (what, use this instead, pattern that must not appear, which suffixes)
RULES = [
	(
		"dialogs and prompts",
		"frappe.msgprint, frappe.confirm, frappe.prompt, frappe.ui.Dialog",
		r"\bwindow\.(alert|confirm|prompt)\s*\(|(?<![.\w])(alert|confirm)\s*\(",
		{".js", ".ts", ".vue"},
	),
	(
		"fetching",
		"frappe.call, frappe.db, frappe.client",
		r"\b(fetch|XMLHttpRequest)\s*\(|\baxios\b",
		{".js", ".ts", ".vue"},
	),
	(
		"dates and numbers",
		"frappe.datetime, frappe.format, frappe.utils",
		r"\.toLocale(Date|Time|)String\s*\(|\bIntl\.(DateTimeFormat|NumberFormat)\b",
		{".js", ".ts", ".vue"},
	),
	(
		"realtime",
		"frappe.realtime",
		r"\bnew\s+WebSocket\s*\(|\bio\s*\(\s*['\"]",
		{".js", ".ts", ".vue"},
	),
	(
		"per-user state",
		"frappe.model.user_settings, or a doctype",
		r"\b(localStorage|sessionStorage)\b",
		{".js", ".ts", ".vue"},
	),
	(
		"colours and sizes",
		"the espresso tokens — var(--ink-*), var(--surface-*), var(--outline-*)",
		r"(?<![\w-])#[0-9a-fA-F]{3,8}\b|\brgba?\s*\(",
		{".vue", ".css", ".scss"},
	),
	(
		"icons",
		"frappe.utils.icon(name) — Lucide, or a Custom Icon in fixtures/custom_icon.json",
		r"<svg\b",
		{".js", ".ts", ".vue", ".html", ".py"},
	),
	(
		"permission checks",
		"frappe.has_permission, frappe.only_for, doctype permissions",
		r"\bif\s+frappe\.session\.user\s*(==|!=)\s*['\"](?!Guest)",
		{".py"},
	),
]


#: Where a literal colour is the point rather than a mistake. theme.css defines
#: the tokens everything on the desk is told to use; portal.css defines a second,
#: smaller set for /start and /welcome, which are not desk screens and load none
#: of espresso.
DEFINES_TOKENS = (
	"onedesk/public/css/theme.css",
	"onedesk/public/css/portal.css",
)


#: (rule, file) pairs where we looked and the framework has nothing. The
#: explorer PUTs a file's bytes straight to a URL R2 signed, on another
#: origin, and shows its progress; frappe.call only posts to this site, and
#: FileUploader only to upload_file.
LOOKED = {
	("fetching", "onedesk/one_storage/page/onecloud/onecloud.js"),
}


def _offenders(pattern: str, suffixes: set[str], what: str = "") -> list[str]:
	found = []
	for path in tree.sources():
		if path.suffix not in suffixes:
			continue
		if str(path.relative_to(tree.ROOT)) in DEFINES_TOKENS:
			continue
		if (what, str(path.relative_to(tree.ROOT))) in LOOKED:
			continue
		for n, line in enumerate(path.read_text().splitlines(), 1):
			if _is_comment(line, path.suffix):
				continue
			if re.search(pattern, line):
				found.append(f"{path.relative_to(tree.ROOT)}:{n}: {line.strip()}")
	return found


def _is_comment(line: str, suffix: str) -> bool:
	stripped = line.lstrip()
	return stripped.startswith("#" if suffix == ".py" else ("//", "*", "/*"))


@pytest.mark.parametrize("what,instead,pattern,suffixes", RULES, ids=[r[0] for r in RULES])
def test_the_framework_does_this_for_us(what, instead, pattern, suffixes):
	hits = _offenders(pattern, suffixes, what)
	assert not hits, f"{what} — use {instead} instead:\n" + "\n".join(hits)


def test_every_rule_would_catch_its_own_example():
	"""A pattern that matches nothing is a guard that has stopped guarding."""
	examples = {
		"dialogs and prompts": "window.confirm('sure?')",
		"fetching": "const r = await fetch('/api/method/ping')",
		"dates and numbers": "d.toLocaleDateString('en-GB')",
		"realtime": "const s = new WebSocket('wss://x')",
		"per-user state": "localStorage.setItem('tab', tab)",
		"colours and sizes": "color: #1a1a1a;",
		"icons": '<svg viewBox="0 0 16 16"><path d="M4 4l8 8" /></svg>',
		"permission checks": "if frappe.session.user == 'admin@example.com':",
	}
	for what, _instead, pattern, _suffixes in RULES:
		assert re.search(pattern, examples[what]), f"{what} no longer matches its example"


#: The sprite the desk loads: Lucide as frappe ships it, then every Custom Icon.
LUCIDE = Path("/home/frappe/bench1/apps/frappe/frappe/public/icons/lucide/icons.svg")

#: How an icon is named in our code: the Icon component, or frappe's own call.
NAMED = (
	r"<Icon\s+name=\"([\w-]+)\"",
	r"<Icon\s+:name=\"[^\"]*\"",  # a ternary: every quoted name inside it
	r"frappe\.utils\.icon\(\s*['\"]([\w-]+)['\"]",
)


def _named() -> dict[str, str]:
	found = {}
	for path in tree.sources():
		if path.suffix not in {".js", ".vue"}:
			continue
		text = path.read_text()
		for match in re.finditer(NAMED[0], text):
			found[match.group(1)] = str(path.relative_to(tree.ROOT))
		for match in re.finditer(NAMED[1], text):
			for name in re.findall(r"[?:]\s*'([\w-]+)'", match.group(0)):
				found[name] = str(path.relative_to(tree.ROOT))
		for match in re.finditer(NAMED[2], text):
			found[match.group(1)] = str(path.relative_to(tree.ROOT))
		# A lookup table of names, like the record card's glyphs.
		for block in re.findall(r"// .*Lucide.*\n(?:.*\n){0,3}", text):
			for name in re.findall(r"\"([a-z][\w-]+)\"", block):
				found[name] = str(path.relative_to(tree.ROOT))
	return found


def test_every_icon_is_in_the_sprite():
	"""A name the sprite lacks draws nothing, silently. Lucide or a fixture."""
	if not LUCIDE.exists():
		pytest.skip("no frappe checkout beside this one")
	have = set(re.findall(r'id="icon-([\w-]+)"', LUCIDE.read_text()))
	custom = json.loads((tree.APP / "fixtures" / "custom_icon.json").read_text())
	have |= {one["icon_name"] for one in custom}
	missing = {name: where for name, where in _named().items() if name not in have}
	assert not missing, "not in Lucide or fixtures/custom_icon.json:\n" + "\n".join(
		f"  {name} ({where})" for name, where in sorted(missing.items())
	)
