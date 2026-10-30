"""A OneWorkbook workbook as an Excel file, for what cannot run the editor:
the network drive and a public link. Written from what the editor saved,
formulas with the values it last worked out, and read back into the
workbook when Excel saves over it. AGENTS.md, excel.py.
"""

import io
import json
import re
from datetime import date, datetime, time

import frappe
from frappe import _

from onedesk.one_sheet import api, storage

SUFFIX = ".xlsx"

MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

#: Functions only OneWorkbook knows: Excel would show #NAME?, so such a cell
#: goes as the value it last showed, and comes back as its formula.
OURS = re.compile(r"\b(RECORD|FIELD|BRAND|IMAGE|SPARKLINE)\s*\(", re.I)

#: An open-ended range, `H6:H`, which Excel does not have.
OPEN_RANGE = re.compile(r"(?<![A-Za-z0-9_$.])(\$?[A-Z]{1,3}\$?\d+):(\$?[A-Z]{1,3})(?![A-Za-z0-9_(!])")

LAST_ROW = 1048576

CLOSED_RANGE = re.compile(rf"(\$?[A-Z]{{1,3}}\$?\d+):(\$?[A-Z]{{1,3}}){LAST_ROW}(?!\d)")

PX_PER_CHAR = 7

DATE_Z = {"dmy": "dd/mm/yyyy", "mdy": "mm/dd/yyyy", "ymd": "yyyy-mm-dd", "long": "d mmm yyyy", "full": "ddd, d mmm yyyy"}

TIME_Z = {"hm": "hh:mm", "hms": "hh:mm:ss", "hm12": "h:mm AM/PM", "hms12": "h:mm:ss AM/PM"}

CACHE = "one_sheet_xlsx"


def letters(col: int) -> str:
	out = ""
	col += 1
	while col:
		col, rest = divmod(col - 1, 26)
		out = chr(65 + rest) + out
	return out


def at(ref: str) -> tuple[int, int] | None:
	found = re.fullmatch(r"([A-Z]+)(\d+)", ref or "")
	if not found:
		return None
	col = 0
	for letter in found.group(1):
		col = col * 26 + ord(letter) - 64
	return int(found.group(2)) - 1, col - 1


def to_excel(formula: str) -> str:
	"""A formula as Excel reads it: an open-ended range closed at the last
	row. Pure."""
	return OPEN_RANGE.sub(lambda m: f"{m.group(1)}:{m.group(2)}{LAST_ROW}", formula)


def from_excel(formula: str) -> str:
	"""A formula from Excel as the editor reads it: Excel's markers before
	newer functions dropped and a range closed at the last row opened
	again. Pure."""
	said = re.sub(r"_xl(fn|ws)\.", "", formula, flags=re.I)
	return CLOSED_RANGE.sub(lambda m: f"{m.group(1)}:{m.group(2)}", said)


def number_format(fmt: str | None, symbol=None) -> str | None:
	"""An editor number format (`currency:EUR:2;`) as an Excel code. Pure but
	for `symbol`, which names a currency's sign."""
	if not fmt:
		return None
	fmt = str(fmt)
	blank = fmt.endswith(";")
	fmt = fmt.rstrip(";")
	if fmt.startswith("custom:"):
		return fmt[7:] or None
	parts = fmt.split(":")
	kind, variant, decimals = parts[0], "", None
	if len(parts) >= 3:
		variant, decimals = parts[1], parts[2]
	elif len(parts) == 2:
		if re.fullmatch(r"-?\d+", parts[1]):
			decimals = parts[1]
		else:
			variant = parts[1]
	places = int(decimals) if decimals not in (None, "") and str(decimals).lstrip("-").isdigit() else None
	dec = lambda n: "." + "0" * n if n and n > 0 else ""  # noqa: E731
	if kind == "text":
		return "@"
	if kind == "number":
		code = "#,##0" + dec(places or 0)
	elif kind == "percentage":
		code = "0" + dec(2 if places is None else places) + "%"
	elif kind == "currency":
		sign = (symbol(variant) if symbol else None) or variant or "$"
		code = f'"{sign} "#,##0' + dec(2 if places is None else places)
	elif kind == "date":
		return DATE_Z.get(variant, DATE_Z["ymd"])
	elif kind == "time":
		return TIME_Z.get(variant, TIME_Z["hm"])
	elif kind == "datetime":
		day, _sep, hour = variant.partition("_")
		return f"{DATE_Z.get(day, DATE_Z['ymd'])} {TIME_Z.get(hour, TIME_Z['hm'])}"
	else:
		return None
	return f"{code};-{code};;@" if blank else code


def _symbol(code: str) -> str | None:
	return frappe.db.get_value("Currency", code, "symbol") if code else None


def _number(value):
	if isinstance(value, bool):
		return None
	if isinstance(value, int | float):
		return value
	text = str(value).strip()
	if not text or re.match(r"^[+0]\d", text):
		return None
	try:
		return float(text) if re.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", text) else None
	except ValueError:
		return None


def _data(name: str) -> dict:
	return json.loads(storage.decode_sheets_data(frappe.db.get_value(api.WORKBOOK, name, "sheets_data")) or "{}")


def _sheets(data: dict) -> dict:
	held = data.get("sheet") if isinstance(data.get("sheet"), dict) else {}
	return held.get("sheets") or {}


def _grid(page: dict) -> dict:
	"""{(row, col): raw} of one stored sheet."""
	out = {}
	for row, line in (page.get("rows") or {}).items():
		for col, raw in enumerate(line or []):
			if raw is not None and raw != "":
				out[(int(row), col)] = raw
	return out


def _format(formats: dict, sheet: str, row: int, col: int) -> dict:
	held = formats.get(sheet) or {}
	if not isinstance(held, dict) or "cells" not in held:
		return {}
	return {
		**(held.get("cols") or {}).get(str(col), {}),
		**(held.get("rows") or {}).get(str(row), {}),
		**(held.get("cells") or {}).get(f"{letters(col)}{row + 1}", {}),
	}


def build(name: str) -> bytes:
	"""The workbook as the bytes of an Excel file. The reader's right to it
	is the caller's to check."""
	import xlsxwriter

	data = _data(name)
	formats = data.get("formats") if isinstance(data.get("formats"), dict) else {}
	values = data.get("values") if isinstance(data.get("values"), dict) else {}
	merges = data.get("merge") if isinstance(data.get("merge"), dict) else {}
	views = data.get("view") if isinstance(data.get("view"), dict) else {}
	out = io.BytesIO()
	book = xlsxwriter.Workbook(out, {"in_memory": True, "strings_to_numbers": False, "strings_to_formulas": False})
	styles = {}

	def style(fmt: dict):
		key = (number_format(fmt.get("numberFormat"), _symbol), bool(fmt.get("bold")), bool(fmt.get("italic")))
		if key == (None, False, False):
			return None
		if key not in styles:
			spec = {"num_format": key[0]} if key[0] else {}
			spec.update({"bold": key[1], "italic": key[2]})
			styles[key] = book.add_format(spec)
		return styles[key]

	used = set()
	for title, page in (_sheets(data) or {"Sheet1": {}}).items():
		label = re.sub(r"[\[\]:*?/\\]", " ", str(title))[:31].strip() or "Sheet"
		while label.lower() in used:
			label = (label[:28] + " " + str(len(used) + 1))[:31]
		used.add(label.lower())
		ws = book.add_worksheet(label)
		known = (values.get(title) or {}) if isinstance(values, dict) else {}
		for (row, col), raw in sorted(_grid(page or {}).items()):
			look = style(_format(formats, title, row, col))
			if isinstance(raw, str) and raw.startswith("="):
				said = known.get(f"{letters(col)}{row + 1}")
				if OURS.search(raw):
					_value(ws, row, col, said, look)
				else:
					ws.write_formula(row, col, to_excel(raw), look, "" if said is None else said)
			else:
				_value(ws, row, col, raw, look)
		view = views.get(title) if isinstance(views.get(title), dict) else {}
		for col, width in (view.get("colW") or {}).items():
			if str(col).isdigit():
				ws.set_column(int(col), int(col), max(1, round(float(width) / PX_PER_CHAR, 1)))
		for col in view.get("hiddenCols") or []:
			if str(col).isdigit():
				ws.set_column(int(col), int(col), None, None, {"hidden": True})
		for found in ((merges.get(title) or {}).get("masterMap") or {}).values():
			r, c, rs, cs = found.get("r"), found.get("c"), found.get("rowSpan", 1), found.get("colSpan", 1)
			if isinstance(r, int) and isinstance(c, int) and (rs > 1 or cs > 1):
				first = _grid(page or {}).get((r, c))
				ws.merge_range(r, c, r + rs - 1, c + cs - 1, "", style(_format(formats, title, r, c)))
				if first is not None and not (isinstance(first, str) and first.startswith("=")):
					_value(ws, r, c, first, style(_format(formats, title, r, c)))
		if view.get("freezeRows") or view.get("freezeCols"):
			ws.freeze_panes(int(view.get("freezeRows") or 0), int(view.get("freezeCols") or 0))
	book.close()
	return out.getvalue()


def _value(ws, row: int, col: int, value, look) -> None:
	if value is None or value == "":
		ws.write_blank(row, col, None, look)
	elif isinstance(value, bool) or value in ("TRUE", "FALSE"):
		ws.write_boolean(row, col, value is True or value == "TRUE", look)
	elif (number := _number(value)) is not None:
		ws.write_number(row, col, number, look)
	else:
		ws.write_string(row, col, str(value), look)


def xlsx(name: str) -> bytes:
	"""`build`, kept until the workbook changes."""
	modified = frappe.db.get_value(api.WORKBOOK, name, "modified")
	key = f"{name}:{modified}"
	held = frappe.cache.hget(CACHE, key)
	if held:
		return held
	made = build(name)
	frappe.cache.hset(CACHE, key, made)
	frappe.cache.expire(CACHE, 600)
	return made


def _plain(value):
	"""A value Excel saved, as the editor stores it."""
	if value is None:
		return None
	if isinstance(value, bool):
		return "TRUE" if value else "FALSE"
	if isinstance(value, datetime):
		return value.strftime("%Y-%m-%d %H:%M:%S") if (value.hour or value.minute or value.second) else value.strftime("%Y-%m-%d")
	if isinstance(value, date):
		return value.strftime("%Y-%m-%d")
	if isinstance(value, time):
		return value.strftime("%H:%M")
	if isinstance(value, float) and value.is_integer():
		return int(value)
	return value


def read(name: str, content: bytes) -> dict:
	"""What Excel saved, as the workbook's content: its values and formulas
	in place of the sheets', everything else the workbook keeps (formats,
	widths, notes) as it was. A cell OneWorkbook alone can work out, sent as
	its value, gets its formula back when the value is unchanged."""
	from openpyxl import load_workbook

	try:
		formulas = load_workbook(io.BytesIO(content), data_only=False)
		shown = load_workbook(io.BytesIO(content), data_only=True)
	except Exception:
		frappe.throw(_("This file cannot be opened."))
	data = _data(name)
	before = _sheets(data)
	values = data.get("values") if isinstance(data.get("values"), dict) else {}
	pages = {}
	for ws in formulas.worksheets:
		title = ws.title
		old = _grid(before.get(title) or {})
		known = values.get(title) or {}
		rows = {}
		for line in ws.iter_rows():
			for cell in line:
				raw = cell.value
				if raw is None:
					continue
				if hasattr(raw, "text"):
					raw = raw.text
				if isinstance(raw, str) and raw.startswith("="):
					raw = from_excel(raw)
				else:
					raw = _plain(raw)
				r, c = cell.row - 1, cell.column - 1
				was = old.get((r, c))
				if isinstance(was, str) and OURS.search(was) and _same(raw, known.get(f"{letters(c)}{r + 1}")):
					raw = was
				line_ = rows.setdefault(str(r), [])
				line_.extend([None] * (c + 1 - len(line_)))
				line_[c] = raw
		for (r, c), was in old.items():
			if isinstance(was, str) and OURS.search(was) and shown[title].cell(row=r + 1, column=c + 1).value is None:
				line_ = rows.setdefault(str(r), [])
				line_.extend([None] * (c + 1 - len(line_)))
				line_[c] = was
		pages[title] = {**(before.get(title) or {}), "rows": rows}
	held = data.get("sheet") if isinstance(data.get("sheet"), dict) else {"v": 2}
	current = held.get("current") if held.get("current") in pages else next(iter(pages), "Sheet1")
	data["sheet"] = {**held, "v": 2, "current": current, "sheets": pages}
	return data


def _same(a, b) -> bool:
	if a == b:
		return True
	x, y = _number(a) if a is not None else None, _number(b) if b is not None else None
	return x is not None and y is not None and abs(x - y) < 1e-9


def write(name: str, content: bytes) -> None:
	"""Excel's save, through the editor's own save so a version is kept. A
	record's workbook is not written from outside: its table is worked out
	in the editor."""
	if frappe.db.get_value(api.WORKBOOK, name, "bound_doctype"):
		frappe.throw(_("A record's workbook can only be edited in OneWorkbook."), frappe.PermissionError)
	item = api._may(name, "write")
	data = read(name, content)
	api.save_sheet(item.get("file_name"), json.dumps(data, default=str), name, request_id=frappe.generate_hash(length=12))
