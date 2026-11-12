"""What OneWorkbook and OneWriter would drop from an office file they save
over (one_storage/fidelity.py), read from the file's parts."""

import io
import zipfile
from types import SimpleNamespace

from onedesk.one_storage import fidelity

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


def test_what_a_workbook_drops_is_read_from_its_parts():
	found = fidelity.workbook(
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
				"xl/styles.xml": b'<styleSheet><fonts count="2"/><fills count="2"/><borders count="1"/></styleSheet>',
			}
		)
	)
	assert found == [
		"macros", "comments", "charts", "pivot_tables", "pictures", "tables", "data_validation",
		"conditional_formatting", "external_links", "formatting",
	]  # fmt: skip


def test_a_workbook_of_ones_own_keeps_its_formatting_from_its_own_copy():
	styled = _book(**{"xl/styles.xml": b'<styleSheet><fonts count="3"/><fills count="4"/><borders count="2"/></styleSheet>'})
	assert fidelity.workbook(styled) == ["formatting"]
	assert fidelity.workbook(styled, formatting=False) == []


def test_what_is_not_an_office_file_has_nothing_to_lose():
	assert fidelity.workbook(b"Item,Rate\nGL,60\n") == []
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
