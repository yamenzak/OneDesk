"""OneAI designs a print format as frappe's builder lays one out (ai.design_print_format).
These read the code that keeps its results consistent: a starting layout by kind
of record, frappe's own look unless another is asked for, the builder's own
block options, and the checks that send a layout that would print badly back."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

AI = (tree.APP / "one" / "ai.py").read_text()
RECIPES = (tree.APP / "one" / "print_recipes.py").read_text()
PRINTING = (tree.APP / "one" / "printing.py").read_text()


def _body(source: str, name: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_print_layout_offers_a_starting_layout():
	assert '"starting_layout": print_recipes.starting_layout(doctype)' in _body(AI, "print_layout")
	assert "return _trade(meta) or _plain(meta)" in _body(RECIPES, "starting_layout")


def test_frappes_own_look_unless_asked():
	"""No css unless a look of their own is asked for, so a format made here
	reads like every other one."""
	assert "frappe's own print style" in AI.split("LAYOUT_HELP = (", 1)[1].split("\n)\n", 1)[0]
	design = _body(AI, "design_print_format")
	assert "Leave out: the format prints in frappe's own print style" in design
	assert "font-size" not in RECIPES and "color" not in RECIPES


def test_the_builders_own_block_options():
	block = _body(AI, "_block")
	for key in ('"show_label"', '"barcode_format"', '"table_bordered"', '"align"'):
		assert key in block or key.strip('"') in AI.split("FIELD_OPTIONS =", 1)[1].split("\n", 1)[0], key
	# frappe's words for a label: show, hide, or inline.
	assert '"inline"' in block and '"hide"' in block


def test_a_layout_that_would_print_badly_goes_back():
	built = _body(AI, "_built")
	for problem in (
		"is empty",
		"more than the page",
		"give it its columns",
		"for the barcode",
		"is not a table",
	):
		assert problem in built, problem
	assert 'frappe.throw(_("The layout would print badly: {0}.")' in built


def test_the_page_number_is_a_format_setting():
	assert "PAGE_NUMBER = (" in PRINTING
	assert "page_number not in PAGE_NUMBER" in _body(PRINTING, "format_doc")
	assert 'values.get("page_number")' in _body(PRINTING, "save_format")
