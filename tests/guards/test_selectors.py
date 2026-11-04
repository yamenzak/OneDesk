"""Selectors that make every change restyle the page. Chrome re-checks a
`:has()` rule whenever something it looks for might have changed. Three
shapes make that "anything, anywhere", so typing one letter restyled 26,000
elements and a phone list scrolled at a few frames a second (4 November 2026):

- on the root (`body:has(...)`, `html:has`, `:root:has`), so any change
  re-checks the whole page;
- with a class or attribute matched by part (`[class*="col-"]`) inside it,
  so any class change anywhere might match;
- followed by a combinator to any element (`:has(...) > *`, `> :not(...)`,
  `> :first-child`), so each re-check restyles every child.

Mark the element in the code that makes it instead (`.one-banded`), or put
`:has()` on the element the rule styles."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSS = ROOT / "onedesk" / "public" / "css"

ROOTED = re.compile(r"(^|[\s,(])(html|body|:root)(\[[^\]]*\]|\.[\w-]+|:not\([^)]*\))*:has\(")
PARTIAL = re.compile(r":has\([^{}]*\[[\w-]+[*^$~|]=")
ANY = re.compile(r"^\)*\s*(>|~|\+|\s)\s*(\*|:not\(|:first-child|:last-child|:nth-child)")


def _closing(text: str, at: int) -> int:
	depth = 0
	for i in range(at, len(text)):
		depth += {"(": 1, ")": -1}.get(text[i], 0)
		if depth == 0 and text[i] == ")":
			return i
	return len(text)


def costly(selector: str) -> list[str]:
	"""What makes one selector restyle the page. Pure."""
	why = []
	if ROOTED.search(selector):
		why.append("on the root")
	if PARTIAL.search(selector):
		why.append("a partial match inside")
	at = selector.find(":has(")
	while at >= 0:
		end = _closing(selector, at + 4)
		if ANY.match(selector[end + 1 :]):
			why.append("then any element")
			break
		at = selector.find(":has(", end)
	return why


def _selectors(text: str):
	text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
	for head in re.findall(r"([^{}]+)\{", text):
		for one in head.split(","):
			if ":has(" in one:
				yield one.strip()


def test_each_shape_is_caught():
	assert costly("body:has(.modal.show) .x") == ["on the root"]
	assert costly(":root[data-a] body.b:has(.c) .d") == ["on the root"]
	assert costly(".row:has(> [class*='col-'] > .b)") == ["a partial match inside"]
	assert costly(".row:has(> * > .btn-move) > *") == ["then any element"]
	assert costly(".m:not(:has(.band)) > :not(.icon)") == ["then any element"]
	assert costly(".row:has(> * > .btn-move)") == []
	assert costly(".row > .col-sm-6:has(> .btn-move)") == []


def test_no_rule_of_ours_restyles_the_page():
	found = []
	for path in sorted(CSS.rglob("*.css")):
		if "dist" in path.parts:
			continue
		for selector in _selectors(path.read_text(encoding="utf-8")):
			why = costly(selector)
			if why:
				found.append(f"{path.relative_to(ROOT)}: {selector[:120]} ({', '.join(why)})")
	assert not found, "\n".join(found)
