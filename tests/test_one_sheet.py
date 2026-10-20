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


def test_ask_shows_the_sheet_and_keeps_only_whole_actions():
	import json
	import re

	room = _lifted(
		SHEET / "assist.py",
		("MOST_ROWS", "MOST_COLS", "MOST_BYTES", "MOST_ACTIONS", "MOST_FORMULA", "MOST_ANSWER", "CELL", "letters", "cells_of", "context", "cleaned"),
		{"json": json, "re": re},
	)
	assert [room["letters"](n) for n in (0, 25, 26, 701)] == ["A", "Z", "AA", "ZZ"]
	data = {"sheet": {"v": 2, "sheets": {"Sheet1": {"rows": {"0": ["Item", "Qty"], "1": ["Glass", "4"]}}}}}
	cells = room["cells_of"](data, "Sheet1")
	said = room["context"](cells, "Sheet1", {"r0": 1, "c0": 1, "r1": 1, "c1": 1, "active": "B2"})
	assert said["used"] == "A1:B2" and said["selection"] == "B2:B2"
	assert said["cells"] == [{"A1": "Item", "B1": "Qty"}, {"A2": "Glass", "B2": "4"}]
	kept = room["cleaned"]([{"type": "setCell", "cell": "b3", "formula": "=B2*2"}, {"type": "setCell", "cell": "B"}, {"type": "drop"}, {"type": "answer", "text": " "}])
	assert kept == [{"type": "setCell", "cell": "B3", "formula": "=B2*2"}]


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
	_lifted(SHEET / "assist.py", ("letters",), room)
	import html

	room["html"] = html
	names = ("NUMBER", "TEXT", "SHOWN", "MOST_COLUMNS", "MOST_ROWS", "SPARE", "LOCKED_TO", "MARK", "YES", "NO", "EPOCH")
	_lifted(SHEET / "table.py", (*names, "columns", "shown", "taken", "lined", "fingerprint", "_rule", "kept", "laid", "stored", "emptied", "placed", "read", "back"), room)
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
	assert room["read"]([["#" + mark, "Item"]], cols)[2][0].startswith("The column Kind"), "a column gone is refused"


def test_a_table_sheet_keeps_its_formulas():
	import html
	import re

	room = {"_": lambda text: text, "re": re, "html": html}
	_lifted(SHEET / "assist.py", ("letters",), room)
	names = ("NUMBER", "TEXT", "SHOWN", "MOST_COLUMNS", "MARK", "SPARE", "LOCKED_TO")
	_lifted(SHEET / "table.py", (*names, "columns", "shown", "_rule", "kept", "laid", "stored", "emptied"), room)
	fields = [
		{"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "in_list_view": 1},
		{"fieldname": "description", "label": "Description", "fieldtype": "Text Editor"},
		{"fieldname": "qty", "label": "Qty", "fieldtype": "Float", "in_list_view": 1},
		{"fieldname": "rate", "label": "Rate", "fieldtype": "Currency", "in_list_view": 1},
	]
	assert [col["fieldname"] for col in room["columns"](fields)] == ["name", "item_name", "qty", "rate"], "formatted text only when asked for"
	cols = room["columns"](fields, also=["description"])
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
	kept = room["emptied"](data, "Items")
	assert room["stored"](kept, "Items") == {
		"0": ["#", "Item Name", "Rate", "Qty", "Description"],
		"1": [None, "=Costing!A4:A", "=Costing!P4:P/Costing!C4:C", None, None],
		"2": [None, None, None, "=C2*2", None],
	}, "the header and the formulas, not the rows"
	assert room["stored"](kept, "Costing") == {"3": ["CW01"]} and "Items" not in kept["protection"] and kept["view"] == data["view"]
	assert room["shown"]("<p>Aluminum &amp; glass</p>", "Text Editor") == "Aluminum & glass"
