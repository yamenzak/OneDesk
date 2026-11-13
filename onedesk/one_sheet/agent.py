"""What OneAI can do with workbooks: find them and read their cells as they
run, and make one, write cells and formats, or leave a note on a cell as a
card the reader approves (one_ai/proposals.py, Setup). Every one runs as the
person asking, with OneCloud's answer for the File behind the workbook.
AGENTS.md, Asking OneAI.
"""

import json
from typing import Annotated

import frappe
from frappe import _

from onedesk.one_sheet import api, storage
from onedesk.one_sheet.cells import CELL, letters

# The calls that change something OneAI reaches as a card, by the tool whose
# card makes the call when it is approved (docs/READY.md, mechanism 11).
REACH = {"api.make": "draft_workbook", "api.save_sheet": "write_cells"}

# Why OneAI's chat does not do these itself: each is the editor's own, or
# the person's call, made in the editor.
NOT_FOR_AI = {
	"api.rename_sheet": "A workbook is named from its title in the editor, by the person working on it.",
	"api.open_file": "It answers an Excel or CSV file opened from OneCloud.",
	"api.write_back": "It writes the Excel or CSV file back as the person works on it in the editor, or chooses how.",
	"api.dismiss_dropped": "It puts away the note of what a save from the drive left out, in the editor.",
	"paper.pdf": "Printing is the person's choice of sheets, letter head and page, made in the editor's Print dialog.",
	"table.open_table": "A record's table opens in a workbook from the record's form, by the person reading it.",
	"table.redrawn": "It draws a record's table again in the open editor after the record changed on its form.",
	"table.make_missing": "It makes the records a sheet names that do not exist yet, asked from the cell by the person.",
	"templates.save_as": "A template is kept from the editor's File menu by whoever may keep company templates.",
	"versions.label_snapshot": "A version is named in Version History by the person working on it.",
	"versions.make_copy": "A copy of a version is made from Version History by the person working on it.",
	"versions.restore": "Going back to a version is the person's call, from the editor's Version History.",
}

LEVELS = {
	"api.make": "Draft",
	"api.save_sheet": "Draft",
}
"""How far its agent goes with each action (one_ai/agents/levels.py)."""

#: The most cells a read answers with, and a card writes.
MOST_CELLS = 2000

#: What a cell's look can say, and the editor's own words for it.
LOOKS = ("bold", "italic", "color", "backgroundColor", "numberFormat", "align", "fontSize", "textWrap")


def _at(ref: str) -> tuple[int, int] | None:
	"""A1 as (row, col) from 0. Pure."""
	found = CELL.match(str(ref or "").strip().upper())
	if not found:
		return None
	col = 0
	for one in found.group(1):
		col = col * 26 + ord(one) - 64
	return int(found.group(2)) - 1, col - 1


def _span(ref: str) -> list[tuple[int, int]]:
	"""A1 or A1:C4 as every cell in it, row by row. Pure."""
	ends = [_at(one) for one in str(ref or "").split(":")]
	if not ends or None in ends or len(ends) > 2:
		return []
	(r0, c0), (r1, c1) = ends[0], ends[-1]
	return [(r, c) for r in range(min(r0, r1), max(r0, r1) + 1) for c in range(min(c0, c1), max(c0, c1) + 1)]


def _data(name: str) -> dict:
	return json.loads(storage.decode_sheets_data(frappe.db.get_value(api.WORKBOOK, name, "sheets_data")) or "{}")


def _sheets(data: dict) -> list[str]:
	return list(((data.get("sheet") or {}).get("sheets") or {}).keys())


def _readable(workbook: str) -> dict | None:
	if not frappe.db.exists(api.WORKBOOK, workbook):
		return None
	try:
		return api._may(workbook, "read")
	except frappe.PermissionError:
		return None


def my_workbooks(
	words: Annotated[str, "Words from the workbook's name, or nothing for the latest."] | None = None,
) -> list[dict]:
	"""Find workbooks the reader may open, newest first: each one's id, name
	and sheets. Templates are left out."""
	from onedesk.one_cloud import namespace as ns

	filters = {"is_template": 0}
	if words:
		filters["title"] = ["like", f"%{words}%"]
	out = []
	for one in frappe.get_all(api.WORKBOOK, filters=filters, fields=["name", "title", "file", "modified"], order_by="modified desc", limit=100):
		item = ns.row(one.file) if one.file else None
		if not item or item.get("one_deleted_on") or not ns.may(item, "read"):
			continue
		out.append({"workbook": one.name, "name": item["file_name"], "sheets": _sheets(_data(one.name)), "changed": str(one.modified)})
		if len(out) == 20:
			break
	return out


def read_workbook(
	workbook: Annotated[str, "The workbook's id, from my_workbooks."],
	sheet: Annotated[str, "Which sheet. Defaults to the first."] | None = None,
	cells: Annotated[str, "A range such as A1:H40. Defaults to what the sheet holds."] | None = None,
) -> dict:
	"""Read a sheet's cells as they are written: values, and formulas as
	formulas (a formula's result is worked out in the browser, so say what it
	computes rather than a number). Also says the sheets there are and any
	notes on the cells."""
	if not _readable(workbook):
		return {"error": f"No workbook the reader may open is {workbook}."}
	data = _data(workbook)
	names = _sheets(data)
	sheet = sheet or (names[0] if names else None)
	if sheet not in names:
		return {"error": f"{workbook} has no sheet called {sheet}. It has: {', '.join(names)}."}
	from onedesk.one_sheet.cells import cells_of

	held = cells_of(data, sheet)
	wanted = set(_span(cells)) if cells else None
	shown = {f"{letters(c)}{r + 1}": value for (r, c), value in sorted(held.items()) if wanted is None or (r, c) in wanted}
	cut = len(shown) > MOST_CELLS
	notes = {
		ref: " / ".join(one.get("text", "") for one in (said or {}).get("thread", []))
		for ref, said in ((data.get("comments") or {}).get(sheet) or {}).items()
		if isinstance(said, dict)
	}
	return {
		"workbook": workbook,
		"sheets": names,
		"sheet": sheet,
		"cells": dict(list(shown.items())[:MOST_CELLS]),
		**({"cut": f"Only the first {MOST_CELLS} cells; ask for a range."} if cut else {}),
		**({"notes": notes} if notes else {}),
	}


def _cells_given(cells, looks) -> tuple[dict, dict, str | None]:
	"""The cells and looks a model asked for, checked. Pure."""
	given, styled = {}, {}
	for ref, value in (cells or {}).items():
		if not _at(ref):
			return {}, {}, f"{ref} isn't a cell. Name cells as A1, B12."
		given[str(ref).upper()] = "" if value is None else value if isinstance(value, int | float) else str(value)
	for ref, look in (looks or {}).items():
		span = _span(ref)
		if not span:
			return {}, {}, f"{ref} isn't a cell or a range. Name them as A1 or A1:C4."
		kept = {key: value for key, value in (look or {}).items() if key in LOOKS}
		if not kept:
			return {}, {}, f"A look says one of: {', '.join(LOOKS)}."
		for r, c in span:
			styled[f"{letters(c)}{r + 1}"] = {**styled.get(f"{letters(c)}{r + 1}", {}), **kept}
	if len(given) + len(styled) > MOST_CELLS:
		return {}, {}, f"At most {MOST_CELLS} cells a card."
	return given, styled, None


CELLS = "Cell to what it holds: a value, or a formula starting with =, such as {\"A1\": \"Item\", \"D2\": \"=B2*C2\"}."
LOOK = (
	"A cell or range to its look: bold, italic, color and backgroundColor (#rrggbb), align (left, center, right), "
	"fontSize, textWrap, numberFormat (number:us:2, currency:EUR:2, percentage, date, text). "
	'Such as {"A1:F1": {"bold": true, "backgroundColor": "#0E6E8C", "color": "#ffffff"}}.'
)


def draft_workbook(
	name: Annotated[str, "What to call it."],
	sheets: Annotated[
		list[dict],
		'Its sheets, in order, each {"name": ..., "cells": {...}, "looks": {...}}. ' + CELLS + " " + LOOK,
	],
	folder: Annotated[str, "The OneCloud folder to make it in, as its path. Defaults to the reader's own files."]
	| None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a new workbook, as a card the reader approves: its sheets,
	the values and formulas in them and how they look. Approving makes it in
	OneCloud as New › Workbook does and opens nothing."""
	from onedesk.one_ai import proposals

	laid = []
	for at, one in enumerate(sheets or []):
		if not isinstance(one, dict):
			return {"mend": "draft_workbook", "error": "Each sheet is an object with a name, cells and looks."}
		given, styled, wrong = _cells_given(one.get("cells"), one.get("looks"))
		if wrong:
			return {"mend": "draft_workbook", "error": wrong}
		laid.append({"name": str(one.get("name") or f"Sheet{at + 1}")[:100], "cells": given, "looks": styled})
	if not laid:
		return {"mend": "draft_workbook", "error": "A workbook has at least one sheet."}
	changes = {
		"what": "workbook",
		"title": _("Create Workbook {0}").format(name),
		"name": name,
		"folder": folder or "",
		"sheets": laid,
		"summary": [
			{"label": _("Sheets"), "value": ", ".join(one["name"] for one in laid)},
			{"label": _("Cells"), "value": str(sum(len(one["cells"]) for one in laid))},
		],
	}
	return {
		"proposal": proposals.propose("Setup", api.WORKBOOK, changes=changes, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it makes. Nothing is made until they approve it.",
	}


def write_cells(
	workbook: Annotated[str, "The workbook's id, from my_workbooks."],
	sheet: Annotated[str, "Which sheet; a name it doesn't have adds that sheet."],
	cells: Annotated[dict, CELLS + ' An empty value ("") clears the cell.'] | None = None,
	looks: Annotated[dict, LOOK] | None = None,
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest values, formulas and formatting in a workbook, as a card the
	reader approves; a sheet it doesn't have yet is added. Read it first so
	what is written fits what is there. Approving writes them as the reader
	would, and an open copy of the workbook reloads. A record's table sheet
	is changed from its record, never from here."""
	from onedesk.one_ai import proposals

	item = _readable(workbook)
	if not item:
		return {"error": f"No workbook the reader may open is {workbook}."}
	try:
		api._may(workbook, "write")
	except frappe.PermissionError:
		return {"error": "The reader may not change this workbook."}
	if sheet and sheet == frappe.db.get_value(api.WORKBOOK, workbook, "bound_sheet"):
		return {"error": f"{sheet} is the record's table. Change the record instead, or write on another sheet."}
	given, styled, wrong = _cells_given(cells, looks)
	if wrong:
		return {"mend": "write_cells", "error": wrong}
	if not given and not styled:
		return {"mend": "write_cells", "error": "Say which cells to write or how they look."}
	changes = {
		"what": "cells",
		"title": _("Edit {0}, {1}").format(item["file_name"], sheet),
		"workbook": workbook,
		"sheet": sheet,
		"cells": given,
		"looks": styled,
		"summary": [{"label": ref, "value": str(value)} for ref, value in list(given.items())[:8]]
		+ ([{"label": _("More"), "value": _("{0} more cells").format(len(given) - 8)}] if len(given) > 8 else [])
		+ ([{"label": _("Formatted"), "value": _("{0} cells").format(len(styled))}] if styled else []),
	}
	return {
		"proposal": proposals.propose("Setup", api.WORKBOOK, changes=changes, record=workbook, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what approving it writes. Nothing changes until they approve it.",
	}


def comment_on_cell(
	workbook: Annotated[str, "The workbook's id, from my_workbooks."],
	sheet: Annotated[str, "Which sheet."],
	cell: Annotated[str, "The cell, such as D14."],
	text: Annotated[str, "The note, in plain words."],
	why: Annotated[str, "In a sentence, why."] | None = None,
) -> dict:
	"""Suggest a note on a cell, as a card the reader approves; it shows as
	the cell's corner mark and in Notes, signed by the reader."""
	from onedesk.one_ai import proposals

	item = _readable(workbook)
	if not item:
		return {"error": f"No workbook the reader may open is {workbook}."}
	if sheet not in _sheets(_data(workbook)):
		return {"mend": "comment_on_cell", "error": f"{workbook} has no sheet called {sheet}."}
	if not _at(cell):
		return {"mend": "comment_on_cell", "error": f"{cell} isn't a cell. Name it as D14."}
	changes = {
		"what": "note",
		"title": _("Comment on {0} in {1}").format(cell.upper(), item["file_name"]),
		"workbook": workbook,
		"sheet": sheet,
		"cell": cell.upper(),
		"text": str(text or "").strip()[:2000],
		"summary": [{"label": cell.upper(), "value": str(text or "").strip()[:200]}],
	}
	return {
		"proposal": proposals.propose("Setup", api.WORKBOOK, changes=changes, record=workbook, why=why),
		"state": "Proposed",
		"next": "Say in one sentence what the note says. Nothing changes until they approve it.",
	}


def written(data: dict, sheet: str, cells: dict, looks: dict) -> dict:
	"""`data` with `cells` written into `sheet` (added when it isn't there)
	and `looks` laid over each cell's format. Pure."""
	held = data.get("sheet") if isinstance(data.get("sheet"), dict) and data["sheet"].get("v") == 2 else None
	if not held:
		held = {"v": 2, "current": sheet, "sheets": {}}
	page = held["sheets"].setdefault(sheet, {"rows": {}})
	rows = page.setdefault("rows", {})
	for ref, value in cells.items():
		r, c = _at(ref)
		line = rows.setdefault(str(r), [])
		line.extend([None] * (c + 1 - len(line)))
		line[c] = value if value != "" else None
	data["sheet"] = held
	if looks:
		formats = data.get("formats") if isinstance(data.get("formats"), dict) else {}
		mine = formats.setdefault(sheet, {"cells": {}, "cols": {}, "rows": {}})
		mine.setdefault("cells", {})
		for ref, look in looks.items():
			mine["cells"][ref] = {**mine["cells"].get(ref, {}), **look}
		data["formats"] = formats
	return data


def noted(data: dict, sheet: str, cell: str, text: str, author: str, name: str, when: str) -> dict:
	"""`data` with a note added to `cell`'s thread. Pure."""
	comments = data.get("comments") if isinstance(data.get("comments"), dict) else {}
	mine = comments.setdefault(sheet, {})
	thread = mine.get(cell) if isinstance(mine.get(cell), dict) else {"resolved": False, "thread": []}
	thread["resolved"] = False
	thread.setdefault("thread", []).append({"author": author, "name": name, "text": text, "ts": when})
	mine[cell] = thread
	data["comments"] = comments
	return data


def approved(changes: dict) -> str:
	"""A workbook card approved, as the person who pressed Approve."""
	from frappe.utils import get_fullname, now_datetime

	if changes["what"] == "workbook":
		from onedesk.one_cloud import namespace as ns

		made = api.make(changes.get("folder") or ns.HOME, changes["name"])
		data = {}
		for one in changes["sheets"]:
			data = written(data, one["name"], one["cells"], one["looks"])
		data["sheet"]["current"] = changes["sheets"][0]["name"]
		api.save_sheet(changes["name"], json.dumps(data), made["workbook"])
		return made["workbook"]
	name = changes["workbook"]
	item = api._may(name, "write")
	data = _data(name)
	if changes["what"] == "cells":
		data = written(data, changes["sheet"], changes["cells"], changes["looks"])
	else:
		data = noted(data, changes["sheet"], changes["cell"], changes["text"], frappe.session.user, get_fullname(), str(now_datetime()))
	api.save_sheet(item["file_name"], json.dumps(data), name)
	frappe.publish_realtime("one_sheet_written", {"workbook": name}, user=frappe.session.user, after_commit=True)
	return name


#: How many cells the panel is told up front about a selection.
MOST_SEEN = 200


def page(said: dict) -> str | None:
	"""The sentence the model is told on a workbook's page: which workbook,
	its sheets, the record whose table it shows, and the cells the reader has
	selected with what they hold."""
	if said.get("page") != "workbook":
		return None
	name = (said.get("record") or "").strip()
	item = _readable(name) if name else None
	if not item:
		return "The reader is on a workbook's page in OneSheet."
	from onedesk.one_sheet import table

	data = _data(name)
	names = _sheets(data)
	where = f'The reader has the workbook "{item["file_name"]}" open in OneSheet (its id is {name}); its sheets are {", ".join(names)}'
	bound = table.bound(name)
	if bound:
		where += f'. The sheet {bound["sheet"]} is the {bound["label"]} table of {bound["doctype"]} {bound["name"]}, changed from the record, never by write_cells'
	selected = said.get("selection") if isinstance(said.get("selection"), dict) else {}
	if selected.get("workbook") == name and selected.get("sheet") in names and selected.get("range"):
		read = read_workbook(name, selected["sheet"], selected["range"])
		held = dict(list((read.get("cells") or {}).items())[:MOST_SEEN])
		where += (
			f'. The reader is on the sheet {selected["sheet"]} with {selected["range"]} selected'
			+ (f' (the active cell is {selected["active"]})' if selected.get("active") else "")
			+ f"; those cells hold {json.dumps(held, default=str)}. A request about \"this\" or \"these\" means the selection"
		)
	return where + (
		". read_workbook reads any sheet; write_cells writes values, formulas and formatting, and comment_on_cell "
		"leaves a note, each as a card. How OneSheet works is in its documentation (how_to)."
	)


READS = (
	"my_workbooks",
	"read_workbook",
)
"""The tools OneAI reads here (registry/hooks.py lists them in one_ai_reads)."""


SUGGESTS = (
	"draft_workbook",
	"write_cells",
	"comment_on_cell",
)
"""The tools OneAI suggests, each as a card a person applies here (registry/hooks.py lists them in one_ai_suggests)."""
