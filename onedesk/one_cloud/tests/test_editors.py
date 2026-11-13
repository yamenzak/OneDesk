"""OneDoc, OneSheet and OneDeck turned off (one_cloud/editors.py): nothing
new is made, what was made still opens read-only and still leaves as Word,
Excel or PowerPoint. No site needed."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from onedesk.one import registry
from onedesk.one_cloud import editors, opening

APP = Path(__file__).resolve().parents[2]


class Refused(Exception):
	pass


@pytest.fixture
def off(monkeypatch):
	"""The editors as if every one were turned off, frappe's throw and flags
	stood in for."""
	flags = SimpleNamespace(in_install=False, in_migrate=False, in_patch=False)

	def throw(message, exc=None):
		raise Refused(message)

	monkeypatch.setattr(editors, "frappe", SimpleNamespace(flags=flags, throw=throw, PermissionError=Refused))
	monkeypatch.setattr(editors, "_", lambda text: text)
	monkeypatch.setattr(editors, "on", lambda doctype: False)
	return flags


def test_an_editor_is_off_when_its_rail_row_is():
	assert editors.off_among([registry.get("one_doc").sidebar, "OneCRM"]) == {"Writer Document"}
	assert editors.off_among([]) == set()
	assert set(editors.APPS.values()) == {"one_doc", "one_sheet", "one_deck"}
	assert set(editors.KINDS.values()) == set(editors.APPS)


def test_off_refuses_a_new_one_with_the_reason(off):
	with pytest.raises(Refused, match="turned off for this workspace, so nothing new can be made"):
		editors.making(SimpleNamespace(doctype="Writer Document"))


def test_installing_and_migrating_still_set_an_editor_up(off):
	off.in_migrate = True
	assert editors.making(SimpleNamespace(doctype="Presentation")) is None


def test_off_opens_read_only_and_refuses_a_save(off):
	assert editors.read_only("Workbook").endswith("so this opens read-only.")
	with pytest.raises(Refused):
		editors.refuse_change("Workbook")
	assert editors.read_only("File") is None


def test_an_office_file_is_neither_opened_nor_made_in_an_editor_that_is_off():
	assert editors.ways(opening.way("Letter.docx"), {"document"}) is None
	assert editors.ways(opening.way("Pitch.pptx"), {"document"}) == {"edit": None, "make": "presentation", "copy": None}
	assert editors.ways(opening.way("Pitch.pptx"), {"presentation"}) is None
	assert editors.ways(None, {"workbook"}) is None
	assert opening.row({"file_name": "Budget.xlsx"}, frozenset({"workbook"})) is None
	previewed = {"file_name": "Budget.xlsx", "content_hash": "abc", "one_preview_of": "abc"}
	assert opening.row(previewed, frozenset({"workbook"})) == {"previewed": True}, "the preview still opens it"


def _source(path: str) -> str:
	return (APP / path).read_text(encoding="utf-8")


def _function(path: str, name: str) -> str:
	tree = ast.parse(_source(path))
	return next(ast.unparse(node) for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def test_every_way_of_making_one_goes_through_its_record_type():
	"""New, a template, a copy, an import and OneAI's approved card all
	insert the editor's record, so its before_insert refuses them all."""
	for path in (
		"one_doc/doctype/writer_document/writer_document.py",
		"one_sheet/doctype/workbook/workbook.py",
		"one_deck/doctype/presentation/presentation.py",
	):
		assert "editors.making(self)" in _function(path, "before_insert"), path


def test_every_change_asks_whether_the_editor_is_on():
	for folder, doctype in (("one_doc", "DOCUMENT"), ("one_sheet", "WORKBOOK"), ("one_deck", "PRESENTATION")):
		assert f"editors.refuse_change({doctype})" in _function(f"{folder}/api.py", "_may"), folder
	assert _function("one_cloud/saving.py", "_read_only").index("editors.read_only") < _function("one_cloud/saving.py", "_read_only").index("fidelity")
	assert "editors.read_only" in _function("one_cloud/opening.py", "kept_inside"), "OneOS edits it nowhere either"
	assert "editors.on(PRESENTATION)" in _function("one_deck/api.py", "get_editor_access")


def test_exporting_to_word_excel_and_powerpoint_only_reads():
	assert "_need(item, 'read')" in _function("one_cloud/opening.py", "download")
	assert "_may(name, 'read')" in _function("one_deck/powerpoint.py", "export")
	for path, name in (("one_doc/word.py", "docx"), ("one_sheet/excel.py", "xlsx"), ("one_deck/drive.py", "pptx")):
		assert "_may" not in _function(path, name), path


def test_each_editor_is_an_app_with_a_rail_row_of_its_recent_ones_and_new():
	for kind, doctype in editors.KINDS.items():
		app = registry.get(editors.APPS[doctype])
		assert app.kind == "app" and app.rail and app.line and app.sidebar and "one_cloud" in app.needs, app.id
		path = APP / app.id / "sidebar" / app.mark / f"{app.mark}.json"
		sidebar = json.loads(path.read_text(encoding="utf-8"))
		assert sidebar["name"] == app.sidebar and sidebar["module"] == app.module
		asked = [json.loads(row["route_options"]) for row in sidebar["items"]]
		assert asked == [{"node": f"@made/{kind}"}, {"new": kind}], app.id
		assert [row["link_to"] for row in sidebar["items"]] == ["onecloud", "onecloud"]
