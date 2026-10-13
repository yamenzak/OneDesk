"""Point 8: every value shown goes through frappe's formatting, so the
workspace's date, number and currency settings and the field's own precision
apply. Only the kit may wrap frappe's formatters (frontend/src/kit/desk.js)."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BY_HAND = re.compile(r"toLocale(?:Date|Time)?String\(|new Intl\.|\.toFixed\(")

#: Where formatting by hand is allowed: the kit wraps frappe's formatters.
KIT = {"frontend/src/kit/desk.js"}


def _views():
	for base in ("frontend/src", "onedesk/public/js"):
		for path in (ROOT / base).rglob("*"):
			if path.suffix in (".js", ".vue") and "/dist/" not in str(path):
				yield path


def test_nothing_is_formatted_by_hand():
	found = {str(path.relative_to(ROOT)) for path in _views() if BY_HAND.search(path.read_text())}
	assert found - KIT == set(), sorted(found - KIT)


#: frappe-ui's charts and number card: each prints numbers.
CHART = re.compile(r"<(BarChart|AreaChart|LineChart|DonutChart|FunnelChart|HeatmapChart|ScatterChart|SankeyChart|NumberCard)\b([^>]*)>", re.S)


def test_every_chart_prints_through_frappe():
	"""A frappe-ui chart left without a `format` prints its numbers the
	browser's way, not in the workspace's number format or the company's
	currency. Each one is given the kit's formatter (`money`, `count`,
	`hours`), on itself, an axis or a series, or through `v-bind`."""
	bare = []
	for path in _views():
		if path.suffix != ".vue":
			continue
		for match in CHART.finditer(path.read_text()):
			attrs = match.group(2)
			if not re.search(r"format|v-bind=", attrs):
				bare.append(f"{path.relative_to(ROOT)}: {match.group(1)}")
	assert not bare, bare
