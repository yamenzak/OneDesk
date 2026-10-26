"""How a workbook looks when One lays it out: the company's branding that
BRAND() reads, a record's fields that RECORD() reads, and the formats of a
record's table sheet and a template's sheets, in the editor's own shapes
(engine/formats.js: cells, cols and rows; numberFormat grammar of
utils/format-number.js). README, Branded sheets.
"""

import re

import frappe
from frappe.utils import cint, strip_html

from onedesk.one_sheet.cells import letters
from onedesk.one_studio import letter_heads

#: Lines worked out by a formula, and the rows around a header.
WORKED = "#F5F5F4"
LINE = "#E7E5E4"
MUTED = "#57534E"


def tint(colour: str, share: float) -> str:
	"""`colour` mixed with white, `share` of it kept. Pure."""
	held = colour.lstrip("#")
	if len(held) == 3:
		held = "".join(one * 2 for one in held)
	try:
		red, green, blue = (int(held[at : at + 2], 16) for at in (0, 2, 4))
	except ValueError:
		return WORKED
	return "#" + "".join(f"{round(255 - (255 - one) * share):02X}" for one in (red, green, blue))


def brand() -> dict:
	"""The company as BRAND() reads it: name, logo, colour, currency and
	where to reach it."""
	held = letter_heads.company()
	company = frappe.db.get_default("company")
	return {
		"name": held.get("name") or "",
		"logo": held.get("logo") or "",
		"colour": held.get("colour") or letter_heads.INK,
		"on_colour": letter_heads.on(held.get("colour") or letter_heads.INK),
		"currency": (company and frappe.db.get_value("Company", company, "default_currency")) or "",
		"address": ", ".join(held.get("address") or []),
		"phone": held.get("phone") or "",
		"email": held.get("email") or "",
		"website": held.get("website") or "",
		"tax_id": held.get("tax_id") or "",
	}


def record(doc) -> dict:
	"""A record's own fields as its form shows them, for RECORD(): links by
	their name, dates and money as the reader formats them."""
	if not doc:
		return {}
	out = {"name": doc.name, "doctype": doc.doctype}
	for df in doc.meta.fields:
		if df.fieldtype in frappe.model.no_value_fields or df.fieldtype in frappe.model.table_fields:
			continue
		value = doc.get(df.fieldname)
		if value in (None, ""):
			continue
		if df.fieldtype in ("Link", "Dynamic Link", "Data", "Select", "Small Text", "Text", "Long Text", "Read Only"):
			out[df.fieldname] = str(value)
			continue
		try:
			out[df.fieldname] = strip_html(str(frappe.format(value, df, doc=doc))).strip()
		except Exception:
			out[df.fieldname] = str(value)
	return out


def number_format(fieldtype: str, currency: str = "", precision: int | None = None) -> str | None:
	"""The editor's number format for a field type. Pure."""
	if fieldtype == "Currency":
		return f"currency:{currency}:{2 if precision is None else precision}" if currency else f"number:us:{2 if precision is None else precision}"
	if fieldtype in ("Float", "Duration"):
		return f"number:us:{3 if precision is None else precision}"
	if fieldtype == "Int":
		return "number:us:0"
	if fieldtype == "Percent":
		return f'custom:#,##0.{"0" * (2 if precision is None else max(precision, 0))}"%"'.replace('.""', '""')
	return None


def width(fieldtype: str) -> int:
	"""How wide a column starts, by what it holds. Pure."""
	if fieldtype in ("Text Editor", "Small Text", "Text", "Long Text", "Code", "Markdown Editor", "HTML Editor"):
		return 280
	if fieldtype in ("Check",):
		return 72
	if fieldtype in ("Int", "Float", "Currency", "Percent", "Duration", "Rating"):
		return 116
	if fieldtype in ("Date", "Datetime", "Time"):
		return 120
	return 170


def header(colour: str) -> dict:
	"""A header row: bold on the company's colour, in whichever of white or
	ink reads on it. Pure."""
	return {"bold": True, "color": letter_heads.on(colour), "backgroundColor": colour, "valign": "middle", "textWrap": "wrap"}


#: Numbers a line leaves at zero when it has none, a size or a count it does
#: not use: blank in a table sheet, as on the form. A required one and money
#: show their zero.
UNSET_AT_ZERO = ("Int", "Float", "Percent")


def table(cols: list[dict], colour: str, currency: str = "", precisions: dict | None = None) -> dict:
	"""A record's table sheet: the header on the company's colour, numbers
	formatted as their fields are (a field's own precision first; an optional
	one blank at zero), what the record works out in grey, and widths by kind.
	Answers {"formats", "colW", "rowH"}. Pure."""
	precisions = precisions or {}
	formats = {"cells": {}, "cols": {}, "rows": {"0": header(colour)}}
	widths = {"0": 40}
	for at, col in enumerate(cols):
		if not at:
			continue
		held = {}
		own = col.get("precision")
		kind = number_format(col["fieldtype"], currency, own if own is not None else precisions.get(col["fieldtype"]))
		if kind:
			held["numberFormat"] = kind + (";" if col["fieldtype"] in UNSET_AT_ZERO and not col.get("reqd") else "")
		if col.get("read_only"):
			held["color"] = MUTED
			held["backgroundColor"] = WORKED
		if held:
			formats["cols"][str(at)] = held
		widths[str(at)] = width(col["fieldtype"])
	return {"formats": formats, "colW": widths, "rowH": {"0": 34}}


def precisions() -> dict:
	"""The workspace's decimals for money and other numbers."""
	return {
		"Currency": cint(frappe.db.get_default("currency_precision")) or 2,
		"Float": cint(frappe.db.get_default("float_precision")) or 3,
		"Percent": cint(frappe.db.get_default("float_precision")) or 2,
	}


#: A branded sheet: the logo and what it is for over three rows, its
#: totals on the fourth, the header on the fifth, and its lines from the sixth.
TOTALS = 4
FIRST = 6

#: What each kind of column holds, as the editor formats it.
KINDS = {"count": "number:us:0", "size": "number:us:0", "area": "number:us:3", "kilos": "number:us:2"}

#: A field beside the logo that is picked or typed: a box to type in.
TYPED_FIELD = {
	"align": "left",
	"backgroundColor": "#FFFFFF",
	**{side: {"style": "thin", "color": "#A8A29E"} for side in ("borderTop", "borderBottom", "borderLeft", "borderRight")},
}

#: A field beside the logo worked out from the others or from the record.
WORKED_FIELD = {"align": "left", "backgroundColor": WORKED, "color": "#292524"}

#: Where the facts beside the logo start: a label, then its value over three
#: columns, three to a group.
META = 3


def branded(title: str, head: list, line: dict, totals: dict, kinds: dict, colour: str, currency: str = "", meta: list | None = None) -> dict:
	"""A sheet laid out under the company's logo: up to nine `meta` fields
	beside it (label, formula, doctype, how), `totals` over the header, and
	`line`'s formulas as the rule each line takes once its first column is
	filled; `kinds` names the columns holding money, counts, sizes, areas,
	kilos, the key figures and wide text. README, Under the hood. Pure."""
	wide = len(head)
	rows, cells, masters, slaves, rules = {}, {}, {}, {}, {}
	col = {letters(at): at for at in range(max(wide, META + 8, 26))}

	def where(ref):
		return col[ref.rstrip("0123456789")], int(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) - 1

	def put(ref, value=None, look=None):
		at, line_no = where(ref)
		if value is not None:
			held = rows.setdefault(str(line_no), [])
			held.extend([None] * (at + 1 - len(held)))
			held[at] = value
		if look:
			cells[ref] = {**cells.get(ref, {}), **look}

	def merge(ref, row_span, col_span):
		at, line_no = where(ref)
		masters[ref] = {"rowSpan": row_span, "colSpan": col_span, "r": line_no, "c": at}
		for r in range(line_no, line_no + row_span):
			for c in range(at, at + col_span):
				if (r, c) != (line_no, at):
					slaves[f"{letters(c)}{r + 1}"] = ref

	put("A1", '=IMAGE(BRAND("logo"))', {"align": "left"})
	merge("A1", 3, 1)
	put("B1", title, {"bold": True, "fontSize": 13, "valign": "middle", "numberFormat": "text", "align": "left"})
	meta = [(*one, None, None)[:4] for one in (meta or [])[:9]]
	value_of = [f"{letters(META + (at // 3) * 4 + 1)}{at % 3 + 1}" for at in range(len(meta))]

	def placed(formula, fixed=False):
		for n, ref in enumerate(value_of):
			formula = formula.replace(f"{{meta{n}}}", re.sub(r"([A-Z]+)(\d+)", r"$\1$\2", ref) if fixed else ref)
		return formula.replace("{first}", str(FIRST))

	line = {letter: placed(formula, fixed=True) for letter, formula in line.items()}
	for at, (label, formula, doctype, how) in enumerate(meta):
		label_col, row = META + (at // 3) * 4, at % 3 + 1
		how = how or {}
		typed = bool(doctype) or how.get("typed")
		put(f"{letters(label_col)}{row}", label, {**header(colour), "textWrap": "clip", "fontSize": 11, "align": "right", "numberFormat": "text"})
		put(value_of[at], placed(formula), {**(TYPED_FIELD if typed else WORKED_FIELD), "numberFormat": how.get("numberFormat") or "text"})
		merge(value_of[at], 1, 3)
		if doctype:
			rules[value_of[at]] = {"type": "link", "doctype": doctype}
	for letter, value in totals.items():
		value, look = value if isinstance(value, tuple) else (value, None)
		put(f"{letter}{TOTALS}", value.replace("{first}", str(FIRST)), look)
	for at in range(wide):
		put(f"{letters(at)}{TOTALS + 1}", head[at], {"align": "center"})
	worked, key = set(line), set(kinds.get("key", ""))
	formats_cols, widths = {}, {}
	for at in range(wide):
		letter = letters(at)
		kind = next((name for name, held in kinds.items() if letter in held and name in (*KINDS, "money")), None)
		blank = ";" if letter in worked else ""
		look = {}
		if kind == "money":
			look["numberFormat"] = (f"currency:{currency}:2" if currency else "number:us:2") + blank
		elif kind:
			look["numberFormat"] = KINDS[kind] + blank
		if letter in key:
			look.update({"backgroundColor": tint(colour, 0.1), "bold": True})
		elif letter in worked:
			look["backgroundColor"] = WORKED
		if look:
			formats_cols[str(at)] = look
		widths[str(at)] = 300 if letter in kinds.get("wide", "") else 124 if kind == "money" else 76 if kind == "count" else 108
	widths["0"] = max(widths.get("0", 96), 120)
	plain = {"backgroundColor": "#FFFFFF", "bold": False}
	return {
		"rows": rows,
		"formats": {
			"cells": cells,
			"cols": formats_cols,
			"rows": {
				**{str(r): plain for r in range(TOTALS - 1)},
				str(TOTALS - 1): {"bold": True, "backgroundColor": tint(colour, 0.14), "borderBottom": {"style": "medium", "color": colour}},
				str(TOTALS): header(colour),
			},
		},
		"merge": {"masterMap": masters, "slaveMap": slaves},
		"validation": rules,
		"lines": {"from": FIRST, "key": "A", "formulas": dict(line)},
		"view": {"freezeRows": TOTALS + 1, "freezeCols": 1, "colW": widths, "rowH": {"0": 30, "1": 24, "2": 24, "3": 28, "4": 44}},
	}
