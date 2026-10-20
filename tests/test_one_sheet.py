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
