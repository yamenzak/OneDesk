"""A figure is one card everywhere: a small grey label, the number, a line
under it, framed. On the desk it is frappe's own `frappe.ui.stat_card`
(ERPNext's Customer Overview draws the same); on an island it is frappe-ui's
NumberCard in the same frame, through the kit's Figures. A record's head, a
module's Home and a page of ours used to draw three kinds. docs/READY.md,
One figure."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

SRC = tree.ROOT / "frontend" / "src"
JS = tree.APP / "public" / "js"
CSS = (tree.APP / "public" / "css" / "desk.css").read_text(encoding="utf-8")


def test_a_record_head_draws_frappes_stat_card():
	band = (JS / "band.js").read_text(encoding="utf-8")
	assert "frappe.ui.stat_card(" in band, "a head's figure is frappe's stat card"
	assert "desk_charts.bundle.js" in band, "the stat card's bundle is loaded before a head is drawn"
	assert "one-stat-value" not in band and "one-stat-value" not in CSS, "no figure of the head's own"


def test_the_desk_card_reads_as_the_island_card():
	"""frappe-ui's NumberCard: 8px corners and a 20px number."""
	assert re.search(r"body \.es-stat-card \{\s*border-radius: var\(--radius-4\);", CSS)
	assert re.search(r"body \.es-stat-card__value \{\s*font-size: var\(--text-3xl\);", CSS)


def test_an_island_draws_figures_through_the_kit():
	figures = (SRC / "kit" / "Figures.vue").read_text(encoding="utf-8")
	assert "boxed" not in figures, "every figure is framed; there is no unframed kind"
	for path in SRC.rglob("*.vue"):
		source = path.read_text(encoding="utf-8")
		where = path.relative_to(SRC)
		if "NumberCard" in source:
			# A module's Home draws its row of cards itself, wherever its screens live.
			assert where.parts[0] in ("kit", "home") or where.name.endswith("Home.vue"), (
				f"{where} draws a figure of its own; use the kit's Figures"
			)
		assert not re.search(r"<Figures[^>]*\bboxed\b", source), f"{where} asks for an unframed figure"
