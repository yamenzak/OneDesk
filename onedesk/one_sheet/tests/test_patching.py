"""OneWorkbook writes an Excel file back by writing what changed into the
file itself (one_sheet/patching.py), so what it does not edit stays."""

import io
from datetime import datetime

from openpyxl import Workbook, load_workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table

from onedesk.one_sheet import patching
from onedesk.one_storage import fidelity


def _styled() -> bytes:
	book = Workbook()
	ws = book.active
	ws.title = "Budget"
	ws.append(["Line", "Q1", "Q2", "Year"])
	ws.append(["Projects", 1200000, 1450000, "=SUM(B2:C2)"])
	ws.append(["Fees", 40000, 55000, "=SUM(B3:C3)"])
	ws["E1"] = datetime(2026, 1, 1)
	ws["E1"].number_format = "d mmm yyyy"
	for cell in ws[1]:
		cell.font = Font(bold=True)
		cell.fill = PatternFill("solid", fgColor="DDEEFF")
	for row in ws.iter_rows(min_row=2, min_col=2, max_col=4):
		for cell in row:
			cell.number_format = "#,##0"
	ws["A2"].comment = Comment("Signed contracts only", "Huda")
	rule = DataValidation(type="whole", operator="greaterThan", formula1="0")
	rule.add("B2:C3")
	ws.add_data_validation(rule)
	ws.conditional_formatting.add("D2:D3", CellIsRule(operator="greaterThan", formula=["1000000"], fill=PatternFill("solid", fgColor="CCFFCC")))
	ws.add_table(Table(displayName="Lines", ref="A1:D3"))
	ws.column_dimensions["A"].width = 24
	ws.freeze_panes = "B2"
	ws.merge_cells("F1:G1")
	book.create_sheet("Notes")["A1"] = "Ex works Dubai"
	out = io.BytesIO()
	book.save(out)
	return out.getvalue()


def _data(rows: dict, **more) -> dict:
	sheets = {title: {"rows": {str(r): line for r, line in held.items()}} for title, held in rows.items()}
	return {"sheet": {"v": 2, "current": next(iter(sheets)), "sheets": sheets}, **more}


AS_READ = {
	"Budget": {
		0: ["Line", "Q1", "Q2", "Year", "2026-01-01"],
		1: ["Projects", "1200000", "1450000", "=SUM(B2:C2)"],
		2: ["Fees", "40000", "55000", "=SUM(B3:C3)"],
	},
	"Notes": {0: ["Ex works Dubai"]},
}

MERGED = {"Budget": {"masterMap": {"F1": {"r": 0, "c": 5, "rowSpan": 1, "colSpan": 2}}}}


def _patched(rows=AS_READ, **more) -> object:
	data = _data(rows, merge=more.pop("merge", MERGED), **more)
	return load_workbook(io.BytesIO(patching.file(data, _styled(), lambda code: None)), rich_text=True)


def test_a_styled_workbook_loses_nothing_when_saved_over():
	assert fidelity.workbook(_styled()) == []


def test_an_edit_keeps_the_file_as_it_was_around_it():
	edited = {**AS_READ, "Budget": {**AS_READ["Budget"], 1: ["Projects", "1300000", "1450000", "=SUM(B2:C2)"]}}
	ws = _patched(edited)["Budget"]
	assert ws["B2"].value == 1300000
	assert ws["D2"].value == "=SUM(B2:C2)"
	assert ws["A1"].font.bold and ws["A1"].fill.fgColor.rgb.endswith("DDEEFF")
	assert ws["B2"].number_format == "#,##0" and ws["D3"].number_format == "#,##0"
	assert ws["E1"].value == datetime(2026, 1, 1)
	assert ws["A2"].comment.text == "Signed contracts only"
	assert ws.data_validations.dataValidation and ws.conditional_formatting
	assert "Lines" in ws.tables
	assert ws.column_dimensions["A"].width == 24 and ws.freeze_panes == "B2"
	assert "F1:G1" in {str(one) for one in ws.merged_cells.ranges}


def test_cells_typed_and_deleted_and_formats_changed_are_written():
	edited = {**AS_READ, "Budget": {0: AS_READ["Budget"][0], 1: ["Projects", "1200000", "1450000", "=SUM(B2:C2)*2", None, "new"]}}
	formats = {"Budget": {"cells": {"B2": {"numberFormat": "number:2", "bold": True}}, "rows": {}, "cols": {}}}
	ws = _patched(edited, formats=formats)["Budget"]
	assert ws["D2"].value == "=SUM(B2:C2)*2"
	assert ws["F2"].value == "new"
	assert ws["A3"].value is None and ws["D3"].value is None
	assert ws["B2"].number_format == "#,##0.00" and ws["B2"].font.bold
	assert ws["C2"].number_format == "#,##0", "a format the editor read in as it was"


def test_sheets_follow_the_editor():
	book = _patched({"Plan": AS_READ["Budget"], "Extra": {0: ["x"]}})
	assert book.sheetnames == ["Plan", "Extra"], "Budget renamed where it stands, Notes removed, Extra added"
	assert book["Plan"]["A1"].font.bold
	assert book["Extra"]["A1"].value == "x"


def test_widths_and_merges_the_editor_changed():
	ws = _patched(merge={"Budget": {"masterMap": {}}}, view={"Budget": {"colW": {"1": 140}, "freezeRows": 1}})["Budget"]
	assert ws.column_dimensions["B"].width == 20
	assert ws.freeze_panes == "A2"
	assert not ws.merged_cells.ranges


def test_one_of_ones_own_functions_goes_as_its_value():
	edited = {**AS_READ, "Notes": {0: ["Ex works Dubai", '=FIELD("Item","GL","rate")']}}
	ws = _patched(edited, values={"Notes": {"B1": 60}})["Notes"]
	assert ws["B1"].value == 60


def test_what_is_the_same_is_not_written():
	assert patching.same("=_xlfn.STDEV.S(A1:A3)", "=STDEV(A1:A3)")
	assert patching.same(1200000, "1200000") and patching.same(0.1, "0.1")
	assert patching.same(True, "TRUE")
	assert patching.same(datetime(2026, 1, 1), "2026-01-01")
	assert not patching.same(1200000, "1300000")
	assert not patching.same("=A1", "5")
	assert patching.same_format("#,##0.00", "number:2") and patching.same_format('"AED"#,##0.00', "currency:AED:2")
	assert patching.same_format("0.0%", "percentage:1") and patching.same_format("@", "text")
	assert not patching.same_format("#,##0", "number:2")


def test_a_value_is_written_as_its_kind():
	assert patching.typed("12") == 12 and patching.typed("1.5") == 1.5
	assert patching.typed("007") == "007" and patching.typed("12", text=True) == "12"
	assert patching.typed("FALSE") is False
	assert patching.typed("2026-03-01", dated=True) == datetime(2026, 3, 1)
	assert patching.typed("2026-03-01") == "2026-03-01"
