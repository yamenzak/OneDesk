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
	assert feet == ["centred", "split", "band"]
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
