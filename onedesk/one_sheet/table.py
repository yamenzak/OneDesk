"""A record's table as the first sheet of a workbook. The table's button on
the form opens it, made the first time; what is typed in that sheet becomes
the table through the record's own save, so every rule the record has
applies. README, table.py.
"""

import hashlib
import html
import json
import re
from datetime import date, datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import flt, strip_html

from onedesk.one_sheet import api, storage
from onedesk.one_sheet.cells import letters

NUMBER = ("Int", "Float", "Currency", "Percent", "Rating", "Duration")
TEXT = ("Data", "Small Text", "Text", "Long Text", "Link", "Dynamic Link", "Read Only", "Phone", "Autocomplete", "Color", "Attach", "Attach Image")
#: Long formatted text: a column only when the grid's gear picks it, shown
#: and taken as plain text.
LONG = ("Text Editor", "Code", "Markdown Editor", "HTML Editor")
SHOWN = (*NUMBER, *TEXT, *LONG, "Select", "Check", "Date", "Datetime", "Time")

MOST_COLUMNS, MOST_ROWS = 20, 1000

#: Empty lines under the table that carry its dropdowns and number rules.
SPARE = 200

#: How far down a locked column is locked.
LOCKED_TO = 100_000

#: The hidden first column's header: this, then what the table held when the
#: sheet last matched it.
MARK = "#"

YES, NO = ("TRUE", "1", "YES", "Y"), ("FALSE", "0", "NO", "N", "")
EPOCH = date(1899, 12, 30)
SAVEPOINT = "one_sheet_table"

#: Cache key of the record types some workbook has a table of.
BOUND_KEY = "one_sheet_bound_doctypes"


def columns(fields: list[dict], picked: list[str] | None = None) -> list[dict]:
	"""The hidden row id, then the table's columns as the form's grid shows
	them: the ones chosen on the grid's gear when there are any (`picked`),
	else the fields in its list view; and the required ones either way.
	Formatted text is a column only when asked for. Pure."""
	usable = [
		df
		for df in fields
		if df.get("fieldtype") in SHOWN and not df.get("hidden") and (df["fieldtype"] not in LONG or df["fieldname"] in (picked or []))
	]
	by = {df["fieldname"]: df for df in usable}
	if picked:
		chosen = [by[name] for name in picked if name in by]
		chosen += [df for df in usable if df.get("reqd") and df["fieldname"] not in picked]
	else:
		chosen = [df for df in usable if df.get("in_list_view") or df.get("reqd")] or usable[:8]
	out, seen = [{"fieldname": "name", "header": MARK, "fieldtype": "Data", "read_only": True}], set()
	for df in chosen[:MOST_COLUMNS]:
		header = _(df.get("label")) if df.get("label") else df["fieldname"]
		if header in seen:
			header = f"{header} ({df['fieldname']})"
		seen.add(header)
		out.append(
			{
				"fieldname": df["fieldname"],
				"header": header,
				"fieldtype": df["fieldtype"],
				"options": [one for one in (df.get("options") or "").split("\n") if one] if df["fieldtype"] == "Select" else None,
				"link": df.get("options") if df["fieldtype"] == "Link" else None,
				"precision": int(df["precision"]) if str(df.get("precision") or "").strip().isdigit() else None,
				"read_only": bool(df.get("read_only") or df["fieldtype"] == "Read Only" or (df.get("fetch_from") and not df.get("fetch_if_empty"))),
			}
		)
	return out


def shown(value, fieldtype: str) -> str:
	"""A field's value as its cell holds it. Pure."""
	if fieldtype == "Check":
		return "TRUE" if value else "FALSE"
	if value is None or value == "":
		return ""
	if fieldtype == "Text Editor":
		return html.unescape(re.sub(r"<[^>]+>", " ", str(value))).strip() if "<" in str(value) else str(value)
	if fieldtype in NUMBER:
		number = float(value)
		return str(int(number)) if number.is_integer() else repr(number)
	return str(value)


def taken(text, column: dict) -> tuple:
	"""A cell's text as the field's value, and why not when it can't be. Pure."""
	kind, text = column["fieldtype"], str(text if text is not None else "").strip()
	if kind == "Check":
		if text.upper() in YES:
			return 1, None
		if text.upper() in NO:
			return 0, None
		return None, _("{0} must be TRUE or FALSE.").format(column["header"])
	if not text:
		return (0 if kind in NUMBER else None), None
	if kind in NUMBER:
		try:
			number = float(text.replace(",", ""))
		except ValueError:
			return None, _("{0} must be a number.").format(column["header"])
		if kind == "Int" and not number.is_integer():
			return None, _("{0} must be a whole number.").format(column["header"])
		return (int(number) if kind == "Int" else number), None
	if kind == "Date":
		try:
			return date.fromisoformat(text[:10]), None
		except ValueError:
			pass
		try:
			return EPOCH + timedelta(days=int(float(text))), None
		except (ValueError, OverflowError):
			return None, _("{0} must be a date, such as 2026-10-21.").format(column["header"])
	if kind == "Datetime":
		try:
			return datetime.fromisoformat(text), None
		except ValueError:
			return None, _("{0} must be a date and time, such as 2026-10-21 09:30.").format(column["header"])
	if kind == "Time":
		try:
			return time.fromisoformat(text).isoformat(), None
		except ValueError:
			return None, _("{0} must be a time, such as 09:30.").format(column["header"])
	if kind == "Select" and column.get("options") and text not in column["options"]:
		return None, _("{0} must be one of: {1}.").format(column["header"], ", ".join(column["options"]))
	return text, None


def lined(message: str, rows: list[dict]) -> str:
	"""The record's "Row #3" or "Row 3" as the sheet's line for that row, so
	its refusals and the sheet's own point at the same line. Pure."""
	said = {_("Row #{0}"), _("Row {0}"), "Row #{0}", "Row {0}"}
	pattern = "|".join(re.escape(one).replace(re.escape("{0}"), r"(\d+)") + r"(?!\d)" for one in sorted(said, key=len, reverse=True))

	def line(found):
		at = int(next(one for one in found.groups() if one))
		return _("Row {0}").format(rows[at - 1]["line"]) if 0 < at <= len(rows) else found.group(0)

	return re.sub(pattern, line, message)


def pinned(message: str, rows: list[dict], cols: list[dict], at: dict) -> list[dict]:
	"""The cell a record's refusal is about: its line from "Row 4", its
	column from the header the message names first, else the line's first
	column. None when it names no line. Pure."""
	lines = {row["line"] for row in rows}
	found = re.search(re.escape(_("Row {0}")).replace(re.escape("{0}"), r"(\d+)"), message or "")
	if not found or int(found.group(1)) not in lines:
		return []
	said = message.lower()
	named = [col for col in cols[1:] if col["fieldname"] in at and col["header"].lower() in said]
	col = min(named, key=lambda one: (said.index(one["header"].lower()), -len(one["header"]))) if named else next((one for one in cols[1:] if one["fieldname"] in at), None)
	if not col:
		return []
	return [{"cell": f"{letters(at[col['fieldname']])}{found.group(1)}", "message": message}]


def fingerprint(docstatus: int, rows: list, cols: list[dict]) -> str:
	"""What the table holds, short: the sheet carries the one it last matched. Pure."""
	held = [int(docstatus or 0)]
	held += [[row.get("name")] + [shown(row.get(col["fieldname"]), col["fieldtype"]) for col in cols[1:]] for row in rows]
	return hashlib.sha1(json.dumps(held, default=str).encode("utf-8")).hexdigest()[:16]


def _rule(col: dict) -> dict | None:
	if col["fieldtype"] == "Link" and col.get("link"):
		return {"type": "link", "doctype": col["link"]}
	if col["fieldtype"] == "Select" and col.get("options"):
		return {"type": "list", "options": col["options"], "message": _("Select a value from the list.")}
	if col["fieldtype"] == "Check":
		return {"type": "checkbox", "message": _("Enter TRUE or FALSE.")}
	if col["fieldtype"] == "Int":
		return {"type": "number", "operator": "between", "min": None, "max": None, "whole": True, "message": _("Enter a whole number.")}
	if col["fieldtype"] in NUMBER:
		return {"type": "number", "operator": "between", "min": None, "max": None, "message": _("Enter a number.")}
	if col["fieldtype"] == "Date":
		return {"type": "date", "message": _("Enter a date, for example 2026-10-21.")}
	return None


def kept(stored: dict, cols: list[dict]) -> dict:
	"""The formulas typed under the bound sheet's header, by line and the
	field each column is: a table sheet keeps them when it is drawn again,
	and a template carries them. Pure."""
	header = [str(one if one is not None else "").strip() for one in (stored.get("0") or [])]
	field = {header.index(col["header"]): col["fieldname"] for col in cols[1:] if col["header"] in header}
	out = {}
	for line, values in stored.items():
		if not str(line).isdigit() or int(line) < 1:
			continue
		for at, value in enumerate(values or []):
			if at in field and isinstance(value, str) and value.startswith("="):
				out[(int(line), field[at])] = value
	return out


def laid(cols: list[dict], rows: list, mark: str, locked: bool, formulas: dict | None = None) -> dict:
	"""The bound sheet as the editor keeps it: the header, a line a row, the
	formulas kept from before, the dropdowns and number rules, the header,
	row id and worked-out columns locked, and the row id hidden. A column
	with a formula on its first line is that formula's, which fills it down,
	so the table's values aren't written under it. Pure."""
	formulas = formulas or {}
	fed = {field for (line, field) in formulas if line == 1}
	cells = {"0": [MARK + mark] + [col["header"] for col in cols[1:]]}
	for at, row in enumerate(rows, 1):
		cells[str(at)] = [row.get("name")] + [None if col["fieldname"] in fed else shown(row.get(col["fieldname"]), col["fieldtype"]) or None for col in cols[1:]]
	where = {col["fieldname"]: at for at, col in enumerate(cols)}
	for (line, field), formula in formulas.items():
		if field not in where:
			continue
		held = cells.setdefault(str(line), [])
		held.extend([None] * (where[field] + 1 - len(held)))
		held[where[field]] = formula
	rules = {}
	for at, col in enumerate(cols):
		rule = None if not at or col["read_only"] or col["fieldname"] in fed else _rule(col)
		for line in range(2, len(rows) + SPARE + 2) if rule else ():
			rules[f"{letters(at)}{line}"] = rule
	ranges = [(0, 0, 0, len(cols) - 1), (0, 0, LOCKED_TO, 0)]
	ranges += [(1, at, LOCKED_TO, at) for at, col in enumerate(cols) if at and col["read_only"]]
	return {
		"rows": cells,
		"validation": rules,
		"protection": {
			"locked": bool(locked),
			"ranges": [{"id": n, "r0": r0, "c0": c0, "r1": r1, "c1": c1, "description": ""} for n, (r0, c0, r1, c1) in enumerate(ranges, 1)],
		},
		"view": {"freezeRows": 1, "hiddenCols": [0]},
	}


def stored(data: dict, sheet: str) -> dict:
	"""A sheet's lines as the workbook keeps them. Pure."""
	return ((((data.get("sheet") or {}).get("sheets") or {}).get(sheet) or {}).get("rows")) or {}


def without(data: dict, sheet: str) -> dict:
	"""A workbook's content without one sheet and what it keeps per sheet:
	a table workbook's other sheets, as its template keeps them. Pure."""
	held = dict(data.get("sheet") or {})
	held["sheets"] = {name: one for name, one in (held.get("sheets") or {}).items() if name != sheet}
	if held.get("current") not in held["sheets"]:
		held["current"] = next(iter(held["sheets"]), None)
	out = {key: ({name: one for name, one in part.items() if name != sheet} if isinstance(part, dict) else part) for key, part in data.items()}
	out["sheet"] = held
	return out


def placed(data: dict, sheet: str, layout: dict, look: dict | None = None) -> dict:
	"""A workbook's content with the bound sheet drawn in, first; the other
	sheets, and the bound sheet's column widths, are kept. `look`
	(style.table) formats the bound sheet the first time only, so what
	somebody formatted since stays. Pure."""
	held = data.get("sheet")
	if not isinstance(held, dict) or held.get("v") != 2:
		held = {"v": 2, "current": sheet, "sheets": {}}
	others = {name: one for name, one in (held.get("sheets") or {}).items() if name != sheet}
	held["sheets"] = {sheet: {"rows": layout["rows"]}, **others}
	if held.get("current") not in held["sheets"]:
		held["current"] = sheet
	data["sheet"] = held
	for key in ("validation", "protection", "view"):
		part = data.get(key)
		if not isinstance(part, dict) or (key == "view" and "colW" in part):
			part = {}
		was = part.get(sheet) if key == "view" and isinstance(part.get(sheet), dict) else {}
		first = {"colW": look["colW"], "rowH": look["rowH"]} if look and key == "view" else {}
		part[sheet] = {**first, **was, **layout[key]}
		data[key] = part
	if look:
		formats = data.get("formats") if isinstance(data.get("formats"), dict) else {}
		if not formats.get(sheet):
			formats[sheet] = look["formats"]
		data["formats"] = formats
	return data


def _look(doc, cols: list[dict]) -> dict:
	"""How a record's table sheet is formatted: style.table with the
	company's colour and the record's currency."""
	from onedesk.one_sheet import style

	brand = style.brand()
	return style.table(cols, brand["colour"], doc.get("currency") or brand["currency"], style.precisions())


def read(sent: list, cols: list[dict], faults: list | None = None) -> tuple[dict, list[dict], list[str]]:
	"""The sheet's lines as the table's rows, each column found by its header
	wherever it has moved: (where each column is, the rows, what is wrong).
	`faults`, when given, gets each wrong cell and why. Pure."""
	header = [str(one if one is not None else "").strip() for one in (sent[0] if sent else [])]
	at = {}
	for n, text in enumerate(header):
		if text.startswith(MARK) and "name" not in at:
			at["name"] = n
	if "name" not in at:
		return at, [], [_("The sheet's hidden first column was deleted. Undo the change, or reopen the workbook from the record.")]
	for col in cols[1:]:
		if col["header"] in header:
			at[col["fieldname"]] = header.index(col["header"])
		elif not col["read_only"]:
			return at, [], [_("Column {0} was removed from the sheet. Undo the change, or reopen the workbook from the record.").format(col["header"])]
	editable = [col for col in cols[1:] if not col["read_only"]]
	rows, wrong = [], []
	for line, values in enumerate(sent[1:], 2):

		def cell(field, values=values):
			where = at.get(field)
			held = values[where] if where is not None and where < len(values) else None
			return str(held if held is not None else "").strip()

		if not any(cell(col["fieldname"]) not in ("", "FALSE") for col in editable):
			continue
		row = {"name": cell("name") or None, "line": line, "values": {}}
		for col in editable:
			value, why = taken(cell(col["fieldname"]), col)
			if why:
				wrong.append(_("Row {0}: {1}").format(line, why))
				if faults is not None:
					faults.append({"cell": f"{letters(at[col['fieldname']])}{line}", "message": why})
			else:
				row["values"][col["fieldname"]] = value
		rows.append(row)
	return at, rows, wrong


def back(sent: list, at: dict, rows: list[dict], table: list, cols: list[dict], mark: str) -> dict:
	"""The cells the sheet takes back after the record saved: the new mark,
	the ids of rows it added, what the record worked out, and what it filled
	in where the sheet was empty. Pure."""

	def had(line, field):
		values = sent[line - 1] if line - 1 < len(sent) else []
		where = at.get(field)
		held = values[where] if where is not None and where < len(values) else None
		return str(held if held is not None else "").strip()

	out = {}
	if had(1, "name") != MARK + mark:
		out[f"{letters(at['name'])}1"] = MARK + mark
	for row, child in zip(rows, table, strict=False):
		if had(row["line"], "name") != child.get("name"):
			out[f"{letters(at['name'])}{row['line']}"] = child.get("name")
		for col in cols[1:]:
			if col["fieldname"] not in at:
				continue
			now, before = shown(child.get(col["fieldname"]), col["fieldtype"]), had(row["line"], col["fieldname"])
			if now != before and (col["read_only"] or not before):
				out[f"{letters(at[col['fieldname']])}{row['line']}"] = now
	return out


def _held(book) -> dict:
	return frappe.db.get_value(
		api.WORKBOOK,
		book,
		["name", "bound_doctype", "bound_name", "bound_field", "bound_sheet", "bound_columns", "sheets_data"],
		as_dict=True,
	)


@frappe.whitelist(methods=["POST"])
def open_table(doctype: str, name: str, field: str) -> str:
	"""The workbook a record's table is the first sheet of, made the first
	time it is asked for. Answers its name."""
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	df = doc.meta.get_field(field)
	if not df or df.fieldtype != "Table":
		frappe.throw(_("This record has no such table."))
	held = frappe.db.get_value(api.WORKBOOK, {"bound_doctype": doctype, "bound_name": name, "bound_field": field}, "name")
	if held and frappe.db.get_value(api.WORKBOOK, held, "file"):
		refresh(held)
		return held
	from frappe.model.utils.user_settings import get_user_settings

	sheet = _(df.label or field)[:31]
	grid = (json.loads(get_user_settings(doctype) or "{}").get("GridView") or {}).get(df.options) or []
	cols = columns(
		[one.as_dict() for one in frappe.get_meta(df.options).fields],
		[one.get("fieldname") for one in grid if isinstance(one, dict)],
	)
	if len(cols) < 2:
		frappe.throw(_("This table has no columns that can be shown in a sheet."))
	table = doc.get(field)
	data = placed({}, sheet, laid(cols, table, fingerprint(doc.docstatus, table, cols), doc.docstatus != 0), _look(doc, cols))
	title = api._titled(f"{doc.name} {_(df.label or field)}")
	book = frappe.get_doc(
		{
			"doctype": api.WORKBOOK,
			"title": title,
			"sheets_data": storage.encode_sheets_data(json.dumps(data, default=str)),
			"bound_doctype": doctype,
			"bound_name": name,
			"bound_field": field,
			"bound_sheet": sheet,
			"bound_columns": json.dumps(cols),
		}
	)
	book.flags.ignore_permissions = True
	book.insert()
	frappe.cache.delete_value(BOUND_KEY)
	file = frappe.get_doc(
		{
			"doctype": "File",
			"file_url": api.URL + book.name,
			"is_private": 1,
			"attached_to_doctype": doctype,
			"attached_to_name": name,
			"file_name": title,
		}
	)
	file.flags.ignore_permissions = True
	file.insert()
	book.db_set("file", file.name)
	return book.name


def refresh(name: str) -> None:
	"""Before a bound workbook opens: when the record's table changed since
	the sheet last matched it, the bound sheet is drawn again from the table,
	keeping the formulas typed in it. The other sheets are kept as they are."""
	book = _held(name)
	if not book or not book.bound_doctype or not frappe.db.exists(book.bound_doctype, book.bound_name):
		return
	doc = frappe.get_doc(book.bound_doctype, book.bound_name)
	cols = json.loads(book.bound_columns or "[]")
	table = doc.get(book.bound_field) or []
	mark = fingerprint(doc.docstatus, table, cols)
	data = json.loads(storage.decode_sheets_data(book.sheets_data) or "{}")
	lines = stored(data, book.bound_sheet)
	if MARK + mark in (lines.get("0") or []):
		return
	data = placed(data, book.bound_sheet, laid(cols, table, mark, doc.docstatus != 0, kept(lines, cols)), _look(doc, cols))
	frappe.db.set_value(api.WORKBOOK, name, "sheets_data", storage.encode_sheets_data(json.dumps(data, default=str)), update_modified=False)


def changed(doc, method=None) -> None:
	"""doc_events: a record saved on its form tells the workbooks its table
	is open in, which draw the table again in place. Its save from a
	workbook tells nobody: that workbook already has it."""
	if doc.flags.from_workbook or doc.doctype not in _bound_doctypes():
		return
	for book in frappe.get_all(api.WORKBOOK, filters={"bound_doctype": doc.doctype, "bound_name": doc.name}, pluck="name"):
		frappe.publish_realtime("one_table_changed", {"workbook": book}, doctype=doc.doctype, docname=doc.name, after_commit=True)


def _bound_doctypes() -> set:
	held = frappe.cache.get_value(BOUND_KEY)
	if held is None:
		held = frappe.get_all(api.WORKBOOK, filters={"bound_doctype": ["is", "set"]}, distinct=True, pluck="bound_doctype")
		frappe.cache.set_value(BOUND_KEY, held)
	return set(held)


@frappe.whitelist(methods=["POST"])
def redrawn(name: str) -> dict:
	"""The bound sheet drawn again from the record, as cells, for a workbook
	that is open when the record changed on its form."""
	api._may(name, "read")
	refresh(name)
	book = _held(name)
	if not book or not book.bound_doctype:
		return {"sheet": None, "cells": {}, "record": {}}
	data = json.loads(storage.decode_sheets_data(book.sheets_data) or "{}")
	cells = {
		f"{letters(col)}{int(line) + 1}": value
		for line, values in stored(data, book.bound_sheet).items()
		for col, value in enumerate(values or [])
		if value not in (None, "")
	}
	return {"sheet": book.bound_sheet, "cells": cells, "record": record_of(name)}


def record_of(name: str) -> dict:
	"""The record a table's workbook belongs to, as RECORD() reads it; empty
	for any other workbook or a reader who may not see the record."""
	from onedesk.one_sheet import style

	book = frappe.db.get_value(api.WORKBOOK, name, ["bound_doctype", "bound_name"], as_dict=True)
	if not book or not book.bound_doctype or not frappe.db.exists(book.bound_doctype, book.bound_name):
		return {}
	doc = frappe.get_doc(book.bound_doctype, book.bound_name)
	if not doc.has_permission("read"):
		return {}
	return style.record(doc)


def bound(name: str) -> dict | None:
	"""What get_sheet tells the editor about the record behind it: the
	sheet, the record and the table's label."""
	book = frappe.db.get_value(api.WORKBOOK, name, ["bound_doctype", "bound_name", "bound_field", "bound_sheet"], as_dict=True)
	if not book or not book.bound_doctype:
		return None
	df = frappe.get_meta(book.bound_doctype).get_field(book.bound_field)
	label = _(df.label) if df and df.label else book.bound_field
	return {"sheet": book.bound_sheet, "doctype": book.bound_doctype, "name": book.bound_name, "field": book.bound_field, "label": label}


def apply(name: str, sent: str) -> dict:
	"""save_sheet with the bound sheet's values: the table becomes the sheet
	through the record's own save. Answers the cells the sheet takes back, or
	why the record refused."""
	book = _held(name)
	said = frappe.parse_json(sent) if sent else {}
	if not book or not book.bound_doctype or not isinstance(said, dict) or said.get("sheet") != book.bound_sheet:
		return {"ok": True, "cells": {}}
	cols = json.loads(book.bound_columns or "[]")
	doc = frappe.get_doc(book.bound_doctype, book.bound_name)
	table = doc.get(book.bound_field) or []
	lines = said.get("rows") if isinstance(said.get("rows"), list) else []
	mark = fingerprint(doc.docstatus, table, cols)
	if not any(str(one or "") == MARK + mark for one in (lines[0] if lines else [])):
		return {
			"ok": False,
			"message": _("{0} was changed on the record after this sheet was last updated. Reopen the workbook from the record to load the changes.").format(
				book.bound_sheet
			),
		}
	if doc.docstatus != 0:
		return {"ok": True, "cells": {}}
	faults = []
	at, rows, wrong = read(lines, cols, faults)
	if wrong:
		said = wrong[0] if len(wrong) == 1 else _("{0} (and {1} more)").format(wrong[0], len(wrong) - 1)
		return {"ok": False, "message": said, "faults": faults}
	if len(rows) > MOST_ROWS:
		return {"ok": False, "message": _("A table can take at most {0} rows from a workbook.").format(MOST_ROWS)}
	links = _links(cols, doc.meta.get_field(book.bound_field).options)
	gone = missing(links, rows)
	if gone:
		return {"ok": False, "message": _gone(gone), "missing": gone, "faults": unknown(links, gone, rows, at)}
	if _changed(table, rows):
		_put(doc, book.bound_field, table, rows)
		doc.flags.from_workbook = True
		frappe.db.savepoint(SAVEPOINT)
		try:
			doc.save()
		except (frappe.ValidationError, frappe.PermissionError) as error:
			said = lined(_refusal(error), rows)
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.clear_messages()
			return {"ok": False, "message": said or _("The record rejected this table."), "faults": pinned(said, rows, cols, at)}
		except Exception:
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.clear_messages()
			frappe.log_error(f"Workbook {name} into {doc.doctype} {doc.name}")
			return {"ok": False, "message": _("The record rejected this table. See the Error Log for details.")}
		table = doc.get(book.bound_field)
		mark = fingerprint(doc.docstatus, table, cols)
	return {"ok": True, "cells": back(lines, at, rows, table, cols, mark)}


def _links(cols: list[dict], child: str) -> dict:
	"""The table's link columns and the record type each names."""
	meta = frappe.get_meta(child)
	out = {}
	for col in cols[1:]:
		df = meta.get_field(col["fieldname"])
		if df and df.fieldtype == "Link" and df.options and not col["read_only"]:
			out[col["fieldname"]] = df.options
	return out


def missing(links: dict, rows: list[dict]) -> dict:
	"""The names the rows give in link columns that aren't records yet, by
	record type."""
	wanted = {}
	for row in rows:
		for field, doctype in links.items():
			value = row["values"].get(field)
			if value:
				wanted.setdefault(doctype, set()).add(str(value))
	out = {}
	for doctype, values in wanted.items():
		held = set(frappe.get_all(doctype, filters={"name": ["in", list(values)]}, pluck="name"))
		gone = sorted(value for value in values if value not in held)
		if gone:
			out[doctype] = gone
	return out


def unknown(links: dict, gone: dict, rows: list[dict], at: dict) -> list[dict]:
	"""Each cell naming a record that isn't there, why, and what would make
	it. Pure."""
	out = []
	for row in rows:
		for field, doctype in links.items():
			value = row["values"].get(field)
			if value and str(value) in gone.get(doctype, ()) and field in at:
				out.append(
					{
						"cell": f"{letters(at[field])}{row['line']}",
						"message": _("{0} {1} not found.").format(_(doctype), value),
						"doctype": doctype,
						"value": str(value),
					}
				)
	return out


def _gone(gone: dict) -> str:
	said = [_("{0} not found: {1}").format(_(doctype), ", ".join(values[:5]) + (" …" if len(values) > 5 else "")) for doctype, values in gone.items()]
	return "; ".join(said)


@frappe.whitelist(methods=["POST"])
def make_missing(name: str, doctype: str, values: str | list) -> dict:
	"""Make the records a table sheet names that aren't there yet, each from
	its name alone, as a new record of that type would start. Answers the
	ones made and why each of the others wasn't."""
	api._may(name, "write")
	book = _held(name)
	child = book and book.bound_doctype and frappe.get_meta(book.bound_doctype).get_field(book.bound_field)
	if not child or doctype not in _links(json.loads(book.bound_columns or "[]"), child.options).values():
		frappe.throw(_("This table does not link to records of that type."))
	frappe.has_permission(doctype, "create", throw=True)
	values = frappe.parse_json(values) if isinstance(values, str) else values
	made, failed = [], {}
	for value in [str(one).strip() for one in values or [] if str(one).strip()][:MOST_ROWS]:
		if frappe.db.exists(doctype, value):
			made.append(value)
			continue
		frappe.db.savepoint(SAVEPOINT)
		try:
			made.append(_made(doctype, value))
		except Exception as error:
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.clear_messages()
			failed[value] = strip_html(str(error)) or _("Could not create the record.")
	return {"made": made, "failed": failed}


def _made(doctype: str, value: str) -> str:
	"""A record of `doctype` called `value`: its name, and its title, set
	from it."""
	meta = frappe.get_meta(doctype)
	doc = frappe.new_doc(doctype)
	named = (meta.autoname or "").removeprefix("field:") if (meta.autoname or "").startswith("field:") else None
	for field in {named, meta.title_field, "item_code" if doctype == "Item" else None, "item_name" if doctype == "Item" else None} - {None}:
		if meta.get_field(field):
			doc.set(field, value)
	for df in meta.fields:
		if df.reqd and df.fieldtype == "Link" and df.options and not doc.get(df.fieldname):
			doc.set(df.fieldname, _default(df.options, df.fieldname))
	if not named:
		doc.name = value
		doc.flags.name_set = True
	doc.insert()
	return doc.name


def _default(doctype: str, field: str) -> str | None:
	"""What a required link starts as on a record made from its name: the
	user's default for the field, the top of a tree, or the only one."""
	said = frappe.defaults.get_user_default(field)
	if said:
		return said
	if frappe.get_meta(doctype).is_tree:
		from frappe.utils.nestedset import get_root_of

		return get_root_of(doctype)
	only = frappe.get_all(doctype, pluck="name", limit=2)
	return only[0] if len(only) == 1 else None


def _refusal(error) -> str:
	"""What the record said. A missing required field raises with field
	names only; the words it showed are in the message log."""
	if isinstance(error, frappe.MandatoryError):
		told = [strip_html(one.get("message") or "") for one in frappe.get_message_log() if isinstance(one, dict)]
		if any(told):
			return "; ".join(one for one in told if one)
	return strip_html(str(error))


def _differs(child, field: str, value) -> bool:
	held = child.get(field)
	if isinstance(value, float | int) and not isinstance(value, bool):
		precision = child.precision(field)
		return flt(value, precision) != flt(held, precision)
	kind = child.meta.get_field(field).fieldtype if child.meta.get_field(field) else None
	if kind in LONG:
		return shown(held, kind) != shown(value, kind)
	return str(held if held is not None else "") != str(value if value is not None else "")


def _changed(table: list, rows: list[dict]) -> bool:
	if [row["name"] for row in rows] != [child.name for child in table]:
		return True
	by = {child.name: child for child in table}
	return any(_differs(by[row["name"]], field, value) for row in rows for field, value in row["values"].items())


def _put(doc, field: str, table: list, rows: list[dict]) -> None:
	"""The table rebuilt in the sheet's order: a row the sheet names keeps
	every field the sheet doesn't show; a row it doesn't name is gone."""
	by = {child.name: child for child in table}
	doc.set(field, [])
	for row in rows:
		child = by.pop(row["name"], None) if row["name"] else None
		if child is None:
			doc.append(field, row["values"])
			continue
		for key, value in row["values"].items():
			if _differs(child, key, value):
				child.set(key, value)
		doc.append(field, child)
	for at, child in enumerate(doc.get(field), 1):
		child.idx = at
