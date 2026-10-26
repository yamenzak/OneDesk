"""A sheet or a whole workbook on paper: drawn as the editor shows it, under
the company's letter head, as a PDF to print, keep beside the workbook, or
attach to the record the workbook belongs to. README, paper.py.

The editor sends what it draws (the text each cell shows, its format, the
merges, widths and heights), never HTML: the page is written here, and only
the format keys below reach it.
"""

import re

import frappe
from frappe import _
from frappe.utils import cint, escape_html

from onedesk.one_sheet import api

#: Paper sizes Print Settings may name, in millimetres, portrait.
PAPER = {"A4": (210, 297), "A3": (297, 420), "A5": (148, 210), "Letter": (216, 279), "Legal": (216, 356)}

MARGIN = 15

#: CSS pixels to the millimetre as wkhtmltopdf lays out a page without
#: shrinking it: 500px measured 288pt wide.
PX = 500 / (288 * 25.4 / 72)

COL_W = 100

ROW_H = 24

FONT_SIZE = 13

FONT = "InterVar, Inter, ui-sans-serif, system-ui, sans-serif"

GRID = "#e5e7eb"

MOST_SHEETS = 50

MOST_CELLS = 100_000

MOST_TEXT = 5_000

COLOUR = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(\s*[\d.]+%?\s*,\s*[\d.]+%?\s*,\s*[\d.]+%?\s*(,\s*[\d.]+\s*)?\))$")

FAMILY = re.compile(r"""^[A-Za-z0-9 ,'"-]{1,80}$""")

ALIGN = ("left", "center", "right")

VALIGN = ("top", "middle", "bottom")

LINE = {"thin": "1px solid", "medium": "2px solid", "thick": "3px solid", "dashed": "1px dashed", "dotted": "1px dotted", "double": "3px double"}

SIDES = {"borderTop": "top", "borderBottom": "bottom", "borderLeft": "left", "borderRight": "right"}

KEEP = ("", "cloud", "record")


def _colour(value) -> str | None:
	value = str(value or "").strip()
	return value if COLOUR.match(value) else None


def _px(value, low: int, high: int, default: int) -> int:
	try:
		return min(max(int(float(value)), low), high)
	except (TypeError, ValueError):
		return default


def style(fmt: dict | None, gridlines: bool = True) -> str:
	"""A cell's format as CSS, from the keys the editor keeps and nothing
	else. Pure."""
	fmt = fmt if isinstance(fmt, dict) else {}
	out = []
	if fmt.get("bold"):
		out.append("font-weight:bold")
	if fmt.get("italic"):
		out.append("font-style:italic")
	lines = [one for one, key in (("underline", "underline"), ("line-through", "strikethrough")) if fmt.get(key)]
	if lines:
		out.append("text-decoration:" + " ".join(lines))
	if ink := _colour(fmt.get("color")):
		out.append(f"color:{ink}")
	if fill := _colour(fmt.get("backgroundColor")):
		out.append(f"background:{fill}")
	if fmt.get("fontSize"):
		out.append(f"font-size:{_px(fmt['fontSize'], 6, 72, FONT_SIZE)}px")
	if FAMILY.match(str(fmt.get("fontFamily") or "")):
		out.append(f"font-family:{fmt['fontFamily']}")
	if fmt.get("align") in ALIGN:
		out.append(f"text-align:{fmt['align']}")
	if fmt.get("valign") in VALIGN:
		out.append(f"vertical-align:{fmt['valign']}")
	if fmt.get("textWrap") == "wrap" or fmt.get("wrapText"):
		out.append("white-space:pre-wrap;word-wrap:break-word")
	for key, side in SIDES.items():
		border = fmt.get(key)
		if isinstance(border, dict) and border.get("style") in LINE:
			out.append(f"border-{side}:{LINE[border['style']]} {_colour(border.get('color')) or '#000'}")
		elif not gridlines:
			out.append(f"border-{side}:0")
	return ";".join(out)


def _cells(sheet: dict) -> dict:
	"""{(row, col): (text, format, image)} from what the editor sent, capped."""
	held = {}
	for one in (sheet.get("cells") or [])[:MOST_CELLS]:
		if not isinstance(one, list | tuple) or len(one) < 3:
			continue
		row, col = cint(one[0]), cint(one[1])
		if row < 0 or col < 0:
			continue
		fmt = one[3] if len(one) > 3 and isinstance(one[3], dict) else {}
		image = one[4] if len(one) > 4 and isinstance(one[4], str) else None
		held[(row, col)] = (str(one[2] if one[2] is not None else "")[:MOST_TEXT], fmt, _picture(image))
	return held


def _picture(url: str | None) -> str | None:
	"""A picture only from this site's files."""
	from onedesk.one import printing

	return url if url and printing.FILE_URL.match(url) else None


def _merges(sheet: dict) -> dict:
	"""{(row, col): (rows, cols)} for each merge's top-left cell."""
	held = {}
	for one in sheet.get("merges") or []:
		if isinstance(one, list | tuple) and len(one) == 4:
			row, col, rows, cols = (cint(x) for x in one)
			if row >= 0 and col >= 0 and (rows > 1 or cols > 1):
				held[(row, col)] = (max(rows, 1), max(cols, 1))
	return held


def bands(widths: list[tuple[int, int]], room: float) -> list[list[tuple[int, int]]]:
	"""The columns cut into runs that each fit across the page, left to
	right, as Excel prints a sheet too wide for it. Pure."""
	out, run, used = [], [], 0
	for col, width in widths:
		if run and used + width > room:
			out.append(run)
			run, used = [], 0
		run.append((col, width))
		used += width
	return [*out, run] if run else out


def _guess(text: str, fmt: dict) -> float:
	"""How wide a cell's text runs, near enough to let it spill over its
	empty neighbours as it does on screen."""
	size = _px(fmt.get("fontSize"), 6, 72, FONT_SIZE)
	return len(text) * size * (0.62 if fmt.get("bold") else 0.56) + 8


def _table(sheet: dict, room: float, fit: bool, gridlines: bool) -> str:
	"""One sheet as tables: one fitted to the page width, or one per run of
	columns that fits it. Frozen rows head every page."""
	rows_n = min(cint((sheet.get("size") or [0, 0])[0]), 100_000)
	cols_n = min(cint((sheet.get("size") or [0, 0])[1]), 2_000)
	if not rows_n or not cols_n:
		return ""
	hidden_rows = {cint(one) for one in sheet.get("hidden_rows") or []}
	hidden_cols = {cint(one) for one in sheet.get("hidden_cols") or []}
	given = sheet.get("widths") or {}
	tall = sheet.get("heights") or {}
	cells = _cells(sheet)
	merges = _merges(sheet)
	under = {
		(r, c)
		for (row, col), (rs, cs) in merges.items()
		for r in range(row, row + rs)
		for c in range(col, col + cs)
		if (r, c) != (row, col)
	}
	widths = [
		(col, _px(given.get(str(col), given.get(col)), 8, 2000, COL_W)) for col in range(cols_n) if col not in hidden_cols
	]
	rows = [row for row in range(rows_n) if row not in hidden_rows]
	head = min(max(cint(sheet.get("head")), 0), rows_n)
	whole = sum(width for _, width in widths)
	runs = [widths] if fit else bands(widths, room)
	zoom = min(1.0, room / whole) if fit and whole else 1.0
	out = []
	for at, run in enumerate(runs):
		cols = [col for col, _ in run]
		place = {col: n for n, col in enumerate(cols)}
		parts = [
			f'<table class="sheet{" grid" if gridlines else ""}" style="width:{sum(w for _, w in run)}px;'
			f'{f"zoom:{zoom:.4f};" if zoom < 1 else ""}{"page-break-before:always;" if at else ""}">',
			"<colgroup>" + "".join(f'<col style="width:{w}px">' for _, w in run) + "</colgroup>",
		]
		for section, these in (("thead", [r for r in rows if r < head]), ("tbody", [r for r in rows if r >= head])):
			if not these:
				continue
			order = {row: n for n, row in enumerate(these)}
			covered = set()
			parts.append(f"<{section}>")
			for row in these:
				height = _px(tall.get(str(row), tall.get(row)), 4, 2000, ROW_H)
				parts.append(f'<tr style="height:{height}px">')
				spill = 0
				for col in cols:
					if (row, col) in covered:
						continue
					if spill:
						spill -= 1
						continue
					text, fmt, image = cells.get((row, col), ("", {}, None))
					if (row, col) in under:
						text, image = "", None
					span = ""
					if (row, col) in merges:
						rs, cs = merges[(row, col)]
						down = [r for r in range(row, row + rs) if r in order]
						across = [c for c in range(col, col + cs) if c in place]
						for r in down:
							for c in across:
								covered.add((r, c))
						span = (f' rowspan="{len(down)}"' if len(down) > 1 else "") + (
							f' colspan="{len(across)}"' if len(across) > 1 else ""
						)
					elif text and not image and fmt.get("textWrap") not in ("wrap", "clip") and fmt.get("align") in (None, "", "left"):
						need, room_here, n = _guess(text, fmt), dict(run)[col], place[col] + 1
						while room_here < need and n < len(cols):
							nxt = cols[n]
							if (row, nxt) in cells or (row, nxt) in under or (row, nxt) in merges:
								break
							room_here += dict(run)[nxt]
							spill += 1
							n += 1
						if spill:
							span = f' colspan="{spill + 1}"'
					body = (
						f'<img src="{escape_html(image)}" style="max-height:{height - 4}px">'
						if image
						else escape_html(text).replace("\n", "<br>")
					)
					parts.append(f'<td{span} style="{style(fmt, gridlines)}">{body}</td>')
				parts.append("</tr>")
			parts.append(f"</{section}>")
		parts.append("</table>")
		out.append("".join(parts))
	return "".join(out)


#: The letter head a print asks for to have none.
NO_HEAD = "none"


@frappe.whitelist()
@frappe.read_only()
def letter_heads() -> list[dict]:
	"""The letter heads a print can go under, the default first."""
	return frappe.get_all(
		"Letter Head", filters={"disabled": 0}, fields=["name", "is_default"], order_by="is_default desc, name asc"
	)


def _record(name: str | None) -> dict:
	"""What a letter head's template reads as `doc`: the record a workbook
	belongs to when the reader may open it, else the company and its
	address, so a head written for record prints still finds them."""
	from onedesk.one import control

	book = frappe.db.get_value(api.WORKBOOK, name, ["bound_doctype", "bound_name"], as_dict=True) if name else None
	if book and book.bound_doctype and frappe.has_permission(book.bound_doctype, "read", book.bound_name):
		return frappe.get_doc(book.bound_doctype, book.bound_name)
	company = control._company()
	address = control._company_address(company)
	return frappe._dict(
		doctype="", name="", company=company.name if company else "", company_address=address.name if address else ""
	)


def _letter_head(chosen: str | None = None, doc: dict | None = None) -> tuple[str, str]:
	"""A letter head's top and foot: the one chosen, else the default, else
	one drawn from the company when the workspace has none. `doc` is what
	its template reads."""
	from onedesk.one import letter_heads as drawing

	if chosen == NO_HEAD:
		return "", ""
	where = {"name": chosen} if chosen else {"is_default": 1}
	held = frappe.db.get_value("Letter Head", {**where, "disabled": 0}, ["content", "footer"], as_dict=True)
	if chosen and not held:
		frappe.throw(_("Letter head {0} does not exist.").format(chosen))
	if not held:
		return drawing.draw(None), drawing.draw_foot(None)

	def drawn(html: str | None) -> str:
		if not html:
			return ""
		try:
			return frappe.render_template(html, {"doc": doc if doc is not None else frappe._dict(), "letter_head": held})
		except Exception:
			return html

	return drawn(held.content), drawn(held.footer)


def page(
	title: str,
	sheets: list[dict],
	landscape: bool = False,
	fit: bool = True,
	gridlines: bool = True,
	letter_head: str | None = None,
	doc: dict | None = None,
) -> str:
	"""The whole print as HTML: the letter head's top, each sheet under its
	name, then the foot. `letter_head` is one by name, NO_HEAD, or None for
	the default; `doc` is what its template reads (_record)."""
	size = frappe.db.get_single_value("Print Settings", "pdf_page_size") or "A4"
	short, long = PAPER.get(size, PAPER["A4"])
	room = ((long if landscape else short) - 2 * MARGIN) * PX
	top, foot = _letter_head(letter_head, doc)
	named = len(sheets) > 1
	body = []
	for n, sheet in enumerate(sheets):
		drawn = _table(sheet, room, fit, gridlines)
		if not drawn:
			continue
		name = escape_html(str(sheet.get("name") or ""))
		body.append(
			f'<section{" class=next" if n and body else ""}>'
			f"{f'<h2>{name}</h2>' if named else ''}{drawn}</section>"
		)
	if not body:
		body.append(f'<p class="empty">{escape_html(_("This sheet is empty."))}</p>')
	return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{escape_html(title)}</title>
<style>
body{{margin:0;font-family:{FONT};font-size:{FONT_SIZE}px;color:#111827;-webkit-print-color-adjust:exact}}
.top{{margin-bottom:16px}}
.foot{{margin-top:24px}}
h2{{font-size:13px;font-weight:600;margin:0 0 8px}}
section.next{{page-break-before:always}}
table.sheet{{border-collapse:collapse;table-layout:fixed}}
table.sheet + table.sheet{{margin-top:0}}
thead{{display:table-header-group}}
tr{{page-break-inside:avoid}}
td{{padding:0 4px;overflow:hidden;white-space:nowrap;vertical-align:bottom;line-height:1.25}}
table.grid td{{border:1px solid {GRID}}}
td img{{display:block}}
.empty{{color:#6b7280}}
</style></head><body>
{f'<div class="top">{top}</div>' if top else ''}{''.join(body)}{f'<div class="foot">{foot}</div>' if foot else ''}
</body></html>"""


def _sheets(sheets) -> list[dict]:
	said = frappe.parse_json(sheets) if isinstance(sheets, str) else sheets
	if not isinstance(said, list) or not said:
		frappe.throw(_("Choose a sheet to print."))
	return [one for one in said[:MOST_SHEETS] if isinstance(one, dict)]


def _file_name(title: str, sheets: list[dict]) -> str:
	bare = re.sub(r"\.(xlsx|xlsm|xls|csv)$", "", title or "", flags=re.I).strip() or _("Workbook")
	if len(sheets) == 1 and sheets[0].get("name"):
		bare = f"{bare} - {sheets[0]['name']}"
	return re.sub(r'[\\/:*?"<>|]', " ", f"{bare}.pdf")


@frappe.whitelist(methods=["POST"])
def pdf(
	name: str,
	sheets: str,
	landscape: int = 0,
	fit: int = 1,
	gridlines: int = 1,
	letter_head: str | None = None,
	keep: str = "",
) -> dict | None:
	"""A workbook's sheets as a PDF. With no `keep` it is the answer; with
	"cloud" it is a file beside the workbook; with "record" it is attached
	to the record the workbook is bound to. `letter_head` as page() takes it."""
	from frappe.utils.pdf import get_pdf

	item = api._may(name, "read")
	if keep not in KEEP:
		frappe.throw(_("A PDF can only be saved to OneCloud or attached to the record."))
	title = item.get("file_name") or ""
	said = _sheets(sheets)
	html = page(title, said, bool(cint(landscape)), bool(cint(fit)), bool(cint(gridlines)), letter_head or None, _record(name))
	options = {"orientation": "Landscape" if cint(landscape) else "Portrait"}
	for side in ("top", "bottom", "left", "right"):
		options[f"margin-{side}"] = f"{MARGIN}mm"
	content = get_pdf(html, options)
	file_name = _file_name(title, said)
	if not keep:
		frappe.local.response.filename = file_name
		frappe.local.response.filecontent = content
		frappe.local.response.type = "pdf"
		return None
	return _keep(name, item, file_name, content, keep)


def _keep(name: str, item: dict, file_name: str, content: bytes, keep: str) -> dict:
	"""The PDF as a File: on the record the workbook belongs to, or beside it
	in its folder."""
	from onedesk.one_storage import api as cloud
	from onedesk.one_storage import namespace as ns

	fields = {"doctype": "File", "content": content, "is_private": 1}
	if keep == "record":
		book = frappe.db.get_value(api.WORKBOOK, name, ["bound_doctype", "bound_name"], as_dict=True)
		if not book or not book.bound_doctype:
			frappe.throw(_("This workbook is not linked to a record."))
		frappe.has_permission(book.bound_doctype, "write", book.bound_name, throw=True)
		where = ("record", book.bound_doctype, book.bound_name)
	elif item.get("attached_to_doctype"):
		frappe.has_permission(item["attached_to_doctype"], "write", item["attached_to_name"], throw=True)
		where = ("record", item["attached_to_doctype"], item["attached_to_name"])
	elif item.get("folder"):
		if not ns.may(ns.row(item["folder"]), "add"):
			frappe.throw(_("You can't add to this folder."), frappe.PermissionError)
		where = ("folder", item["folder"])
	else:
		frappe.throw(_("This workbook is not in a folder."))
	if where[0] == "record":
		taken = set(
			frappe.get_all("File", filters={"attached_to_doctype": where[1], "attached_to_name": where[2]}, pluck="file_name")
		)
		fields.update(attached_to_doctype=where[1], attached_to_name=where[2])
	else:
		taken = cloud._taken(where[1])
		fields["folder"] = where[1]
	fields["file_name"] = ns.unique_name(file_name, taken)
	doc = frappe.get_doc(fields)
	doc.flags.ignore_permissions = True
	doc.insert()
	return {**ns.node(ns.row(doc.name)), "file_url": doc.file_url, "where": list(where[1:])}

