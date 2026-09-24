"""Spreadsheets and CSV, read as rows of cells.

A sheet is read as text a row per line, cells tab-separated, which is what a
model and a search index both read well. Formulas are read as the value they
last showed, never evaluated. Pure; openpyxl and xlrd are imported when a file
needs them.
"""

import csv
import io

#: Rows read from each sheet. A ten-thousand-row export is data to import, not
#: a document to understand, and its first rows say what it is.
MOST_ROWS = 2000


def xlsx(content: bytes) -> str | None:
	try:
		import openpyxl

		book = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
	except Exception:
		return None
	out = []
	for sheet in book.worksheets:
		rows = []
		for row in sheet.iter_rows(values_only=True, max_row=MOST_ROWS):
			cells = ["" if value is None else str(value) for value in row]
			if any(cells):
				rows.append("\t".join(cells).rstrip())
		if rows:
			out.append(f"[{sheet.title}]\n" + "\n".join(rows))
	book.close()
	return "\n\n".join(out).strip()


def xls(content: bytes) -> str | None:
	try:
		import xlrd

		book = xlrd.open_workbook(file_contents=content)
	except Exception:
		return None
	out = []
	for sheet in book.sheets():
		rows = [
			"\t".join(str(value) for value in sheet.row_values(index)).rstrip()
			for index in range(min(sheet.nrows, MOST_ROWS))
		]
		rows = [row for row in rows if row.strip()]
		if rows:
			out.append(f"[{sheet.name}]\n" + "\n".join(rows))
	return "\n\n".join(out).strip()


def delimited(content: bytes) -> str:
	text = decoded(content)
	try:
		dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
	except csv.Error:
		dialect = csv.excel
	rows = []
	for index, row in enumerate(csv.reader(io.StringIO(text), dialect)):
		if index >= MOST_ROWS:
			break
		if any(cell.strip() for cell in row):
			rows.append("\t".join(cell.strip() for cell in row))
	return "\n".join(rows)


def decoded(content: bytes) -> str:
	"""Text in whichever of the usual encodings it was written in."""
	if content.startswith(b"\xef\xbb\xbf"):
		return content[3:].decode("utf-8", "replace")
	if content[:2] in (b"\xff\xfe", b"\xfe\xff"):
		return content.decode("utf-16", "replace")
	try:
		return content.decode("utf-8")
	except UnicodeDecodeError:
		return content.decode("cp1252", "replace")
