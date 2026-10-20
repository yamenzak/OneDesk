"""A record's table as the first sheet of a workbook. The table's button on
the form opens it, made the first time; what is typed in that sheet becomes
the table through the record's own save, so every rule the record has
applies. README, table.py.
"""

import hashlib
import json
import re
from datetime import date, datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import flt, strip_html

from onedesk.one_sheet import api, storage
from onedesk.one_sheet.assist import letters

NUMBER = ("Int", "Float", "Currency", "Percent", "Rating")
TEXT = ("Data", "Small Text", "Text", "Long Text", "Link", "Dynamic Link", "Read Only", "Phone", "Autocomplete")
SHOWN = (*NUMBER, *TEXT, "Select", "Check", "Date", "Datetime", "Time")

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


def columns(fields: list[dict], picked: list[str] | None = None) -> list[dict]:
	"""The hidden row id, then the table's columns as the form's grid shows
	them: the ones chosen on the grid's gear when there are any (`picked`),
	else the fields in its list view; and the required ones either way. Pure."""
	usable = [df for df in fields if df.get("fieldtype") in SHOWN and not df.get("hidden")]
	if picked:
		by = {df["fieldname"]: df for df in usable}
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
		return None, _("{0} is TRUE or FALSE.").format(column["header"])
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


def fingerprint(docstatus: int, rows: list, cols: list[dict]) -> str:
	"""What the table holds, short: the sheet carries the one it last matched. Pure."""
	held = [int(docstatus or 0)]
	held += [[row.get("name")] + [shown(row.get(col["fieldname"]), col["fieldtype"]) for col in cols[1:]] for row in rows]
	return hashlib.sha1(json.dumps(held, default=str).encode("utf-8")).hexdigest()[:16]


def _rule(col: dict) -> dict | None:
	if col["fieldtype"] == "Select" and col.get("options"):
		return {"type": "list", "options": col["options"], "message": _("Choose one from the list.")}
	if col["fieldtype"] == "Check":
		return {"type": "checkbox", "message": _("TRUE or FALSE.")}
	if col["fieldtype"] in NUMBER:
		return {"type": "number", "operator": "between", "min": None, "max": None, "message": _("A number.")}
	return None


def laid(cols: list[dict], rows: list, mark: str, locked: bool) -> dict:
	"""The bound sheet as the editor keeps it: the header, a line a row, the
	dropdowns and number rules, the header, row id and worked-out columns
	locked, and the row id hidden. Pure."""
	cells = {"0": [MARK + mark] + [col["header"] for col in cols[1:]]}
	for at, row in enumerate(rows, 1):
		cells[str(at)] = [row.get("name")] + [shown(row.get(col["fieldname"]), col["fieldtype"]) or None for col in cols[1:]]
	rules = {}
	for at, col in enumerate(cols):
		rule = None if not at or col["read_only"] else _rule(col)
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


def placed(data: dict, sheet: str, layout: dict) -> dict:
	"""A workbook's content with the bound sheet drawn in, first; the other
	sheets, and the bound sheet's column widths, are kept. Pure."""
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
		part[sheet] = {**was, **layout[key]}
		data[key] = part
	return data


def read(sent: list, cols: list[dict]) -> tuple[dict, list[dict], list[str]]:
	"""The sheet's lines as the table's rows, each column found by its header
	wherever it has moved: (where each column is, the rows, what is wrong). Pure."""
	header = [str(one if one is not None else "").strip() for one in (sent[0] if sent else [])]
	at = {}
	for n, text in enumerate(header):
		if text.startswith(MARK) and "name" not in at:
			at["name"] = n
	if "name" not in at:
		return at, [], [_("The sheet's hidden first column is gone. Undo, or open the workbook again from the record.")]
	for col in cols[1:]:
		if col["header"] in header:
			at[col["fieldname"]] = header.index(col["header"])
		elif not col["read_only"]:
			return at, [], [_("The column {0} isn't in the sheet any more. Undo, or open the workbook again from the record.").format(col["header"])]
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
		frappe.throw(_("That isn't a table on this record."))
	held = frappe.db.get_value(api.WORKBOOK, {"bound_doctype": doctype, "bound_name": name, "bound_field": field}, "name")
	if held and frappe.db.get_value(api.WORKBOOK, held, "file"):
		refresh(held)
		return held
	from frappe.model.utils.user_settings import get_user_settings

	grid = (json.loads(get_user_settings(doctype) or "{}").get("GridView") or {}).get(df.options) or []
	cols = columns([one.as_dict() for one in frappe.get_meta(df.options).fields], [one.get("fieldname") for one in grid if isinstance(one, dict)])
	if len(cols) < 2:
		frappe.throw(_("This table has no columns a sheet can hold."))
	sheet = _(df.label or field)[:31]
	data = placed({}, sheet, laid(cols, doc.get(field), fingerprint(doc.docstatus, doc.get(field), cols), doc.docstatus != 0))
	title = api._titled(f"{doc.name} {sheet}")
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
	the sheet last matched it, the bound sheet is drawn again from the table.
	The other sheets are kept as they are."""
	book = _held(name)
	if not book or not book.bound_doctype or not frappe.db.exists(book.bound_doctype, book.bound_name):
		return
	doc = frappe.get_doc(book.bound_doctype, book.bound_name)
	cols = json.loads(book.bound_columns or "[]")
	table = doc.get(book.bound_field) or []
	mark = fingerprint(doc.docstatus, table, cols)
	data = json.loads(storage.decode_sheets_data(book.sheets_data) or "{}")
	stored = ((((data.get("sheet") or {}).get("sheets") or {}).get(book.bound_sheet) or {}).get("rows") or {}).get("0") or []
	if MARK + mark in stored:
		return
	data = placed(data, book.bound_sheet, laid(cols, table, mark, doc.docstatus != 0))
	frappe.db.set_value(api.WORKBOOK, name, "sheets_data", storage.encode_sheets_data(json.dumps(data, default=str)), update_modified=False)


def bound(name: str) -> dict | None:
	"""What get_sheet tells the editor about the record behind it."""
	book = frappe.db.get_value(api.WORKBOOK, name, ["bound_doctype", "bound_name", "bound_sheet"], as_dict=True)
	if not book or not book.bound_doctype:
		return None
	return {"sheet": book.bound_sheet, "doctype": book.bound_doctype, "name": book.bound_name}


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
			"message": _("{0} changed on the record since this sheet last matched it. Open the workbook again from the record to bring it in.").format(
				book.bound_sheet
			),
		}
	if doc.docstatus != 0:
		return {"ok": True, "cells": {}}
	at, rows, wrong = read(lines, cols)
	if wrong:
		return {"ok": False, "message": wrong[0] if len(wrong) == 1 else _("{0} (and {1} more)").format(wrong[0], len(wrong) - 1)}
	if len(rows) > MOST_ROWS:
		return {"ok": False, "message": _("A table takes at most {0} rows from a workbook.").format(MOST_ROWS)}
	if _changed(table, rows):
		_put(doc, book.bound_field, table, rows)
		frappe.db.savepoint(SAVEPOINT)
		try:
			doc.save()
		except (frappe.ValidationError, frappe.PermissionError) as error:
			said = _refusal(error)
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.clear_messages()
			return {"ok": False, "message": lined(said, rows) or _("The record didn't take this table.")}
		except Exception:
			frappe.db.rollback(save_point=SAVEPOINT)
			frappe.clear_messages()
			frappe.log_error(f"Workbook {name} into {doc.doctype} {doc.name}")
			return {"ok": False, "message": _("The record didn't take this table. The error is in the error log.")}
		table = doc.get(book.bound_field)
		mark = fingerprint(doc.docstatus, table, cols)
	return {"ok": True, "cells": back(lines, at, rows, table, cols, mark)}


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
