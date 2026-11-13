"""A figure is one card everywhere: a small grey label, the number, a line
under it, framed. On the desk it is frappe's own `frappe.ui.stat_card`
(ERPNext's Customer Overview draws the same); on an island it is frappe-ui's
NumberCard in the same frame, through the kit's Figures. A record's head, a
module's Home and a page of ours used to draw three kinds. docs/STANDARD.md,
One figure."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

SRC = tree.ROOT / "frontend" / "src"
JS = tree.APP / "public" / "js"
CSS = (tree.APP / "public" / "css" / "desk.css").read_text(encoding="utf-8")


def head_problems(band: str, css: str) -> list[str]:
	"""What a record head's script and the desk's CSS get wrong about its figure. Pure."""
	out = []
	if "frappe.ui.stat_card(" not in band:
		out.append("a head's figure is frappe's stat card")
	if "desk_charts.bundle.js" not in band:
		out.append("the stat card's bundle is loaded before a head is drawn")
	if "one-stat-value" in band or "one-stat-value" in css:
		out.append("no figure of the head's own")
	return out


def card_reads_as_frappe_uis(css: str) -> bool:
	"""frappe-ui's NumberCard: 8px corners and a 20px number. Pure."""
	return bool(
		re.search(r"body \.es-stat-card \{\s*border-radius: var\(--radius-4\);", css)
		and re.search(r"body \.es-stat-card__value \{\s*font-size: var\(--text-3xl\);", css)
	)


def figure_problems(figures: str, sources: dict[Path, str]) -> list[str]:
	"""The kit's Figures offering an unframed kind, and an island drawing a
	figure of its own or asking for an unframed one, `sources` by their path
	under frontend/src. A module's Home draws its row of cards itself,
	wherever its screens live. Pure."""
	out = ["every figure is framed; there is no unframed kind"] if "boxed" in figures else []
	for where, source in sources.items():
		if "NumberCard" in source and not (where.parts[0] in ("kit", "home") or where.name.endswith("Home.vue")):
			out.append(f"{where} draws a figure of its own; use the kit's Figures")
		if re.search(r"<Figures[^>]*\bboxed\b", source):
			out.append(f"{where} asks for an unframed figure")
	return out


def test_a_record_head_draws_frappes_stat_card():
	found = head_problems((JS / "band.js").read_text(encoding="utf-8"), CSS)
	assert not found, "; ".join(found)


def test_the_desk_card_reads_as_the_island_card():
	"""frappe-ui's NumberCard: 8px corners and a 20px number."""
	assert card_reads_as_frappe_uis(CSS)


def test_an_island_draws_figures_through_the_kit():
	figures = (SRC / "kit" / "Figures.vue").read_text(encoding="utf-8")
	found = figure_problems(figures, {path.relative_to(SRC): path.read_text(encoding="utf-8") for path in SRC.rglob("*.vue")})
	assert not found, "\n".join(found)


def test_the_figure_rules_catch_their_examples():
	assert not head_problems("frappe.ui.stat_card(x); load('desk_charts.bundle.js')", "")
	assert len(head_problems("<div class='one-stat-value'>", "")) == 3
	css = "body .es-stat-card {\n\tborder-radius: var(--radius-4);\n}\nbody .es-stat-card__value {\n\tfont-size: var(--text-3xl);\n}"
	assert card_reads_as_frappe_uis(css)
	assert not card_reads_as_frappe_uis(css.replace("radius-4", "radius-2"))
	found = figure_problems(
		"<template/>",
		{
			Path("stock/Board.vue"): "<NumberCard/>",
			Path("stock/StockHome.vue"): "<NumberCard/>",
			Path("kit/Row.vue"): "<Figures boxed />",
		},
	)
	assert found == ["stock/Board.vue draws a figure of its own; use the kit's Figures", "kit/Row.vue asks for an unframed figure"]
	assert figure_problems("boxed", {}) == ["every figure is framed; there is no unframed kind"]
