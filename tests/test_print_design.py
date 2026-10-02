"""OneAI designs a print format as frappe's builder lays one out (ai.design_print_format).
These read the code that keeps its results consistent: a starting layout by kind
of record, the house look unless another is asked for, the builder's own
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


def test_the_house_style_unless_they_ask_for_their_own():
	"""A format made here prints in the house style, frappe's print style in
	its own classes and grey scale; a look somebody asks for replaces it, and a
	changed format left without css keeps its own."""
	import re

	help_ = AI.split("LAYOUT_HELP = (", 1)[1].split("\n)\n", 1)[0]
	assert "it replaces the house style" in help_ and "Their taste wins" in help_
	house = RECIPES.split('HOUSE_CSS = """', 1)[1].split('"""', 1)[0]
	assert "#" not in house.replace("#:", ""), (
		"the house style is frappe's grey scale, not colours of its own"
	)
	assert not re.search(r"\drem", house), "em, never rem, as frappe's print css"
	assert all(line.startswith(".print-format-doc") for line in house.strip("\\\n").splitlines())
	styled = _body(AI, "_styled")
	assert "return css" in styled and "HOUSE_CSS" in styled
	assert "before if before is not None" in styled
	assert '_styled(css, house_style, (existing.css or "") if existing else None)' in _body(
		AI, "design_print_format"
	)
	assert "_style_of(held.css)" in _body(AI, "print_layout")


def test_the_jinja_it_is_told_is_the_jinja_it_may_use():
	"""LAYOUT_HELP names every filter and test the sandbox keeps, and says
	what is not there."""
	import re

	html = (tree.APP / "one" / "print_html.py").read_text()
	help_ = AI.split("LAYOUT_HELP = (", 1)[1].split("\n)\n", 1)[0].replace('"\n\t"', "")
	filters = re.search(r"FILTERS = frozenset\(\s*\(\s*(.*?)\)\.split", html, re.S).group(1)
	for name in " ".join(re.findall(r'"([^"]*)"', filters)).split():
		if len(name) == 1:
			continue  # d and e, frappe's short names for default and escape
		assert re.search(rf"\b{name}\b", help_), name
	tests = re.search(r'TESTS = frozenset\("([^"]*)"', html).group(1)
	for name in tests.split():
		assert re.search(rf"\b{name}\b", help_), name
	assert "no frappe.db" in help_ and "get_formatted" in help_


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


RUN = (tree.APP / "one_ai" / "run.py").read_text()


def test_a_weak_model_is_read_as_it_meant():
	"""What the live runs showed a small model writing, read as the one thing
	it can mean: a table's name before its columns, columns spelled out as
	objects, widths as percentages, and Python's True inside the JSON."""
	assert "_paired(c)" in _body(AI, "_built") and "_parsed(sections)" in _body(AI, "_built")
	assert '"table": before.strip()' in _body(AI, "_paired")
	assert 'column.get("field") or column.get("fieldname")' in _body(AI, "_column")
	assert 'rstrip("%")' in _body(AI, "_share")
	assert '"true"' in _body(AI, "_parsed") and '"null"' in _body(AI, "_parsed")
	# The sections and then something after them: the sections.
	assert "raw_decode" in _body(AI, "_parsed")


def test_a_document_of_trade_prints_who_and_how_much():
	assert "print_recipes.essentials(doctype)" in _body(AI, "_built")
	assert '("grand_total", "rounded_total")' in _body(RECIPES, "essentials")


def test_a_design_that_does_not_hold_is_mended_not_reported():
	"""The layout goes back with what to start from, the loop asks for the
	call once more, and if it still does not hold the model says nothing was
	made rather than that it was."""
	redo = _body(AI, "_redo")
	assert '"mend": "design_print_format"' in redo and '"starting_layout"' in redo
	assert "MEND_IT.format(mend)" in RUN and "GAVE_UP.format(mend)" in RUN
	assert "nothing was made" in RUN.split("GAVE_UP = (", 1)[1].split("\n)\n", 1)[0]
	assert '_unsaid(out["turns"])' in RUN


def test_a_typeface_is_frappes_own_font():
	"""frappe's Print Format has a Google Font field it imports itself, so a
	look with a typeface never needs an import of ours."""
	assert "FONT = re.compile(" in PRINTING
	assert '"font": font' in _body(PRINTING, "format_doc")
	assert 'font=values.get("font")' in _body(PRINTING, "save_format")
	assert "font," in _body(AI, "design_print_format")


def test_leaving_the_sections_out():
	"""A plain request prints the starting layout; a restyle keeps the
	format's own layout."""
	laid = _body(AI, "_laid_out")
	assert "json.loads(existing.format_data)" in laid
	assert "print_recipes.starting_layout(doctype)" in laid


def test_it_reads_a_kind_as_oneai_and_intake_do():
	"""print_layout reads a kind through the describer OneAI and Intake share,
	told it is for a page: every field with its type, each table with its
	rows, and what frappe's own formats leave off said to be."""
	assert "kind.fields(meta, printing=True)" in _body(AI, "print_layout")
	assert "fields_of" not in _body(AI, "print_layout")
	kind = (tree.APP / "one_ai" / "kind.py").read_text()
	fields = kind.split("def fields(", 1)[1].split("\ndef ", 1)[0]
	assert "not printed" in fields and "f.print_hide" in fields
	assert '"rows": fields(frappe.get_meta(f.options), depth + 1, printing=True)' in fields


def test_blocks_then_a_block_of_html_then_a_page_of_it():
	"""The order a page is built in, so what OneAI makes stays the builder's:
	its blocks, an html block for a part they cannot draw, and one across the
	whole body only for a page designed end to end. A format written by hand
	is not a step at all: validate_format refuses it."""
	help_ = AI.split("LAYOUT_HELP = (", 1)[1].split("\n)\n", 1)[0]
	first = help_.index("first the")
	then = help_.index("one html block in its place")
	last = help_.index("one html block across the whole body")
	assert first < then < last
	assert "Never " in help_ and "html for what a block already prints" in help_
	assert "not written by hand" in PRINTING


def test_print_design_runs_on_a_model_that_lays_a_page_out():
	"""The two tools that lay a page out name Print Design; the chat hands the
	conversation to it the moment its model reaches for one; and Print Design
	names its own model, a stronger one than the chat's, with room for a
	page's long answer."""
	import json

	assert 'print_layout.action = design_print_format.action = "print_design"' in AI
	tools = (tree.APP / "one_ai" / "tools.py").read_text()
	assert 'getattr(fn, "action", None)' in _body(tools, "action_of")
	assert "surface.action_of(" in RUN and "chose = mine(action)" in RUN
	fixture = json.loads((tree.APP / "fixtures" / "ai_action.json").read_text())
	design = next(one for one in fixture if one["name"] == "print_design")
	chat = next(one for one in fixture if one["name"] == "chat")
	assert design["default_model"] and design["may_use_tools"]
	assert design["max_output_tokens"] > chat["max_output_tokens"]
	actions = (tree.APP / "one_admin" / "actions.py").read_text()
	assert "fallback = action_default(asked)" in _body(actions, "_model")
	assert 'asked.get("default_model")' in _body(actions, "action_default")


def test_a_tool_call_the_provider_could_not_read_is_asked_again():
	"""Gemini's MALFORMED_FUNCTION_CALL, which a long stylesheet or layout
	brings on, is recognised rather than said as an empty answer, and the call
	is asked for again on one line."""
	gateway = (tree.APP / "one_admin" / "gateway.py").read_text()
	assert '"MALFORMED_FUNCTION_CALL"' in _body(gateway, "_malformed")
	assert "except faults.Malformed:" in _body(gateway, "_said")
	assert "ONE_LINE" in _body(gateway, "_said")


PROPS = (tree.APP / "one" / "print_props.py").read_text()


def test_every_property_the_builder_sets_is_ours_to_set():
	"""A section, a column, a field, a table and its columns, each palette
	block and the page each take frappe's own properties by frappe's own
	names, checked for their shape, and a changed format keeps every one."""
	for where in (
		"SECTION = {",
		"COLUMN = {",
		"FIELD = {",
		"TABLE = {",
		"TABLE_COLUMN = {",
		"BLOCKS = {",
		"PAGE = {",
	):
		assert where in PROPS, where
	for key in (
		'"visible_if"',
		'"row_condition"',
		'"column_condition"',
		'"merged_fields"',
		'"table_header"',
		'"field_borders"',
		'"label_justify"',
		'"repeater_columns"',
		'"Linked Field"',
		'"margin_top"',
	):
		assert key in PROPS, key
	block = _body(AI, "_block")
	assert "print_props.taken(" in block and "print_props.TABLE_COLUMN" in block
	assert "print_props.SECTION" in _body(AI, "_built") and "print_props.stored(" in _body(AI, "_written")
	# A style is a style wherever it is written, a condition is only grammar-checked
	# here and run by frappe's own safe_eval.
	assert "printing._style(str(value), where)" in PROPS and 'compile(str(value), key, "eval")' in PROPS
	assert '("custom_style", "background", "border_color")' in PRINTING
	assert "print_props.taken(page or {}, print_props.PAGE" in _body(PRINTING, "format_doc")


def test_the_house_has_parts_for_an_html_block():
	"""An html block in the house style is built of the house's classes, each
	drawn in frappe-ui's greys and colours; the model is told them by name."""
	house = RECIPES.split('HOUSE_CSS = """', 1)[1].split('"""', 1)[0]
	parts = RECIPES.split("HOUSE_PARTS = (", 1)[1].split("\n)\n", 1)[0]
	for part in ("one-card", "one-kv", "one-badge", "one-stamp", "one-table", "one-figure", "one-note"):
		assert f".{part}" in house and part in parts, part
	assert "print_recipes.HOUSE_PARTS" in _body(AI, "_how")
	help_ = AI.split("LAYOUT_HELP = (", 1)[1].split("\n)\n", 1)[0]
	assert "doc.name" in help_ and "naming_series" in help_


def test_a_blank_is_asked_again_past_the_gateways_cache():
	"""Cloudflare's gateway caches a blank answer like any other, so a retry
	that is the same call gets the same blank back: it asks past the cache."""
	gateway = (tree.APP / "one_admin" / "gateway.py").read_text()
	assert 'FRESH = "cf-aig-skip-cache"' in gateway
	assert "headers[FRESH]" in _body(gateway, "through")
	assert 'return asking(({"role": "user", "text": SAY_IT, "calls": []},), fresh=True)' in _body(gateway, "_said")


def test_sections_written_by_hand_are_read_as_meant():
	"""A raw line break in a string and a backslash before a character JSON
	does not escape are what a model writes; they are read, not refused."""
	parsed = _body(AI, "_parsed")
	assert "json.JSONDecoder(strict=False)" in parsed
	assert "'\"\\\\/bfnrtu'" in parsed
	assert "never by css" in _body(AI, "_how")
