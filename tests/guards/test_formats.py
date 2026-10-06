"""Point 8: every value shown goes through frappe's formatting, so the
workspace's date, number and currency settings and the field's own precision
apply. Only the kit may wrap frappe's formatters (frontend/src/kit/desk.js)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BY_HAND = re.compile(r"toLocale(?:Date|Time)?String\(|new Intl\.|\.toFixed\(")

#: Where formatting by hand is allowed: the kit wraps frappe's formatters.
KIT = {"frontend/src/kit/desk.js"}

#: Found when this guard was written, to be routed through frappe (ARC 4).
KNOWN = {
	"onedesk/public/js/onemail.js",
	"onedesk/public/js/onecloud.js",
	"onedesk/public/js/oneai/Panel.vue",
	"onedesk/public/js/one_drop.js",
	"onedesk/public/js/desk.js",
}


def _views():
	for base in ("frontend/src", "onedesk/public/js"):
		for path in (ROOT / base).rglob("*"):
			if path.suffix in (".js", ".vue") and "/dist/" not in str(path):
				yield path


def test_nothing_is_formatted_by_hand():
	found = {str(path.relative_to(ROOT)) for path in _views() if BY_HAND.search(path.read_text())}
	assert found - KIT - KNOWN == set(), sorted(found - KIT - KNOWN)
	assert KNOWN <= found, sorted(KNOWN - found)
