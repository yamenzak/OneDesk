"""Point 8: every value shown goes through frappe's formatting, so the
workspace's date, number and currency settings and the field's own precision
apply. Only the kit may wrap frappe's formatters (frontend/src/kit/desk.js)."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import tree

BY_HAND = re.compile(r"toLocale(?:Date|Time)?String\(|new Intl\.|\.toFixed\(")

KIT = {"frontend/src/kit/desk.js"}


def _views():
	for base in ("frontend/src", "onedesk/public/js"):
		for path in (ROOT / base).rglob("*"):
			if path.suffix in (".js", ".vue") and "/dist/" not in str(path) and not tree.vendored(path):
				yield path


def test_nothing_is_formatted_by_hand():
	found = {str(path.relative_to(ROOT)) for path in _views() if BY_HAND.search(path.read_text())}
	assert found - KIT == set(), sorted(found - KIT)


CHART = re.compile(r"<(BarChart|AreaChart|LineChart|DonutChart|FunnelChart|HeatmapChart|ScatterChart|SankeyChart|NumberCard)\b([^>]*)>", re.S)


def test_every_chart_prints_through_frappe():
	"""A frappe-ui chart left without a `format` prints its numbers the
	browser's way, not in the workspace's number format or the company's
	currency. Each one is given the kit's formatter (`money`, `count`,
	`hours`), on itself, an axis or a series, or through `v-bind`."""
	bare = [f"{path.relative_to(ROOT)}: {chart}" for path in _views() if path.suffix == ".vue" for chart in unformatted(path.read_text())]
	assert not bare, bare


def unformatted(source: str) -> list[str]:
	"""The charts in a screen's source given no formatter. Pure."""
	return [match.group(1) for match in CHART.finditer(source) if not re.search(r"format|v-bind=", match.group(2))]


def test_the_format_rules_catch_their_examples():
	assert BY_HAND.search("total.toFixed(2)") and BY_HAND.search("new Intl.NumberFormat()") and BY_HAND.search("d.toLocaleDateString()")
	assert not BY_HAND.search("frappe.format(total, { fieldtype: 'Currency' })")
	assert unformatted('<BarChart :config="c" />\n<LineChart :config="c" :format="money" />') == ["BarChart"]
