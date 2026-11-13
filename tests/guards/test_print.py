"""Point 11: a record that leaves the company prints from a format we ship,
laid out in frappe's print format builder. A format is native, made of the
builder's own pieces, or not yet, opening with One's title block. These read
the code."""

import ast
import json
import re
from pathlib import Path

import pytest
from tests.bench import APPS
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


def test_every_record_that_leaves_has_a_format_we_ship():
	formats = _formats()
	assert set(LEAVES) <= set(formats), sorted(set(LEAVES) - set(formats))
	for doctype, (name, module) in formats.items():
		shipped = _format(name, module)
		assert shipped["doc_type"] == doctype and shipped["standard"] == "Yes" and not shipped["disabled"], name
		assert shipped["print_format_builder_beta"] and not shipped.get("custom_format"), f"{name} is not laid out in the builder"


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
	native = _native(blocks=True)
	assert set(replaces) <= set(native), sorted(set(replaces) - set(native))
	if not (APPS / "erpnext").exists():
		pytest.skip("erpnext is not checked out beside this app")
	theirs = {
		json.loads(path.read_text())["name"]
		for app in ("erpnext", "hrms")
		for path in APPS.glob(f"{app}/{app}/*/print_format/*/*.json")
	}
	named = {one for names in replaces.values() for one in names}
	assert named <= theirs, sorted(named - theirs)


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
		for one in _pieces(layout):
			for key in ("visible_if", "column_condition", "row_condition"):
				said = one.get(key) or ""
				assert not NO_BUILTINS.search(said), f"{doctype}: {said}"
			for column in one.get("table_columns") or []:
				said = column.get("column_condition") or ""
				assert not NO_BUILTINS.search(said), f"{doctype}: {said}"


def _fields(doctype: str) -> set:
	scrub = _scrub(doctype)
	found = {"name", "idx", "owner", "creation", "modified", "modified_by", "docstatus"}
	for path in APPS.glob(f"*/*/*/doctype/{scrub}/{scrub}.json"):
		found |= {one["fieldname"] for one in json.loads(path.read_text())["fields"]}
	for path in APP.glob(f"*/custom/{scrub}.json"):
		found |= {one["fieldname"] for one in json.loads(path.read_text()).get("custom_fields") or []}
	return found


def _child(doctype: str, table: str) -> str:
	scrub = _scrub(doctype)
	for path in APPS.glob(f"*/*/*/doctype/{scrub}/{scrub}.json"):
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
		for one in _pieces(layout):
			if one.get("fieldtype") == "Table":
				assert one["fieldname"] in has, f"{doctype}: {one['fieldname']}"
				rows = _fields(_child(doctype, one["fieldname"]))
				for column in one.get("table_columns") or []:
					for shown in [column, *(column.get("merged_fields") or [])]:
						assert shown["fieldname"] in rows, f"{doctype} {one['fieldname']}: {shown['fieldname']}"
			elif one.get("fieldtype") == "Linked Field":
				assert one["link_path"].split(".")[0] in has, f"{doctype}: {one['link_path']}"
			elif one.get("fieldtype") not in (None, "Field Template") and not one.get("custom") and one.get("fieldname"):
				assert one["fieldname"] in has, f"{doctype}: {one['fieldname']}"


def test_every_block_is_a_field_template_with_its_template():
	known = set(re.findall(r'^\t\t"(\w+)": \w+,$', BLOCKS.read_text(), flags=re.M))
	shipped = {}
	for path in TEMPLATES.glob("*/*.json"):
		one = json.loads(path.read_text())
		assert one["standard"] and one["module"] == "One", path
		template = APP / one["template_file"]
		assert template.exists(), f"{one['name']} has no {one['template_file']}"
		assert one["template"] == '{%% include "%s" %%}' % one["template_file"], f"{one['name']} previews something else"
		block = re.search(r'one_print_block\(doc, "(\w+)"\)', template.read_text())
		assert block and block[1] in known, f"{one['template_file']} draws no block of print_blocks.py"
		shipped[one["name"]] = one
	for doctype, (name, module) in _formats().items():
		used = {one["field_template"] for one in _blocks(json.loads(_format(name, module)["format_data"]))}
		assert used <= set(shipped), sorted(used - set(shipped))


def test_the_blocks_reach_jinja_and_settle_after_migrate():
	"""A new site gets the blocks and the formats as defaults, and every migrate keeps them."""
	hooks = tree.hooks()
	assert '"onedesk.one_studio.print_blocks.one_print_block"' in hooks
	assert hooks.count('"onedesk.one_studio.print_blocks.settle"') == 2, "after_install and after_migrate"
	assert "def _sync_blocks" in BLOCKS.read_text() and "_sync_blocks()" in BLOCKS.read_text()


def test_a_template_escapes_what_it_shows():
	"""A value from the record goes through `|e`, so a name can't write markup
	onto the paper. Only an address, which ERPNext keeps as HTML, is shown as it is."""
	for path in (APP / "templates" / "one_print").glob("*.html"):
		for shown in re.findall(r"\{\{(.*?)\}\}", path.read_text()):
			plain = "|e" in shown or "colour" in shown or "loop" in shown
			assert plain or re.search(r"\b(address|ship)\b", shown), f"{path.name}: {shown.strip()}"
