"""If the framework ships it, we do not write our own.

A named list, not a heuristic: "is this a reimplementation" is a judgement, and
a judgement belongs somewhere a person has to edit on purpose. Adding a rule
here is how we record that we looked.
"""

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


def _offenders(pattern: str, suffixes: set[str]) -> list[str]:
	found = []
	for path in tree.sources():
		if path.suffix not in suffixes:
			continue
		if str(path.relative_to(tree.ROOT)) in DEFINES_TOKENS:
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
	hits = _offenders(pattern, suffixes)
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
		"permission checks": "if frappe.session.user == 'admin@example.com':",
	}
	for what, _instead, pattern, _suffixes in RULES:
		assert re.search(pattern, examples[what]), f"{what} no longer matches its example"
