"""What OneWorkbook and OneWriter would drop from an office file they save
over (one_cloud/fidelity.py), read from the file's parts."""

import io
import zipfile
from types import SimpleNamespace

from onedesk.one_cloud import fidelity

PLAIN_STYLES = b'<styleSheet><fonts count="1"/><fills count="2"/><borders count="1"/></styleSheet>'
SHEET = b"<worksheet><sheetData/></worksheet>"
BODY = b"<w:document><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body></w:document>"


def _zip(parts: dict) -> bytes:
	out = io.BytesIO()
	with zipfile.ZipFile(out, "w") as made:
		for name, body in parts.items():
			made.writestr(name, body)
	return out.getvalue()


def _book(**more) -> bytes:
	return _zip({"xl/workbook.xml": b"<workbook/>", "xl/styles.xml": PLAIN_STYLES, "xl/worksheets/sheet1.xml": SHEET, **more})


def _letter(body: bytes = BODY, **more) -> bytes:
	return _zip({"word/document.xml": body, **more})


def test_a_plain_workbook_loses_nothing():
	assert fidelity.workbook(_book()) == []
	assert fidelity.read_in(_book()) == []


def _made(build) -> bytes:
	from openpyxl import Workbook

	book = Workbook()
	build(book.active)
	out = io.BytesIO()
	book.save(out)
	return out.getvalue()


def test_saving_over_keeps_what_openpyxl_keeps():
	from openpyxl.comments import Comment
	from openpyxl.formatting.rule import ColorScaleRule
	from openpyxl.styles import Border, Font, PatternFill, Side
	from openpyxl.worksheet.datavalidation import DataValidation
	from openpyxl.worksheet.table import Table

	def build(ws):
		ws.append(["Line", "Amount"])
		ws.append(["Rent", 15000])
		ws["A1"].font = Font(bold=True, color="FF0000")
		ws["A1"].fill = PatternFill("solid", fgColor="FFFF00")
		ws["A1"].border = Border(bottom=Side(style="thin"))
		ws["B2"].comment = Comment("Monthly", "Huda")
		rule = DataValidation(type="list", formula1='"Rent,Fees"')
		rule.add("A2")
		ws.add_data_validation(rule)
		ws.conditional_formatting.add("B2", ColorScaleRule(start_type="min", start_color="FFFFFF", end_type="max", end_color="00FF00"))
		ws.add_table(Table(displayName="Costs", ref="A1:B2"))

	made = _made(build)
	assert fidelity.workbook(made) == []
	assert fidelity.read_in(made) == ["comments", "tables", "data_validation", "conditional_formatting"]


def test_saving_over_a_chart_changes_it():
	from openpyxl.chart import BarChart, Reference

	def build(ws):
		ws.append(["Q1", 10])
		ws.append(["Q2", 20])
		chart = BarChart()
		chart.add_data(Reference(ws, min_col=2, min_row=1, max_row=2))
		ws.add_chart(chart, "D2")

	assert fidelity.workbook(_made(build)) == ["charts"]


def test_what_saving_over_drops_is_read_from_its_parts():
	extended = "".join(f'<ext uri="{uri.decode()}"/>' for uri in fidelity.EXTENDED.values())
	found = fidelity.workbook(
		_book(
			**{
				"xl/vbaProject.bin": b"x",
				"xl/threadedComments/threadedComment1.xml": b"<t/>",
				"xl/charts/chart1.xml": b"<c/>",
				"xl/slicers/slicer1.xml": b"<s/>",
				"xl/media/image1.emf": b"emf",
				"xl/media/image2.png": b"png",
				"xl/worksheets/sheet2.xml": f"<worksheet><extLst>{extended}</extLst></worksheet>".encode(),
				"xl/drawings/drawing1.xml": b"<xdr:wsDr><xdr:twoCellAnchor><xdr:sp/></xdr:twoCellAnchor></xdr:wsDr>",
				"xl/embeddings/oleObject1.bin": b"x",
				"xl/ctrlProps/ctrlProp1.xml": b"<c/>",
				"xl/connections.xml": b"<connections/>",
				"xl/pivotTables/pivotTable1.xml": b"<p/>",
				"xl/externalLinks/externalLink1.xml": b"<e/>",
				"xl/comments1.xml": b"<comments/>",
			}
		)
	)
	assert found == [
		"macros", "comments", "charts", "slicers", "pictures", "data_validation", "conditional_formatting",
		"sparklines", "text_boxes", "embedded_files", "form_controls", "connections",
	]  # fmt: skip


def test_what_a_workbook_of_ones_own_drops_is_read_from_its_parts():
	found = fidelity.read_in(
		_book(
			**{
				"xl/vbaProject.bin": b"x",
				"xl/comments1.xml": b"<comments/>",
				"xl/charts/chart1.xml": b"<c/>",
				"xl/pivotTables/pivotTable1.xml": b"<p/>",
				"xl/media/image1.png": b"png",
				"xl/tables/table1.xml": b"<table/>",
				"xl/externalLinks/externalLink1.xml": b"<e/>",
				"xl/worksheets/sheet2.xml": b"<worksheet><dataValidations count='1'><dataValidation/></dataValidations><conditionalFormatting/></worksheet>",
				"xl/styles.xml": b'<styleSheet><fonts count="3"/><fills count="4"/><borders count="2"/></styleSheet>',
			}
		)
	)
	assert found == [
		"macros", "comments", "charts", "pivot_tables", "pictures", "tables", "data_validation",
		"conditional_formatting", "external_links",
	]  # fmt: skip


def test_what_is_not_an_office_file_has_nothing_to_lose():
	assert fidelity.workbook(b"Item,Rate\nGL,60\n") == []
	assert fidelity.read_in(b"Item,Rate\nGL,60\n") == []
	assert fidelity.document(b"") == []


def test_a_plain_letter_loses_nothing():
	assert fidelity.document(_letter()) == []
	assert fidelity.document(_letter(**{"word/footnotes.xml": b'<w:footnotes><w:footnote w:type="separator" w:id="-1"/></w:footnotes>'})) == [], "only the separators Word always writes"
	assert fidelity.document(_letter(**{"word/header1.xml": b"<w:hdr><w:p/></w:hdr>"})) == [], "an empty header"


def test_what_a_letter_drops_is_read_from_its_parts():
	body = (
		b"<w:document><w:body><w:p><w:ins><w:r><w:t>new</w:t></w:r></w:ins>"
		b"<w:hyperlink><w:r><w:t>site</w:t></w:r></w:hyperlink><w:r><w:rPr><w:color w:val=\"FF0000\"/></w:rPr><w:t>red</w:t></w:r>"
		b"<w:r><w:txbxContent/></w:r><m:oMath/><w:fldSimple w:instr=\"TOC\"/></w:p></w:body></w:document>"
	)
	found = fidelity.document(
		_letter(
			body,
			**{
				"word/vbaProject.bin": b"x",
				"word/comments.xml": b"<w:comments><w:comment w:id=\"0\"/></w:comments>",
				"word/footer1.xml": b"<w:ftr><w:p><w:r><w:t>Page</w:t></w:r></w:p></w:ftr>",
				"word/footnotes.xml": b"<w:footnotes><w:footnote w:id=\"1\"/></w:footnotes>",
				"word/charts/chart1.xml": b"<c/>",
				"word/embeddings/sheet.xlsx": b"x",
			},
		)
	)
	assert found == [
		"macros", "comments", "tracked_changes", "headers_and_footers", "footnotes", "charts", "text_boxes",
		"equations", "embedded_files", "links", "fields", "text_formatting",
	]  # fmt: skip


def test_a_document_of_ones_own_never_had_fonts_and_colours():
	red = _letter(b'<w:document><w:r><w:rPr><w:color w:val="FF0000"/></w:rPr></w:r></w:document>')
	assert fidelity.document(red) == ["text_formatting"]
	assert fidelity.document(red, formatting=False) == []


def test_only_a_style_the_reader_did_not_know_and_one_did_not_write_counts():
	said = lambda text: SimpleNamespace(type="warning", message=text)  # noqa: E731
	assert fidelity.document(_letter(), [said("Unrecognised paragraph style: Title (Style ID: Title)")]) == ["styles"]
	assert fidelity.document(_letter(), [said("Unrecognised paragraph style: Quote (Style ID: Quote)")], built=("Quote",)) == []
	assert fidelity.document(_letter(), [said("Unrecognised run style: None (Style ID: CommentReference)")]) == [], "comments are read from their part"
	assert fidelity.document(_letter(), [said("Paragraph style with ID CommentText was referenced but not defined")]) == []


def test_macros_and_older_formats_open_read_only():
	assert fidelity.read_only("Budget.xlsm", [])
	assert fidelity.read_only("Letter.docm", [])
	assert fidelity.read_only("Budget.xlsx", ["macros"]), "macros inside an xlsx"
	assert fidelity.read_only("Old.XLS", [])
	assert fidelity.read_only("Budget.xlsx", ["comments"]) is None
	assert fidelity.read_only("rows.csv", []) is None
