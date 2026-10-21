"""OneWorkbook's pure parts: how a workbook's File names it, how the history
thins, and what Ask shows the model and keeps of its answer."""

import ast
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SHEET = tree.APP / "one_sheet"


def _named(target) -> set:
	return {one.id for one in getattr(target, "elts", [target]) if isinstance(one, ast.Name)}


def _lifted(where: Path, names: tuple, room: dict) -> dict:
	body = ast.parse(where.read_text(encoding="utf-8"))
	kept = [
		node
		for node in body.body
		if (isinstance(node, ast.FunctionDef) and node.name in names)
		or (isinstance(node, ast.Assign) and any(_named(t) & set(names) for t in node.targets))
	]
	exec(compile(ast.Module(body=kept, type_ignores=[]), str(where), "exec"), room)
	return room


def test_a_workbook_file_names_its_workbook():
	from urllib.parse import parse_qs, urlparse

	room = _lifted(SHEET / "api.py", ("URL", "workbook_of"), {"parse_qs": parse_qs, "urlparse": urlparse})
	assert room["workbook_of"](room["URL"] + "abc123") == "abc123"
	assert room["workbook_of"]("/api/method/onedesk.one_storage.store.fetch?key=x") is None
	assert room["workbook_of"](None) is None


def test_unnamed_versions_thin_as_they_age():
	room = _lifted(SHEET / "versions.py", ("THINNED", "thinned"), {"timedelta": timedelta})
	now = datetime(2026, 10, 20, 12, 0)
	rows = [
		{"name": "fresh-1", "creation": now - timedelta(hours=1)},
		{"name": "fresh-2", "creation": now - timedelta(hours=2)},
		{"name": "week-a", "creation": now - timedelta(days=3, minutes=10)},
		{"name": "week-b", "creation": now - timedelta(days=3, minutes=20)},
		{"name": "old", "creation": now - timedelta(days=200)},
	]
	gone = room["thinned"](rows, now)
	assert set(gone) == {"week-b", "old"}, "the newest of each hour stays; nothing past three months"


def test_cells_are_named_and_read_as_the_sheet_holds_them():
	import re

	room = _lifted(SHEET / "cells.py", ("CELL", "letters", "cells_of"), {"re": re})
	assert [room["letters"](n) for n in (0, 25, 26, 701)] == ["A", "Z", "AA", "ZZ"]
	data = {"sheet": {"v": 2, "sheets": {"Sheet1": {"rows": {"0": ["Item", "Qty"], "1": ["Glass", "4", ""]}}}}}
	assert room["cells_of"](data, "Sheet1") == {(0, 0): "Item", (0, 1): "Qty", (1, 0): "Glass", (1, 1): "4"}
	assert room["CELL"].match("B12") and not room["CELL"].match("B0")


def test_the_relay_names_the_room_and_keeps_readers_from_writing():
	relay = (tree.ROOT / "realtime" / "handlers.js").read_text(encoding="utf-8")
	assert "onedesk.one_sheet.live.admit" in relay
	assert "const room = roomName(kind, message.name)" in relay, "the server names the room"
	assert "seat.write || READERS_MAY.has(event)" in relay
	assert '"yjs_update"' not in relay.split("READERS_MAY = new Set(")[1].split(")")[0], "a reader may not change cells"
	assert "socket.to(room).emit" in relay, "a change is not echoed to its sender"
	assert '"type": "commonjs"' in (tree.ROOT / "realtime" / "package.json").read_text(encoding="utf-8")


def test_a_table_sheet_reads_back_as_the_table():
	import hashlib
	import json
	import re
	from datetime import date, datetime, time, timedelta

	room = {"_": lambda text: text, "hashlib": hashlib, "json": json, "re": re, "date": date, "datetime": datetime, "time": time, "timedelta": timedelta}
	_lifted(SHEET / "cells.py", ("letters",), room)
	import html

	room["html"] = html
	names = ("NUMBER", "TEXT", "LONG", "SHOWN", "MOST_COLUMNS", "MOST_ROWS", "SPARE", "LOCKED_TO", "MARK", "YES", "NO", "EPOCH")
	_lifted(SHEET / "table.py", (*names, "columns", "shown", "taken", "lined", "fingerprint", "_rule", "kept", "laid", "stored", "without", "placed", "read", "back", "unknown", "pinned"), room)
	fields = [
		{"fieldname": "item_code", "label": "Item", "fieldtype": "Link", "in_list_view": 1, "reqd": 1},
		{"fieldname": "notes", "label": "Notes", "fieldtype": "Text Editor", "in_list_view": 1},
		{"fieldname": "kind", "label": "Kind", "fieldtype": "Select", "options": "\nSupply\nFit", "in_list_view": 1},
		{"fieldname": "qty", "label": "Qty", "fieldtype": "Float", "in_list_view": 1},
		{"fieldname": "amount", "label": "Amount", "fieldtype": "Currency", "in_list_view": 1, "read_only": 1},
		{"fieldname": "secret", "label": "Secret", "fieldtype": "Data", "hidden": 1, "reqd": 1},
	]
	cols = room["columns"](fields)
	assert [col["fieldname"] for col in cols] == ["name", "item_code", "kind", "qty", "amount"], "no editor fields, nothing hidden"
	assert cols[2]["options"] == ["Supply", "Fit"] and cols[4]["read_only"]
	fields.append({"fieldname": "free", "label": "Free", "fieldtype": "Check"})
	picked = room["columns"](fields, ["free", "qty", "notes"])
	assert [col["fieldname"] for col in picked] == ["name", "free", "qty", "notes", "item_code"], "the grid's gear decides, formatted text too, and required stays"

	assert room["shown"](420.0, "Float") == "420" and room["shown"](6.75, "Currency") == "6.75" and room["shown"](0, "Check") == "FALSE"
	assert room["taken"]("1,260", cols[3]) == (1260.0, None)
	assert room["taken"]("lots", cols[3])[1] == "Qty must be a number."
	assert room["taken"]("Paint", cols[2])[1] == "Kind must be one of: Supply, Fit."
	assert room["taken"]("46000", {"fieldtype": "Date", "header": "On"}) == (date(2025, 12, 9), None), "a date the grid worked out as a number"
	assert room["taken"]("2026-10-21 09:30", {"fieldtype": "Datetime", "header": "At"}) == (datetime(2026, 10, 21, 9, 30), None)
	assert room["taken"]("half nine", {"fieldtype": "Time", "header": "At"})[1] == "At must be a time, such as 09:30."
	assert room["lined"]("Row #2: Quantity can't be zero. Row #12 too.", [{"line": 2}, {"line": 4}]) == "Row 4: Quantity can't be zero. Row #12 too."
	assert room["lined"]("Row 1: Quantity (12.5) cannot be a fraction.", [{"line": 2}]) == "Row 2: Quantity (12.5) cannot be a fraction."

	table = [{"name": "r1", "item_code": "GL", "kind": "Supply", "qty": 6, "amount": 600}]
	mark = room["fingerprint"](0, table, cols)
	layout = room["laid"](cols, table, mark, False)
	assert layout["rows"]["0"][0] == "#" + mark and layout["rows"]["1"] == ["r1", "GL", "Supply", "6", "600"]
	assert layout["validation"]["C2"]["type"] == "list" and "E2" not in layout["validation"], "no rule on a worked-out column"
	assert {(one["c0"], one["c1"]) for one in layout["protection"]["ranges"]} == {(0, 4), (0, 0), (4, 4)}
	kept = room["placed"]({"sheet": {"v": 2, "current": "Notes", "sheets": {"Notes": {"rows": {}}}}, "view": {"Items": {"colW": {"1": 180}}}}, "Items", layout)
	assert list(kept["sheet"]["sheets"]) == ["Items", "Notes"] and kept["view"]["Items"]["colW"] == {"1": 180}

	moved = [["Notes to self", "Qty", "#" + mark, "Item", "Kind", "Amount"], ["", "8", "r1", "GL", "Supply", "600"], ["", "2", "", "GL", "", ""], ["", "", "", "", "", ""]]
	at, rows, wrong = room["read"](moved, cols)
	assert not wrong and at["name"] == 2 and at["qty"] == 1, "columns are found by their headers wherever they moved"
	assert [(row["name"], row["values"]["qty"]) for row in rows] == [("r1", 8.0), (None, 2.0)], "the empty line is skipped"
	after = [{"name": "r1", "item_code": "GL", "kind": "Supply", "qty": 8, "amount": 800}, {"name": "r2", "item_code": "GL", "kind": "Fit", "qty": 2, "amount": 200}]
	cells = room["back"](moved, at, rows, after, cols, "new")
	assert cells == {"C1": "#new", "F2": "800", "C3": "r2", "E3": "Fit", "F3": "200"}, cells
	assert room["read"]([["#" + mark, "Item"]], cols)[2][0].startswith("Column Kind was removed"), "a column gone is refused"
	faults = []
	room["read"]([moved[0], ["", "lots", "r1", "GL", "Supply", "600"]], cols, faults)
	assert faults and faults[0]["cell"] == "B2", "a wrong cell is said where it is"
	said = room["unknown"]({"item_code": "Item"}, {"Item": ["GL"]}, rows, at)
	assert [(one["cell"], one["doctype"], one["value"]) for one in said] == [("D2", "Item", "GL"), ("D3", "Item", "GL")], said
	assert room["pinned"]("Row 3: Qty for Item GL cannot be zero", rows, cols, at) == [{"cell": "B3", "message": "Row 3: Qty for Item GL cannot be zero"}]
	assert room["pinned"]("Row 9: gone", rows, cols, at) == [] and room["pinned"]("Nothing about a row", rows, cols, at) == []


def test_a_table_sheet_keeps_its_formulas():
	import html
	import re

	room = {"_": lambda text: text, "re": re, "html": html}
	_lifted(SHEET / "cells.py", ("letters",), room)
	names = ("NUMBER", "TEXT", "LONG", "SHOWN", "MOST_COLUMNS", "MARK", "SPARE", "LOCKED_TO")
	_lifted(SHEET / "table.py", (*names, "columns", "shown", "_rule", "kept", "laid", "stored", "without"), room)
	fields = [
		{"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "in_list_view": 1},
		{"fieldname": "description", "label": "Description", "fieldtype": "Text Editor"},
		{"fieldname": "qty", "label": "Qty", "fieldtype": "Float", "in_list_view": 1},
		{"fieldname": "rate", "label": "Rate", "fieldtype": "Currency", "in_list_view": 1},
	]
	assert [col["fieldname"] for col in room["columns"](fields)] == ["name", "item_name", "qty", "rate"], "formatted text only when asked for"
	more = [
		{"fieldname": "drawing", "label": "Drawing", "fieldtype": "Attach", "in_list_view": 1},
		{"fieldname": "spec", "label": "Spec", "fieldtype": "Code", "in_list_view": 1},
		{"fieldname": "supplier", "label": "Supplier", "fieldtype": "Link", "options": "Supplier", "in_list_view": 1},
	]
	cols = room["columns"](more, ["drawing", "spec", "supplier"])
	assert [col["fieldname"] for col in cols] == ["name", "drawing", "spec", "supplier"] and cols[3]["link"] == "Supplier"
	assert room["_rule"](cols[3]) == {"type": "link", "doctype": "Supplier"}, "a link column searches its records"
	assert room["shown"]("<b>x</b>", "Code") == "<b>x</b>", "code is kept as it is written"
	cols = room["columns"](fields, ["item_name", "qty", "rate", "description"])
	assert [col["fieldname"] for col in cols] == ["name", "item_name", "qty", "rate", "description"]
	lines = {
		"0": ["#old", "Item Name", "Rate", "Qty", "Description"],
		"1": ["r1", "=Costing!A4:A", "=Costing!P4:P/Costing!C4:C", "6", None],
		"2": ["r2", None, None, "=C2*2", "Glass"],
	}
	formulas = room["kept"](lines, cols)
	assert formulas == {(1, "item_name"): "=Costing!A4:A", (1, "rate"): "=Costing!P4:P/Costing!C4:C", (2, "qty"): "=C2*2"}, "found by header"
	table = [{"name": "r1", "item_name": "Wall", "qty": 6, "rate": 9}, {"name": "r2", "item_name": "Door", "qty": 3, "rate": 4}]
	layout = room["laid"](cols, table, "new", False, formulas)
	assert layout["rows"]["1"] == ["r1", "=Costing!A4:A", "6", "=Costing!P4:P/Costing!C4:C", None]
	assert layout["rows"]["2"] == ["r2", None, "=C2*2", None, None], "a formula's column isn't written under, a lone formula replaces its cell"
	assert "D2" not in layout["validation"] and layout["validation"]["C2"]["type"] == "number", "no rule under a formula that fills its column"
	data = {
		"sheet": {"v": 2, "current": "Items", "sheets": {"Items": {"rows": lines}, "Costing": {"rows": {"3": ["CW01"]}}}},
		"view": {"Items": {"hiddenCols": [0]}},
		"protection": {"Items": {"locked": False}},
		"validation": {"Items": {"C2": {}}},
	}
	kept = room["without"](data, "Items")
	assert list(kept["sheet"]["sheets"]) == ["Costing"] and kept["sheet"]["current"] == "Costing", "a template keeps the other sheets, not the table"
	assert room["stored"](kept, "Costing") == {"3": ["CW01"]} and kept["view"] == {} and kept["protection"] == {} and kept["validation"] == {}
	assert room["shown"]("<p>Aluminum &amp; glass</p>", "Text Editor") == "Aluminum & glass"


def test_a_branded_sheet_is_laid_out_under_the_company():
	from types import SimpleNamespace

	room = {}
	_lifted(SHEET / "cells.py", ("letters",), room)
	heads = _lifted(SHEET.parent / "one" / "letter_heads.py", ("INK", "_rgb", "_luminance", "_contrast", "on"), {})
	_lifted(SHEET / "style.py", ("WORKED", "LINE", "MUTED", "TOTALS", "FIRST", "KINDS", "META", "tint", "header", "number_format", "width", "table", "branded"), room)
	room["frappe"] = None
	room["letter_heads"] = SimpleNamespace(on=heads["on"])
	assert room["tint"]("#000000", 0.1) == "#E6E6E6" and room["tint"]("#FFF", 0.5) == "#FFFFFF"
	head = ["Item", "Description", "Qty", "Width", "Height", "Area", "Rate", "Total"]
	line = {"F": "=D{r}*E{r}/1000000", "H": "=C{r}*G{r}"}
	kinds = {"money": "GH", "count": "C", "size": "DE", "area": "F", "key": "H", "wide": "B"}
	meta = [("Project", '=RECORD("project")', "Project"), ("Name", '=FIELD("Project",{meta0},"project_name")')]
	laid = room["branded"]("Costing", head, line, {"G": "TOTAL", "H": "=SUM(H{first}:H)"}, kinds, "#1F6FEB", "AED", meta)
	rows, looks = laid["rows"], laid["formats"]
	assert rows["0"][0] == '=IMAGE(BRAND("logo"))' and rows["0"][1] == "Costing", "the logo, and what the sheet is for beside it"
	assert laid["merge"]["masterMap"]["A1"] == {"rowSpan": 3, "colSpan": 1, "r": 0, "c": 0} and laid["merge"]["slaveMap"]["A3"] == "A1"
	assert rows["0"][3] == "Project" and rows["0"][4] == '=RECORD("project")' and rows["1"][4] == '=FIELD("Project",E1,"project_name")', "a project picked, its fields read"
	assert laid["validation"] == {"E1": {"type": "link", "doctype": "Project"}}
	assert rows["3"][7] == "=SUM(H6:H)" and looks["rows"]["3"]["borderBottom"]["color"] == "#1F6FEB", "the totals over the header"
	assert rows["4"] == head and looks["rows"]["4"]["backgroundColor"] == "#1F6FEB" and looks["rows"]["4"]["color"] == "#ffffff"
	assert room["header"]("#FDE68A")["color"] == "#111827", "ink on a light colour"
	assert "5" not in rows, "no line laid out before it is used"
	assert laid["lines"] == {"from": 6, "key": "A", "formulas": line}
	assert looks["cols"]["7"] == {"numberFormat": "currency:AED:2;", "backgroundColor": "#E9F1FD", "bold": True}, "the key figure marked"
	assert looks["cols"]["5"] == {"numberFormat": "number:us:3;", "backgroundColor": "#F5F5F4"}, "worked out: grey, a zero is blank"
	assert looks["cols"]["6"] == {"numberFormat": "currency:AED:2"}, "typed: a zero shows"
	assert looks["rows"]["0"]["backgroundColor"] == "#FFFFFF", "the top stays white"
	assert laid["view"]["freezeRows"] == 5 and laid["view"]["freezeCols"] == 1 and laid["view"]["colW"]["1"] == 300
	cols = [{"fieldname": "name", "fieldtype": "Data"}, {"fieldname": "qty", "fieldtype": "Float"}, {"fieldname": "amount", "fieldtype": "Currency", "read_only": True}]
	look = room["table"](cols, "#1F6FEB", "AED", {"Currency": 2, "Float": 3})
	assert room["table"]([cols[0], {**cols[2], "precision": 4}], "#1F6FEB", "AED", {"Currency": 2})["formats"]["cols"]["1"]["numberFormat"] == "currency:AED:4", "a field's own precision first"
	assert look["formats"]["rows"]["0"]["backgroundColor"] == "#1F6FEB"
	assert look["formats"]["cols"]["1"] == {"numberFormat": "number:us:3"}
	assert look["formats"]["cols"]["2"]["numberFormat"] == "currency:AED:2" and look["formats"]["cols"]["2"]["backgroundColor"] == "#F5F5F4"


def test_a_table_cell_is_checked_as_its_field():
	room = _lifted(SHEET / "table.py", ("NUMBER", "_rule"), {"_": lambda text: text})
	rule = room["_rule"]
	assert rule({"fieldtype": "Int"})["whole"] and not rule({"fieldtype": "Float"}).get("whole"), "an Int takes whole numbers"
	assert rule({"fieldtype": "Currency"})["min"] is None, "a negative amount is a number too"
	assert rule({"fieldtype": "Date"})["type"] == "date" and rule({"fieldtype": "Data"}) is None
	columns = _lifted(SHEET / "table.py", ("MARK", "MOST_COLUMNS", "NUMBER", "TEXT", "LONG", "SHOWN", "columns"), {"_": lambda text: text})["columns"]
	cols = columns(
		[{"fieldname": "rate", "fieldtype": "Currency", "label": "Rate", "in_list_view": 1, "precision": "3"}, {"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "in_list_view": 1}]
	)
	assert [col["precision"] for col in cols[1:]] == [3, None], "a field's own precision is kept"


def test_oneai_writes_cells_formats_and_notes_into_the_saved_shape():
	room = _lifted(SHEET / "cells.py", ("CELL", "letters"), {"re": __import__("re")})
	_lifted(SHEET / "ai.py", ("MOST_CELLS", "LOOKS", "_at", "_span", "_cells_given", "written", "noted"), room)
	assert room["_at"]("B12") == (11, 1) and room["_at"]("AA1") == (0, 26) and room["_at"]("12B") is None
	assert room["_span"]("A1:B2") == [(0, 0), (0, 1), (1, 0), (1, 1)] and room["_span"]("nonsense") == []
	given, styled, wrong = room["_cells_given"]({"a1": "Item", "D2": "=B2*C2", "C2": 4}, {"A1:B1": {"bold": True, "colour": "x"}})
	assert not wrong and given == {"A1": "Item", "D2": "=B2*C2", "C2": 4} and styled == {"A1": {"bold": True}, "B1": {"bold": True}}
	assert room["_cells_given"]({"row 3": "x"}, None)[2], "a name that isn't a cell is refused"
	data = room["written"]({}, "Costing", {"A1": "Item", "C2": "=A1"}, {"A1": {"bold": True}})
	assert data["sheet"]["sheets"]["Costing"]["rows"] == {"0": ["Item"], "1": [None, None, "=A1"]}
	assert data["formats"]["Costing"]["cells"]["A1"] == {"bold": True}
	data = room["written"](data, "Costing", {"A1": ""}, {})
	assert data["sheet"]["sheets"]["Costing"]["rows"]["0"] == [None], "an empty value clears the cell"
	data = room["noted"](data, "Costing", "C2", "Check this rate", "a@b.c", "A B", "2026-10-21")
	assert data["comments"]["Costing"]["C2"]["thread"][0]["text"] == "Check this rate"


def test_a_sheet_prints_as_it_is_drawn():
	import html
	import re

	room = {"re": re, "escape_html": html.escape, "cint": lambda v: int(float(v or 0))}
	_lifted(
		SHEET / "paper.py",
		("COL_W", "ROW_H", "FONT_SIZE", "GRID", "MOST_CELLS", "MOST_TEXT", "COLOUR", "FAMILY", "ALIGN", "VALIGN", "LINE", "SIDES", "_colour", "_px", "style", "_cells", "_merges", "bands", "_guess", "_table"),
		room,
	)
	room["_picture"] = lambda url: url if url and url.startswith("/files/") else None
	style = room["style"]
	assert style({"bold": True, "color": "#ff0000", "align": "right"}) == "font-weight:bold;color:#ff0000;text-align:right"
	assert style({"color": "red;background:url(x)", "fontFamily": "x;}</style>", "align": "justify"}) == "", "only the keys that print, and only safe values"
	assert style({"borderTop": {"style": "medium", "color": "#123456"}}, gridlines=False) == (
		"border-top:2px solid #123456;border-bottom:0;border-left:0;border-right:0"
	)
	assert room["bands"]([(0, 300), (1, 300), (2, 300), (3, 900)], 700) == [[(0, 300), (1, 300)], [(2, 300)], [(3, 900)]], "over, then down"
	sheet = {
		"size": [3, 4],
		"cells": [
			[0, 0, "A title that runs over the empty cells beside it", {"bold": True}],
			[1, 0, "<b>x</b>", {}],
			[1, 2, "under the merge", {}],
			[2, 0, "", {}, "/files/logo.png"],
			[2, 1, "", {}, "https://elsewhere.example/p.png"],
		],
		"merges": [[1, 1, 1, 2]],
		"widths": {"0": 100},
		"hidden_cols": [3],
		"head": 1,
	}
	drawn = room["_table"](sheet, 10_000, True, True)
	assert drawn.count("<table") == 1 and "<thead>" in drawn and "zoom" not in drawn
	assert 'colspan="3"' in drawn, "a long text spills over its empty neighbours"
	assert "&lt;b&gt;x&lt;/b&gt;" in drawn and "<b>x</b>" not in drawn
	assert "under the merge" not in drawn and 'colspan="2"' in drawn, "a merge spans, and what is under it is hidden"
	assert '<img src="/files/logo.png"' in drawn and "elsewhere" not in drawn, "pictures only from this site's files"
	assert drawn.count("<col ") == 3, "a hidden column isn't printed"
	narrow = room["_table"](sheet, 150, True, True)
	assert "zoom:0.5000" in narrow, "fitted to the page"
	cut = room["_table"](sheet, 150, False, False)
	assert cut.count("<table") == 3 and "page-break-before" in cut and "grid" not in cut


def test_a_workbook_reads_as_excel_writes_it():
	import re

	room = _lifted(SHEET / "excel.py", ("OPEN_RANGE", "LAST_ROW", "CLOSED_RANGE", "DATE_Z", "TIME_Z", "to_excel", "from_excel", "number_format"), {"re": re})
	assert room["to_excel"]("=SUM(H6:H)") == "=SUM(H6:H1048576)", "Excel has no open-ended range"
	assert room["to_excel"]("=SUM(A1:B4)+Sheet2!C3") == "=SUM(A1:B4)+Sheet2!C3", "a closed range is left alone"
	assert room["from_excel"]("=_xlfn.SUM(H6:H1048576)") == "=SUM(H6:H)", "and comes back open"
	code = room["number_format"]
	assert code("number:us:2") == "#,##0.00" and code("percentage") == "0.00%" and code("text") == "@"
	assert code("currency:AED:2", lambda c: "AED") == '"AED "#,##0.00'
	assert code("currency:EUR:2;", lambda c: "€") == '"€ "#,##0.00;-"€ "#,##0.00;;@', "a zero shown blank"
	assert code("date:dmy") == "dd/mm/yyyy" and code("custom:0.0x") == "0.0x" and code("") is None
