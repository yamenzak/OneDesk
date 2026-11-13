"""Point 11: a record that leaves the company prints from a format we ship,
laid out in frappe's print format builder. A format is native, made of the
builder's own pieces, or not yet, opening with One's title block. These read
the code."""

import ast
import json
import re
from pathlib import Path

import pytest
from tests.bench import APPS, doctype_json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import tree  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
BLOCKS = APP / "one_studio" / "print_blocks.py"
TEMPLATES = APP / "one" / "print_format_field_template"

LEAVES = (
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Payment Entry",
	"Delivery Note",
	"Purchase Receipt",
	"Packing Slip",
	"Stock Entry",
	"Purchase Order",
	"Request for Quotation",
	"Blanket Order",
	"Work Order",
	"Salary Slip",
	"Job Offer",
	"Appointment Letter",
	"Timesheet",
	"Contract",
	"Project",
	"Maintenance Schedule",
	"Maintenance Visit",
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


def format_wrong(doctype: str, shipped: dict) -> list[str]:
	"""How a format we ship for a doctype is not its standard, enabled,
	builder-laid format. Pure."""
	out = [] if shipped["doc_type"] == doctype and shipped["standard"] == "Yes" and not shipped["disabled"] else ["not the doctype's standard, enabled format"]
	return out + ([] if shipped["print_format_builder_beta"] and not shipped.get("custom_format") else ["is not laid out in the builder"])


def test_every_record_that_leaves_has_a_format_we_ship():
	formats = _formats()
	assert set(LEAVES) <= set(formats), sorted(set(LEAVES) - set(formats))
	for doctype, (name, module) in formats.items():
		found = format_wrong(doctype, _format(name, module))
		assert not found, f"{name}: {found}"


def _native(blocks: bool = False) -> dict:
	"""Every format we ship drawn only from the builder's own pieces, by name,
	as (its doctype, its layout); with `blocks`, those that also gather a part
	from other records in one of One's blocks."""
	found = {}
	for path in APP.glob("*/print_format/*/*.json"):
		shipped = json.loads(path.read_text())
		layout = json.loads(shipped.get("format_data") or "{}")
		if shipped.get("print_format_builder_beta") and layout and (blocks or not _blocks(layout)):
			found[shipped["name"]] = (shipped["doc_type"], layout)
	return found


def test_each_erpnext_format_has_ours():
	"""ERPNext's formats One's replace are turned off on migrate, so each of
	One's is shipped and each of ERPNext's it names is one ERPNext ships."""
	replaces = ast.literal_eval(_assigned("REPLACES"))
	assert not unshipped(replaces, _native(blocks=True))
	if not (APPS / "erpnext").exists():
		pytest.skip("erpnext is not checked out beside this app")
	theirs = {
		json.loads(path.read_text())["name"]
		for app in ("erpnext", "hrms")
		for path in APPS.glob(f"{app}/{app}/*/print_format/*/*.json")
	}
	found = unshipped_theirs(replaces, theirs)
	assert not found, found


def unshipped(replaces: dict, native: dict) -> list[str]:
	"""The formats of ours REPLACES names that are not shipped native. Pure."""
	return sorted(set(replaces) - set(native))


def unshipped_theirs(replaces: dict, theirs: set) -> list[str]:
	"""The formats of ERPNext's REPLACES turns off that ERPNext does not ship. Pure."""
	return sorted({one for names in replaces.values() for one in names} - theirs)


def _pieces(data):
	if isinstance(data, dict):
		if data.get("fieldtype") == "Table":
			return [data]
		found = [data] if data.get("fieldtype") or data.get("columns") else []
		return found + [one for value in data.values() for one in _pieces(value)]
	if isinstance(data, list):
		return [one for value in data for one in _pieces(value)]
	return []


NO_BUILTINS = re.compile(r"\b(len|sum|abs|min|max|any|all|sorted|round|str)\(")


def test_a_native_format_asks_only_what_frappe_can_answer():
	"""A condition frappe cannot evaluate prints the thing anyway and logs
	an error on every print, so one that calls a builtin never ships."""
	assert _native(), "no format is native yet"
	for doctype, layout in _native(blocks=True).values():
		found = builtin_conditions(layout)
		assert not found, f"{doctype}: {found}"


def builtin_conditions(layout) -> list[str]:
	"""The conditions of a layout that call a builtin frappe cannot evaluate. Pure."""
	out = []
	for one in _pieces(layout):
		said = [one.get(key) or "" for key in ("visible_if", "column_condition", "row_condition")]
		said += [column.get("column_condition") or "" for column in one.get("table_columns") or []]
		out += [condition for condition in said if NO_BUILTINS.search(condition)]
	return out


def _fields(doctype: str) -> set:
	scrub = _scrub(doctype)
	found = {"name", "idx", "owner", "creation", "modified", "modified_by", "docstatus"}
	for path in doctype_json(scrub):
		found |= {one["fieldname"] for one in json.loads(path.read_text())["fields"]}
	for path in APP.glob(f"*/custom/{scrub}.json"):
		found |= {one["fieldname"] for one in json.loads(path.read_text()).get("custom_fields") or []}
	return found


def _child(doctype: str, table: str) -> str:
	scrub = _scrub(doctype)
	for path in doctype_json(scrub):
		for one in json.loads(path.read_text())["fields"]:
			if one["fieldname"] == table:
				return one["options"]
	raise AssertionError(f"{doctype} has no table {table}")


PRINTED_ONLY = {"Sales Order": {"proforma_no", "proforma_date"}}


def test_a_native_format_prints_fields_the_record_has():
	"""A misspelt field prints nothing and says nothing, so each is read back
	against the doctype, its custom fields, and its tables' own."""
	if not (APPS / "erpnext").exists():
		pytest.skip("erpnext is not checked out beside this app")
	for doctype, layout in _native(blocks=True).values():
		has = _fields(doctype) | PRINTED_ONLY.get(doctype, set())
		found = printed_missing(layout, has, lambda table, doctype=doctype: _fields(_child(doctype, table)))
		assert not found, f"{doctype}: {found}"


def printed_missing(layout, has: set, rows_of) -> list[str]:
	"""The fields a layout prints that the record, or the table's rows
	(`rows_of` gives a table's fields), has not. Pure."""
	out = []
	for one in _pieces(layout):
		if one.get("fieldtype") == "Table":
			if one["fieldname"] not in has:
				out.append(one["fieldname"])
				continue
			rows = rows_of(one["fieldname"])
			out += [
				f"{one['fieldname']}: {shown['fieldname']}"
				for column in one.get("table_columns") or []
				for shown in [column, *(column.get("merged_fields") or [])]
				if shown["fieldname"] not in rows
			]
		elif one.get("fieldtype") == "Linked Field":
			if one["link_path"].split(".")[0] not in has:
				out.append(one["link_path"])
		elif one.get("fieldtype") not in (None, "Field Template") and not one.get("custom") and one.get("fieldname"):
			if one["fieldname"] not in has:
				out.append(one["fieldname"])
	return out


def test_every_block_is_a_field_template_with_its_template():
	known = set(re.findall(r'^\t\t"(\w+)": \w+,$', BLOCKS.read_text(), flags=re.M))
	shipped = {}
	for path in TEMPLATES.glob("*/*.json"):
		one = json.loads(path.read_text())
		template = APP / one["template_file"]
		found = template_wrong(one, template.read_text() if template.exists() else None, known)
		assert not found, f"{path}: {found}"
		shipped[one["name"]] = one
	for doctype, (name, module) in _formats().items():
		used = {one["field_template"] for one in _blocks(json.loads(_format(name, module)["format_data"]))}
		assert used <= set(shipped), sorted(used - set(shipped))


def template_wrong(one: dict, template: str | None, known: set) -> list[str]:
	"""How a Field Template we ship is not One's standard one, its file there,
	previewing that file and drawing a block of print_blocks.py; `template`
	is its file's text, None when it is not there. Pure."""
	out = [] if one["standard"] and one["module"] == "One" else ["not One's standard"]
	if template is None:
		return out + [f"has no {one['template_file']}"]
	if one["template"] != '{%% include "%s" %%}' % one["template_file"]:
		out.append("previews something else")
	block = re.search(r'one_print_block\(doc, "(\w+)"\)', template)
	return out + ([] if block and block[1] in known else ["draws no block of print_blocks.py"])


def blocks_unsettled(hooks: str, blocks: str) -> list[str]:
	"""How the blocks miss Jinja, or the formats are not settled after install
	and migrate. Pure."""
	out = [] if '"onedesk.one_studio.print_blocks.one_print_block"' in hooks else ["one_print_block is not in Jinja"]
	if hooks.count('"onedesk.one_studio.print_blocks.settle"') != 2:
		out.append("settle is not run after_install and after_migrate")
	return out + ([] if "def _sync_blocks" in blocks and "_sync_blocks()" in blocks else ["the blocks are not synced"])


def test_the_blocks_reach_jinja_and_settle_after_migrate():
	"""A new site gets the blocks and the formats as defaults, and every migrate keeps them."""
	found = blocks_unsettled(tree.hooks(), BLOCKS.read_text())
	assert not found, found


def unescaped(html: str) -> list[str]:
	"""What a print template shows from the record without `|e`, but for an
	address. Pure."""
	return [
		shown.strip()
		for shown in re.findall(r"\{\{(.*?)\}\}", html)
		if not ("|e" in shown or "colour" in shown or "loop" in shown) and not re.search(r"\b(address|ship)\b", shown)
	]


def test_a_template_escapes_what_it_shows():
	"""A value from the record goes through `|e`, so a name can't write markup
	onto the paper. Only an address, which ERPNext keeps as HTML, is shown as it is."""
	for path in (APP / "templates" / "one_print").glob("*.html"):
		found = unescaped(path.read_text())
		assert not found, f"{path.name}: {found}"


def test_the_print_rules_catch_their_examples():
	good = {"doc_type": "Quotation", "standard": "Yes", "disabled": 0, "print_format_builder_beta": 1}
	assert format_wrong("Quotation", good) == []
	assert format_wrong("Quotation", {**good, "disabled": 1, "custom_format": 1}) == ["not the doctype's standard, enabled format", "is not laid out in the builder"]
	assert unshipped({"One Quotation": ["Quotation Standard"]}, {}) == ["One Quotation"]
	assert unshipped_theirs({"One Quotation": ["Quotation Standard"]}, {"Other"}) == ["Quotation Standard"]
	layout = [{"fieldtype": "Data", "fieldname": "titel", "visible_if": "len(doc.items) > 1"}, {"fieldtype": "Table", "fieldname": "items", "table_columns": [{"fieldname": "qty"}, {"fieldname": "rat"}]}]
	layout.append({"fieldtype": "Linked Field", "link_path": "custmer.name"})
	assert builtin_conditions(layout) == ["len(doc.items) > 1"] and builtin_conditions([{"fieldtype": "Data", "visible_if": "doc.total > 1"}]) == []
	assert printed_missing(layout, {"title", "items"}, lambda table: {"qty"}) == ["titel", "items: rat", "custmer.name"]
	assert printed_missing([{"fieldtype": "Data", "fieldname": "title"}], {"title"}, lambda table: set()) == []
	block = {"standard": 1, "module": "One", "template_file": "templates/one_print/head.html", "template": '{% include "templates/one_print/head.html" %}'}
	assert template_wrong(block, 'one_print_block(doc, "head")', {"head"}) == []
	assert template_wrong({**block, "template": "x"}, "", {"head"}) == ["previews something else", "draws no block of print_blocks.py"]
	assert template_wrong(block, None, {"head"}) == ["has no templates/one_print/head.html"]
	hooks = '"onedesk.one_studio.print_blocks.one_print_block" "onedesk.one_studio.print_blocks.settle" "onedesk.one_studio.print_blocks.settle"'
	assert blocks_unsettled(hooks, "def _sync_blocks(): _sync_blocks()") == [] and len(blocks_unsettled("", "")) == 3
	assert unescaped("{{ doc.customer_name }} {{ doc.title|e }} {{ address }}") == ["doc.customer_name"]
