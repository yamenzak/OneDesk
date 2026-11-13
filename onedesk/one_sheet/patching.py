"""An Excel file with what OneSheet changed written into it, so that
everything else the file holds stays as it was: its fonts, fills, borders,
comments, data validation, conditional formatting, tables, defined names,
freeze panes and print settings. Each cell the editor holds is set where its
value or formula differs from the file's, a cell it no longer holds is
cleared, and sheets, merges, number formats, bold and italic, widths, heights
and frozen rows follow the editor where it changed them. What openpyxl cannot
save is fidelity.workbook's list. AGENTS.md, Excel and CSV files."""

import io
import re
from copy import copy
from datetime import date, datetime, time, timedelta

import frappe
from frappe import _

from onedesk.one_sheet import excel

CLASSIC = {
	"CEILING.MATH": "CEILING",
	"CEILING.PRECISE": "CEILING",
	"FLOOR.MATH": "FLOOR",
	"FLOOR.PRECISE": "FLOOR",
	"STDEV.S": "STDEV",
	"STDEV.P": "STDEVP",
	"VAR.S": "VAR",
	"VAR.P": "VARP",
	"PERCENTILE.INC": "PERCENTILE",
}

ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?")

EXCEL_DAY = datetime(1899, 12, 30)

PT_PER_PX = 0.75


def file(data: dict, content: bytes, symbol=None) -> bytes:
	"""The Excel file `content` with the workbook `data` (as the editor
	saves it) written into it. Pure but for `symbol`, which names a
	currency's sign."""
	from openpyxl import load_workbook

	try:
		book = load_workbook(io.BytesIO(content), keep_vba=False, keep_links=True, rich_text=True)
		listing = load_workbook(io.BytesIO(content), read_only=True, keep_links=False)
	except Exception:
		frappe.throw(_("This file cannot be opened."))
	try:
		held = {ws.title: _held(ws) for ws in listing.worksheets}
	finally:
		listing.close()
	sheets = excel._sheets(data) or {}
	formats = data.get("formats") if isinstance(data.get("formats"), dict) else {}
	values = data.get("values") if isinstance(data.get("values"), dict) else {}
	merges = data.get("merge") if isinstance(data.get("merge"), dict) else {}
	views = data.get("view") if isinstance(data.get("view"), dict) else {}
	pages = _paired([ws.title for ws in book.worksheets], list(sheets))
	kept = {title: book[was] for title, was in pages.items()}
	for ws in list(book.worksheets):
		if ws.title not in pages.values():
			book.remove(ws)
	used = set()
	for index, title in enumerate(sheets):
		was = pages.get(title)
		ws = kept.get(title) or book.create_sheet()
		ws.title = excel.sheet_label(title, used)
		target = book.worksheets[index]
		if target is not ws:
			book.move_sheet(ws, book.sheetnames.index(target.title) - book.sheetnames.index(ws.title))
		_merges(ws, merges.get(title))
		_cells(ws, sheets[title] or {}, held.get(was) or {}, formats, title, (values.get(title) or {}) if isinstance(values, dict) else {}, symbol)
		_view(ws, views.get(title) if isinstance(views.get(title), dict) else {})
	if not book.worksheets:
		book.create_sheet("Sheet1")
	book.active = 0
	book.calculation.fullCalcOnLoad = True
	out = io.BytesIO()
	book.save(out)
	return out.getvalue()


def _held(ws) -> dict:
	"""{(row, col): value} of a read-only sheet's cells that hold one."""
	out = {}
	for line in ws.iter_rows():
		for cell in line:
			if cell.value is not None and getattr(cell, "row", None):
				out[(cell.row - 1, cell.column - 1)] = cell.value
	return out


def _paired(held: list[str], wanted: list[str]) -> dict:
	"""{editor's sheet: the file's sheet it is}: by name, else a sheet
	renamed in the editor where it stands. Pure."""
	lower = {title.lower(): title for title in held}
	out = {title: lower[title.lower()] for title in wanted if title.lower() in lower}
	taken = set(out.values())
	for index, title in enumerate(wanted):
		if title not in out and index < len(held) and held[index] not in taken and held[index].lower() not in {one.lower() for one in wanted}:
			out[title] = held[index]
			taken.add(held[index])
	return out


def _cells(ws, page: dict, held: dict, formats: dict, title: str, known: dict, symbol) -> None:
	from openpyxl.cell.cell import MergedCell

	grid = excel._grid(page)
	for (r, c) in held:
		if (r, c) not in grid:
			cell = ws.cell(row=r + 1, column=c + 1)
			if not isinstance(cell, MergedCell):
				cell.value = None
	looks = formats.get(title) if isinstance(formats.get(title), dict) else {}
	styled = {excel.at(ref) for ref in looks.get("cells") or {}} - {None}
	for r, c in sorted(set(grid) | styled):
		cell = ws.cell(row=r + 1, column=c + 1)
		if isinstance(cell, MergedCell):
			continue
		look = excel._format(formats, title, r, c)
		fmt = look.get("numberFormat")
		if fmt and not same_format(cell.number_format, fmt):
			cell.number_format = excel.number_format(fmt, symbol) or "General"
		if (r, c) in grid:
			raw = grid[(r, c)]
			wanted = known.get(f"{excel.letters(c)}{r + 1}") if isinstance(raw, str) and excel.OURS.search(raw) else raw
			if not same(held.get((r, c)), wanted):
				cell.value = typed(wanted, cell.is_date, str(fmt or "").startswith("text"))
		for key in ("bold", "italic"):
			if look.get(key) is True and not getattr(cell.font, key):
				font = copy(cell.font)
				setattr(font, key, True)
				cell.font = font


def _merges(ws, held) -> None:
	"""The editor's merged ranges, where it holds them."""
	if not isinstance(held, dict):
		return
	wanted = set()
	for found in (held.get("masterMap") or {}).values():
		r, c, rs, cs = found.get("r"), found.get("c"), found.get("rowSpan", 1), found.get("colSpan", 1)
		if isinstance(r, int) and isinstance(c, int) and (rs > 1 or cs > 1):
			wanted.add(f"{excel.letters(c)}{r + 1}:{excel.letters(c + cs - 1)}{r + rs}")
	there = {str(one) for one in ws.merged_cells.ranges}
	for one in there - wanted:
		ws.unmerge_cells(one)
	for one in sorted(wanted - there):
		ws.merge_cells(one)


def _view(ws, view: dict) -> None:
	"""Widths and heights the editor set, and its frozen rows and columns."""
	for col, width in (view.get("colW") or {}).items():
		if str(col).isdigit():
			ws.column_dimensions[excel.letters(int(col))].width = max(1, round(float(width) / excel.PX_PER_CHAR, 2))
	for row, height in (view.get("rowH") or {}).items():
		if str(row).isdigit():
			ws.row_dimensions[int(row) + 1].height = round(float(height) * PT_PER_PX, 2)
	rows, cols = int(view.get("freezeRows") or 0), int(view.get("freezeCols") or 0)
	if rows or cols:
		ws.freeze_panes = f"{excel.letters(cols)}{rows + 1}"


def formula(said: str) -> str:
	"""A formula as compared: Excel's markers and newer names as the editor
	reads them, and no spaces. Pure."""
	said = excel.from_excel(str(said))
	for dotted, classic in CLASSIC.items():
		said = re.sub(rf"\b{re.escape(dotted)}\s*\(", f"{classic}(", said, flags=re.I)
	return re.sub(r"\s+", "", said)


def same(was, raw) -> bool:
	"""Whether a cell the file holds already says what the editor holds. Pure."""
	if raw is None or raw == "":
		return was is None or was == ""
	if was is None:
		return False
	if isinstance(raw, str) and raw.startswith("="):
		return isinstance(was, str) and was.startswith("=") and formula(was) == formula(raw)
	if isinstance(was, str) and was.startswith("="):
		return False
	if isinstance(was, datetime | date | time):
		return _moment(was) == _moment(_when(raw))
	return str(excel._plain(was)) == str(excel._plain(raw)) or excel._same(was, raw)


def _when(raw):
	found = ISO.fullmatch(str(raw).strip())
	if not found:
		return None
	parts = [int(one or 0) for one in found.groups()]
	try:
		return datetime(*parts)
	except ValueError:
		return None


def _moment(value):
	if value is None:
		return None
	if isinstance(value, time):
		return EXCEL_DAY + timedelta(hours=value.hour, minutes=value.minute, seconds=value.second)
	if isinstance(value, datetime):
		return value.replace(microsecond=0)
	return datetime(value.year, value.month, value.day)


def typed(raw, dated: bool = False, text: bool = False):
	"""What the editor holds as the value openpyxl writes: a formula, a
	boolean, a number, a date where the cell shows dates, else text. Pure."""
	if raw is None or raw == "":
		return None
	if isinstance(raw, bool | int | float):
		return raw
	said = str(raw)
	if said.startswith("="):
		return excel.to_excel(said)
	if text:
		return said
	if said in ("TRUE", "FALSE"):
		return said == "TRUE"
	if (number := excel._number(said)) is not None:
		return int(number) if isinstance(number, float) and number.is_integer() and re.fullmatch(r"-?\d+", said) else number
	if dated and (when := _when(said)):
		return when
	return said


def same_format(code: str | None, fmt: str) -> bool:
	"""Whether an Excel number format code reads in as the editor's format
	`fmt`, so the file's own code is kept. Pure."""
	fmt = str(fmt or "")
	kind = format_of(code)
	if kind.startswith("currency:") and fmt.startswith("currency:"):
		return kind.rsplit(":", 1)[-1] == fmt.rsplit(":", 1)[-1]
	return kind == fmt


def format_of(code: str | None) -> str:
	"""An Excel number format code as the editor reads it in (xlsx-io.js
	zToNumFmt). Pure."""
	said = (code or "").strip()
	if not said or said == "General":
		return ""
	if said == "@":
		return "text"
	dates = {value: key for key, value in excel.DATE_Z.items()}
	times = {value: key for key, value in excel.TIME_Z.items()}
	if said in dates:
		return f"date:{dates[said]}"
	if said in times:
		return f"time:{times[said]}"
	day, _sep, hour = said.partition(" ")
	if day in dates and hour in times:
		return f"datetime:{dates[day]}_{times[hour]}"
	places = len(found.group(1)) if (found := re.search(r"\.(0+)", said)) else 0
	if _percent(said):
		return "percentage" if places == 2 else f"percentage:{places}"
	if re.match(r'^"([^"]+)"#,##0', said):
		return f"currency:?:{places}"
	if re.fullmatch(r"#,##0(\.0+)?", said):
		return "number" if not places else f"number:{places}"
	return f"custom:{code}"


def _percent(code: str) -> bool:
	quoted, skip = False, False
	for one in code:
		if skip:
			skip = False
		elif one == "\\":
			skip = True
		elif one == '"':
			quoted = not quoted
		elif one == "%" and not quoted:
			return True
	return False
