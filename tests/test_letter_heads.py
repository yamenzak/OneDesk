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
	assert "doc.one_top = None" in apply and 'before.get("one_top") == doc.one_top' in apply


def test_no_table_cells():
	draw = _body("draw")
	assert "<td" not in draw and "<table" not in draw
	assert "_ratio(" in draw
