"""How a workbook looks when One lays it out: the company's branding that
BRAND() reads, a record's fields that RECORD() reads, and the formats of a
record's table sheet and a template's sheets, in the editor's own shapes
(engine/formats.js: cells, cols and rows; numberFormat grammar of
utils/format-number.js). README, Branded sheets.
"""

import frappe
from frappe.utils import cint, strip_html

from onedesk.one_sheet.assist import letters

#: A header's text on the company's colour.
ON_COLOUR = "#FFFFFF"
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
	from onedesk.one import letter_heads

	held = letter_heads.company()
	company = frappe.db.get_default("company")
	return {
		"name": held.get("name") or "",
		"logo": held.get("logo") or "",
		"colour": held.get("colour") or letter_heads.INK,
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
	"""A header row: bold white on the company's colour. Pure."""
	return {"bold": True, "color": ON_COLOUR, "backgroundColor": colour, "valign": "middle", "textWrap": "wrap"}


def table(cols: list[dict], colour: str, currency: str = "", precisions: dict | None = None) -> dict:
	"""A record's table sheet: the header on the company's colour, numbers
	formatted as their fields are, what the record works out in grey, and
	widths by kind. Answers {"formats", "colW", "rowH"}. Pure."""
	precisions = precisions or {}
	formats = {"cells": {}, "cols": {}, "rows": {"0": header(colour)}}
	widths = {"0": 40}
	for at, col in enumerate(cols):
		if not at:
			continue
		held = {}
		kind = number_format(col["fieldtype"], currency, precisions.get(col["fieldtype"]))
		if kind:
			held["numberFormat"] = kind
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


#: Where a branded sheet's lines start: under the brand block, a stripe of
#: the company's colour, and the header.
FIRST = 6

#: What each kind of column holds, as the editor formats it.
KINDS = {"count": "number:us:0", "size": "number:us:0", "area": "number:us:3", "kilos": "number:us:2"}


def branded(title: str, head: list, line: dict, totals: dict, kinds: dict, colour: str, currency: str = "", meta: list | None = None, lines: int = 100) -> dict:
	"""A sheet laid out under the company's brand, `meta` (label, formula)
	beside it, `line`'s formulas ({r} the row) on `lines` lines and `totals`
	under them; `kinds` names the columns holding money, counts, sizes,
	areas, kilos, the key figures and wide text. Answers its rows, formats,
	merges and view. README, Branded sheets. Pure."""
	wide = len(head)
	last = FIRST + lines - 1
	rows, cells, masters, slaves = {}, {}, {}, {}
	col = {letters(at): at for at in range(max(wide, 26))}

	def put(ref, value=None, look=None):
		at, line_no = col[ref.rstrip("0123456789")], int(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) - 1
		if value is not None:
			held = rows.setdefault(str(line_no), [])
			held.extend([None] * (at + 1 - len(held)))
			held[at] = value
		if look:
			cells[ref] = {**cells.get(ref, {}), **look}

	def merge(ref, row_span, col_span):
		at, line_no = col[ref.rstrip("0123456789")], int(ref.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) - 1
		masters[ref] = {"rowSpan": row_span, "colSpan": col_span, "r": line_no, "c": at}
		for r in range(line_no, line_no + row_span):
			for c in range(at, at + col_span):
				if (r, c) != (line_no, at):
					slaves[f"{letters(c)}{r + 1}"] = ref

	put("A1", '=IMAGE(BRAND("logo"))', {"align": "left"})
	merge("A1", 3, 2)
	put("C1", '=BRAND("name")', {"bold": True, "fontSize": 16, "valign": "middle", "numberFormat": "text", "align": "left"})
	put("C2", title, {"color": MUTED, "fontSize": 12, "numberFormat": "text", "align": "left"})
	put("C3", '=BRAND("address")', {"color": MUTED, "fontSize": 11, "numberFormat": "text", "align": "left"})
	first_label = 6
	for at, (label, formula) in enumerate((meta or [])[:6]):
		label_col = first_label + (at // 3) * 4
		row = at % 3 + 1
		put(f"{letters(label_col)}{row}", label, {"color": MUTED, "fontSize": 11, "align": "right", "numberFormat": "text"})
		put(f"{letters(label_col + 1)}{row}", formula, {"bold": True, "numberFormat": "text", "align": "left"})
		merge(f"{letters(label_col + 1)}{row}", 1, 2)
	for at in range(wide):
		put(f"{letters(at)}4", None, {"backgroundColor": colour})
		put(f"{letters(at)}5", head[at] if at < len(head) else None, {**header(colour), "align": "center"})
	worked = set(line)
	key = set(kinds.get("key", ""))
	for r in range(FIRST, last + 1):
		for letter, formula in line.items():
			put(f"{letter}{r}", formula.replace("{r}", str(r)))
		for letter in worked | key:
			look = {"backgroundColor": WORKED}
			if letter in key:
				look = {"backgroundColor": tint(colour, 0.1), "bold": True}
			put(f"{letter}{r}", None, look)
	end = last + 2
	for at in range(wide):
		put(f"{letters(at)}{end}", None, {"bold": True, "backgroundColor": tint(colour, 0.14), "borderTop": {"style": "medium", "color": colour}})
	for letter, value in totals.items():
		put(f"{letter}{end}", value.replace("{first}", str(FIRST)).replace("{last}", str(last)))
	formats_cols, widths = {}, {}
	for at in range(wide):
		letter = letters(at)
		kind = next((name for name, held in kinds.items() if letter in held and name in (*KINDS, "money")), None)
		blank = ";" if letter in worked else ""
		if kind == "money":
			formats_cols[str(at)] = {"numberFormat": (f"currency:{currency}:2" if currency else "number:us:2") + blank}
		elif kind:
			formats_cols[str(at)] = {"numberFormat": KINDS[kind] + blank}
		widths[str(at)] = 300 if letter in kinds.get("wide", "") else 124 if kind == "money" else 76 if kind == "count" else 108
	widths["0"] = max(widths.get("0", 96), 120)
	return {
		"rows": rows,
		"formats": {"cells": cells, "cols": formats_cols, "rows": {}},
		"merge": {"masterMap": masters, "slaveMap": slaves},
		"view": {"freezeRows": FIRST - 1, "freezeCols": 2, "colW": widths, "rowH": {"0": 30, "1": 24, "2": 24, "3": 5, "4": 44}},
	}
