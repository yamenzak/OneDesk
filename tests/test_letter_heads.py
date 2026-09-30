"""A letter head's top is drawn from the company by one/letter_heads.py: one
of its presets, every value escaped, drawn again whenever the company or its
address changes, and laid out without table cells, which frappe's print
stylesheet stretches pictures across. These read the code that says so."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "letter_heads.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _keys(name: str) -> list[str]:
	for node in ast.parse(SOURCE).body:
		if isinstance(node, ast.Assign) and any(getattr(one, "id", None) == name for one in node.targets):
			return [key.value for key in node.value.keys]
	raise AssertionError(name)


def _body(name: str) -> str:
	return SOURCE.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_every_preset_is_drawn():
	draw = _body("draw")
	presets = _keys("PRESETS")
	assert presets == ["classic", "centred", "banner", "minimal", "details", "logo"]
	for preset in presets[1:]:
		assert f'preset == "{preset}"' in draw, preset


def test_what_the_company_says_is_escaped():
	draw = _body("draw")
	assert "escape_html" in draw
	for key in ("name", "logo", "tax_id"):
		assert f'details.get("{key}")' in draw or f'details["{key}"]' in draw, key
	assert "COLOUR.match" in _body("company")


def test_a_top_is_drawn_again_when_the_company_changes():
	assert '"Company": {"on_update": "onedesk.one.letter_heads.redraw"}' in HOOKS
	assert '"Address": {"on_update": "onedesk.one.letter_heads.redraw"}' in HOOKS
	assert "is_your_company_address" in _body("redraw")
	printing = (tree.APP / "one" / "printing.py").read_text()
	validate = printing.split("def validate_letter_head(", 1)[1].split("\ndef ", 1)[0]
	assert validate.index("letter_heads.apply(doc)") < validate.index("print_html.letter_head_html")


def test_a_top_changed_by_hand_is_left_as_written():
	apply = _body("apply")
	assert "doc.set(field, None)" in apply and "before.get(field) == doc.get(field)" in apply


def test_no_table_cells():
	draw = _body("draw")
	assert "<td" not in draw and "<table" not in draw
	assert "_ratio(" in draw


def test_the_top_is_still_filtered():
	"""Letter Head's content skips frappe's XSS filter so a drawn top's icons
	survive; every top not drawn here gets frappe's own filter instead."""
	import json

	custom = json.loads((tree.APP / "one" / "custom" / "letter_head.json").read_text())
	assert any(
		one["field_name"] == "content" and one["property"] == "ignore_xss_filter"
		for one in custom["property_setters"]
	)
	printing = (tree.APP / "one" / "printing.py").read_text()
	validate = printing.split("def validate_letter_head(", 1)[1].split("\ndef ", 1)[0]
	assert "sanitize_html(doc.content)" in validate and "not doc.one_top" in validate
	assert "print_html.letter_head_html(doc.content" in validate


def test_the_brand_line_may_be_left_out_of_every_preset():
	assert '"line":' in _body("settings")
	draw = _body("draw")
	assert 'said["line"]' in draw
	assert draw.count("rule") >= 6  # its definition, and every preset but Minimal, whose line is its border


def test_every_foot_is_drawn_and_carries_no_page_number():
	"""The page number is the print format's own (Print Format's page_number),
	which frappe draws on every page; a foot that drew one too would print it twice."""
	feet = _keys("FEET")
	assert feet == ["centred", "split", "band", "above", "spread"]
	draw_foot = _body("draw_foot")
	for preset in feet[1:]:
		assert f'preset == "{preset}"' in draw_foot, preset
	assert "escape_html" in draw_foot
	assert 'class="page"' not in draw_foot and "topage" not in draw_foot
	assert 'said["line"]' in draw_foot


def test_the_foot_is_drawn_kept_and_filtered_as_the_top_is():
	import json

	parts = SOURCE.split("PARTS = (", 1)[1].split("\n)\n", 1)[0]
	assert '"one_top"' in parts and '"one_foot"' in parts
	assert "for field, source, html, image, read, drawn in PARTS" in _body("apply")
	assert '"one_foot": ["is", "set"]' in _body("redraw")
	custom = json.loads((tree.APP / "one" / "custom" / "letter_head.json").read_text())
	assert {one["fieldname"] for one in custom["custom_fields"]} >= {"one_top", "one_foot"}
	assert {one["field_name"] for one in custom["property_setters"]} >= {"content", "footer"}
	printing = (tree.APP / "one" / "printing.py").read_text()
	validate = printing.split("def validate_letter_head(", 1)[1].split("\ndef ", 1)[0]
	assert "sanitize_html(doc.footer)" in validate and 'not doc.get("one_foot")' in validate


def test_a_foot_is_one_quiet_line_that_may_carry_the_logo():
	source = SOURCE.split("FOOT_FIRST = ", 1)[1].split("\n", 1)[0]
	assert source == '("website", "tax_id")'
	assert '"logo"' in SOURCE.split("FOOT_SHOWN = ", 1)[1].split("\n", 1)[0]
	assert "_ratio(" in _body("draw_foot")


def test_spread_gives_each_detail_an_equal_share():
	"""With cells as wide as their text, the middle detail sat wherever the two
	beside it pushed it; an equal share each puts it on the page's centre."""
	spread = _body("draw_foot").split('preset == "spread"', 1)[1].split("# Centred", 1)[0]
	assert "table-layout:fixed" in spread and "share" in spread


AI = (tree.APP / "one" / "ai.py").read_text()


def test_oneai_reads_each_header_and_footer_as_they_are():
	part = AI.split("def _letter_head_part(", 1)[1].split("\ndef ", 1)[0]
	assert '"drawn_from"' in part and '"settings"' in part and '"written_in"' in part
	reading = AI.split("def workspace_printing(", 1)[1].split("\ndef ", 1)[0]
	assert '"header": _letter_head_part(one, "header")' in reading
	assert '"footer": _letter_head_part(one, "footer")' in reading and '"presets"' in reading


def test_oneai_changes_only_what_it_names():
	"""A change to a letter head that is there is made to what it is now, so
	turning off the footer's line leaves its preset, ticks and note alone."""
	change = AI.split("def change_printing(", 1)[1].split("\ndef ", 1)[0]
	assert "{**(before or {}), **top_said}" in change
	assert "{**(before or {}), **foot_said}" in change
	assert 'foot_said.get("preset") == "none"' in change


def test_icons_by_name_in_html_written_by_hand():
	assert "letter_heads.icons_in(html)" in (tree.APP / "one" / "print_html.py").read_text()
	assert "_known(name)" in _body("icons_in")


def test_the_company_reads_as_three_lines_with_one_edge():
	"""The address on one line and the contacts on one line, in every preset;
	the room between contacts before each, so a wrapped line ends on a contact
	and a right-aligned column keeps one edge."""
	draw = SOURCE.split("def draw(", 1)[1].split("\ndef ", 1)[0]
	assert "enumerate(address)" not in draw, "Classic printed the address a line at a time"
	assert '"margin-left:12px" if n else ""' in draw
	assert "gap.join(contacts)" not in draw
	# Classic's logo cell is as wide as the logo, in pixels: frappe's print style
	# holds letter head pictures to their cell.
	assert "* (ratio or 1)) + 24}px" in draw
