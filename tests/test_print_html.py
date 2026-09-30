"""A workspace's HTML on a printed page is held by one/print_html.py: an HTML
block renders through onedesk's copy of frappe's macro, in a sandbox that
holds only the record, and a letter head's HTML is stored cleaned and without
a template. These read the code that says so."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

HTML = (tree.APP / "one" / "print_html.py").read_text()
PRINTING = (tree.APP / "one" / "printing.py").read_text()
MACRO = (tree.APP / "templates" / "print_format" / "macros" / "HTML.html").read_text()


def _constant(source: str, name: str):
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and any(getattr(one, "id", None) == name for one in node.targets):
			return node.value
	raise AssertionError(name)


def _body(source: str, name: str) -> str:
	return source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]


def test_the_macro_draws_a_marked_block_in_the_sandbox():
	assert "df.one_sandboxed" in MACRO and "one_html_block(df.html, doc)" in MACRO
	assert "Derived from frappe/templates/print_format/macros/HTML.html" in MACRO
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"onedesk.one.print_html.one_html_block"' in hooks
	assert ast.literal_eval(_constant(HTML, "MARK")) == "one_sandboxed"


def test_a_workspace_save_marks_every_html_block_it_did_not_leave_as_frappes():
	layout = _body(PRINTING, "_layout")
	assert "block.pop(print_html.MARK, None)" in layout
	assert "print_html.check_template(" in layout and "block[print_html.MARK] = 1" in layout
	assert layout.index("block.pop(print_html.MARK") < layout.index("block[print_html.MARK] = 1")
	assert ast.literal_eval(_constant(PRINTING, "UNSAFE_BLOCKS")) == ("Typst",)


def test_the_sandbox_holds_only_the_record():
	sandbox = _body(HTML, "_sandbox")
	assert "ImmutableSandboxedEnvironment(autoescape=True)" in sandbox and "env.globals = {}" in sandbox
	filters = HTML.split("FILTERS = frozenset(", 1)[1].split("\n)\n", 1)[0]
	assert " safe " not in f" {filters} " and 'safe"' not in filters
	assert 'NAMES = frozenset(("doc", "loop", "_"))' in HTML
	nodes = HTML.split("NODES = (", 1)[1].split("\n)\n", 1)[0]
	for refused in ("Include", "Import", "FromImport", "Extends", "Macro", "CallBlock", "With", "ExprStmt"):
		assert f"nodes.{refused}," not in nodes, refused
	refused = _body(HTML, "_refused")
	assert 'startswith("_")' in refused and "dyn_args" in refused and "METHODS" in refused


def test_nothing_printed_is_fetched_from_elsewhere():
	attribute = _body(HTML, "_attribute")
	assert "IMAGE.match" in attribute and "LINK.match" in attribute and "_style_ok" in attribute
	clean = _body(HTML, "_cleaned")
	assert 'clean_content_tags={"script", "style"}' in clean and "attribute_filter=_attribute" in clean
	assert '"image_url"' in _body(PRINTING, "_layout")


def test_a_letter_head_is_stored_cleaned_and_without_a_template():
	validate = _body(PRINTING, "validate_letter_head")
	assert validate.count("print_html.letter_head_html(") == 2
	assert "TEMPLATE.search(cleaned)" in _body(HTML, "letter_head_html")


def test_a_preview_renders_the_format_as_saved():
	previewed = _body(PRINTING, "_previewed")
	assert "_content(doc)" in previewed and "return doc.as_dict()" in previewed
	for method in ("render_builder_preview", "download_builder_preview_pdf"):
		assert "print_format = _previewed(print_format)" in _body(PRINTING, method), method
