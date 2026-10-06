"""Point 11: a record that leaves the company prints from a format we ship,
laid out in frappe's print format builder from One's print blocks. These
read the code."""

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
BLOCKS = APP / "one" / "print_blocks.py"
TEMPLATES = APP / "one" / "print_format_field_template"

#: Every record One sends to somebody outside the company.
LEAVES = (
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Payment Entry",
	"Delivery Note",
	"Purchase Order",
	"Request for Quotation",
	"Salary Slip",
	"Job Offer",
	"Appointment Letter",
)


def _assigned(name: str):
	for node in ast.parse(BLOCKS.read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
			return node.value
	raise AssertionError(f"print_blocks.py has no {name}")


def _formats() -> dict:
	return ast.literal_eval(_assigned("FORMATS"))


def _scrub(name: str) -> str:
	return name.lower().replace(" ", "_")


def _format(name: str, module: str) -> dict:
	path = APP / module / "print_format" / _scrub(name) / f"{_scrub(name)}.json"
	assert path.exists(), f"{name} is not shipped in {module}"
	return json.loads(path.read_text())


def _blocks(data) -> list:
	if isinstance(data, dict):
		found = [data] if data.get("fieldtype") == "Field Template" else []
		return found + [one for value in data.values() for one in _blocks(value)]
	if isinstance(data, list):
		return [one for value in data for one in _blocks(value)]
	return []


def test_every_record_that_leaves_has_a_format_we_ship():
	formats = _formats()
	assert set(LEAVES) <= set(formats), sorted(set(LEAVES) - set(formats))
	for doctype, (name, module) in formats.items():
		shipped = _format(name, module)
		assert shipped["doc_type"] == doctype and shipped["standard"] == "Yes" and not shipped["disabled"], name
		assert shipped["print_format_builder_beta"] and not shipped.get("custom_format"), f"{name} is not laid out in the builder"
		used = {one["field_template"] for one in _blocks(json.loads(shipped["format_data"]))}
		assert "One Title" in used, f"{name} does not open with One Title"


def test_every_block_is_a_field_template_with_its_template():
	known = set(re.findall(r'^\t\t"(\w+)": \w+,$', BLOCKS.read_text(), flags=re.M))
	shipped = {}
	for path in TEMPLATES.glob("*/*.json"):
		one = json.loads(path.read_text())
		assert one["standard"] and one["module"] == "One", path
		template = APP / one["template_file"]
		assert template.exists(), f"{one['name']} has no {one['template_file']}"
		# The builder's canvas previews a field template from its text, and prints from its file.
		assert one["template"] == '{%% include "%s" %%}' % one["template_file"], f"{one['name']} previews something else"
		block = re.search(r'one_print_block\(doc, "(\w+)"\)', template.read_text())
		assert block and block[1] in known, f"{one['template_file']} draws no block of print_blocks.py"
		shipped[one["name"]] = one
	for doctype, (name, module) in _formats().items():
		used = {one["field_template"] for one in _blocks(json.loads(_format(name, module)["format_data"]))}
		assert used <= set(shipped), sorted(used - set(shipped))


def test_the_blocks_reach_jinja_and_settle_after_migrate():
	"""A new site gets the blocks and the formats as defaults, and every migrate keeps them."""
	hooks = (APP / "hooks.py").read_text()
	assert '"onedesk.one.print_blocks.one_print_block"' in hooks
	assert hooks.count('"onedesk.one.print_blocks.settle"') == 2, "after_install and after_migrate"
	# frappe's module sync leaves field templates out, so settle brings them in.
	assert "def _sync_blocks" in BLOCKS.read_text() and "_sync_blocks()" in BLOCKS.read_text()


def test_a_template_escapes_what_it_shows():
	"""A value from the record goes through `|e`, so a name can't write markup
	onto the paper. Only an address, which ERPNext keeps as HTML, is shown as it is."""
	for path in (APP / "templates" / "one_print").glob("*.html"):
		for shown in re.findall(r"\{\{(.*?)\}\}", path.read_text()):
			plain = "|e" in shown or "colour" in shown or "loop" in shown
			assert plain or re.search(r"\b(address|ship)\b", shown), f"{path.name}: {shown.strip()}"
