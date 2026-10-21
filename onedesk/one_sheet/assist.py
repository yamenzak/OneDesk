"""Ask OneAI in a workbook: a request about the selection becomes cells to
write or an answer, which the editor applies as one edit that undo takes
back. After Suite's sheets/ai, through the account's gateway and credits.
README, assist.py.
"""

import json
import re

import frappe
from frappe import _

from onedesk.one_sheet import api, storage

ACTION = "sheet_assist"

MOST_PROMPT = 2000
MOST_ROWS, MOST_COLS, MOST_BYTES = 25, 40, 12_000
MOST_ACTIONS, MOST_FORMULA, MOST_ANSWER = 200, 1000, 4000

CELL = re.compile(r"^([A-Z]{1,3})([1-9][0-9]{0,6})$")


def letters(col: int) -> str:
	"""0 → A, 26 → AA. Pure."""
	out, col = "", col + 1
	while col:
		col, rest = divmod(col - 1, 26)
		out = chr(65 + rest) + out
	return out


def cells_of(data: dict, sheet: str) -> dict[tuple[int, int], object]:
	"""A sheet's cells by (row, col), from the saved workbook. Pure."""
	held = ((data.get("sheet") or {}).get("sheets") or {}).get(sheet) or {}
	out = {}
	for row, values in (held.get("rows") or {}).items():
		for col, value in enumerate(values or []):
			if value not in (None, ""):
				out[(int(row), col)] = value
	return out


def context(cells: dict, sheet: str, selection: dict) -> dict:
	"""What the model is shown: the used range, its first row, up to
	MOST_ROWS rows of up to MOST_COLS columns, and the selection. Pure."""
	rows = sorted({row for row, _col in cells})
	cols = sorted({col for _row, col in cells})
	last_row, last_col = (rows[-1] if rows else 0), (cols[-1] if cols else 0)
	shown_cols = range(min(last_col + 1, MOST_COLS))
	table = []
	for row in range(min(last_row + 1, MOST_ROWS + 1)):
		line = {f"{letters(col)}{row + 1}": cells[(row, col)] for col in shown_cols if (row, col) in cells}
		if line:
			table.append(line)
	r0, c0, r1, c1 = (int(selection.get(key) or 0) for key in ("r0", "c0", "r1", "c1"))
	said = {
		"sheet": sheet,
		"used": f"A1:{letters(last_col)}{last_row + 1}",
		"selection": f"{letters(min(c0, c1))}{min(r0, r1) + 1}:{letters(max(c0, c1))}{max(r0, r1) + 1}",
		"active": selection.get("active") or None,
		"cells": table,
		"truncated": last_row + 1 > MOST_ROWS + 1 or last_col + 1 > MOST_COLS,
	}
	while len(json.dumps(said, default=str)) > MOST_BYTES and said["cells"]:
		said["cells"].pop()
		said["truncated"] = True
	return said


def cleaned(raw) -> list[dict]:
	"""The actions that are well formed, the rest dropped. Pure."""
	out = []
	for one in (raw if isinstance(raw, list) else [])[:MOST_ACTIONS]:
		if not isinstance(one, dict):
			continue
		if one.get("type") == "setCell":
			cell = str(one.get("cell") or "").strip().upper()
			formula = one.get("formula")
			if CELL.match(cell) and formula is not None and len(str(formula)) <= MOST_FORMULA:
				out.append({"type": "setCell", "cell": cell, "formula": str(formula)})
		elif one.get("type") == "answer" and isinstance(one.get("text"), str) and one["text"].strip():
			out.append({"type": "answer", "text": one["text"][:MOST_ANSWER]})
	return out


@frappe.whitelist(methods=["POST"])
def ai_assist(name: str, prompt: str, selection: str | None = None) -> dict:
	"""The editor's Ask: cells to write and answers, never written here."""
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	api._may(name, "write")
	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Enter a request first."))
	if len(prompt) > MOST_PROMPT:
		frappe.throw(_("The request is too long."))
	chosen = frappe.parse_json(selection) if selection else {}
	chosen = chosen if isinstance(chosen, dict) else {}
	sheet = chosen.get("sheet") or "Sheet1"
	data = json.loads(storage.decode_sheets_data(frappe.db.get_value(api.WORKBOOK, name, "sheets_data")) or "{}")
	asked = (
		f"The sheet (JSON):\n{json.dumps(context(cells_of(data, sheet), sheet, chosen), default=str)}\n\n"
		f"The request: {prompt}"
	)
	said = read(run.once(ACTION, asked, reference=name)) or {}
	return {"actions": cleaned(said.get("actions")), "source": "model"}
