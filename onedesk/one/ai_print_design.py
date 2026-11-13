"""OneAI designs a print format (one/agent.py lists these tools):
`print_layout` reads a kind of record's starting layout, and
`design_print_format` writes one as a card. The rest compiles the layout a
model writes (LAYOUT_HELP) into the blocks frappe's print format builder
stores, checking each, and is not OneAI's own."""

import json
import re
from typing import Annotated

import frappe
from frappe import _

LAYOUT_HELP = (
	"sections is a list of sections, top to bottom. A section is a list of columns side by side, or "
	"{label, columns, keep_together, labels_beside} (label prints above it; keep_together keeps it on one "
	"page; labels_beside prints every field's label on its line, beside the value, as totals read). A column "
	"is a list of blocks, top to bottom, or {width, blocks} to give it its share of the section (widths are "
	"shares, such as 55 and 45). A block is: a fieldname of the record, printed as its label above its "
	"value; or {field, label, show_label: false|'inline', align: left|center|right, bold, show_empty, "
	"spread} for one printed another way (spread, in a labels_beside section, puts the label at the "
	"column's left edge and the value at its right); '---' for a line; {table: fieldname, columns: "
	"['item_name:45', 'qty:15', 'rate:20:Price', 'amount:20'], bordered, striped, show_label} for a table, "
	"lined between rows unless bordered (boxed) or striped, its label printed above only with show_label, "
	"each column a field of its rows with its share of the width (together at most 100) and, if it should "
	"read differently, its heading; {text: '...', align, bold} for fixed words; {space: 12} for room; "
	"{barcode: fieldname or '' with value, format: QR|CODE128|CODE39}; {image: url} for a file of this "
	"workspace; {linked: 'customer.customer_group'} for a field of the record a link field points at; "
	"{repeater: 'items', repeater_columns: [{template: [{t: 'f', v: 'item_name'}, {t: 's', v: ' x '}], "
	"width, align}]} for a table of rows written your own way; {divider: true}; or {html: '...'}. "
	"An empty column is []. heading is the title at the top in the same HTML, the standard one when left out. "
	"An html block or heading is Jinja over this one record and nothing else: {{ doc.fieldname }}, "
	"{{ doc.get('fieldname') }}, {{ doc.get_formatted('grand_total') }} (a value as the form shows it, "
	"with its currency), {% for row in doc.items %}{{ row.item_name }} {{ row.get_formatted('amount') "
	"}}{% endfor %} with loop.index, loop.first and loop.last, {% if %}/{% elif %}/{% else %}, {% set x = "
	"... %}, arithmetic and comparisons, _('text') to translate, the tests defined, undefined, none, number, string, "
	"odd, even, divisibleby, eq, ne, lt, gt, le, ge and in, and only the filters abs, capitalize, center, "
	"count, default, escape, first, float, format, int, join, last, length, lower, replace, reverse, "
	"round, sort, string, striptags, sum, title, trim, truncate, upper and wordcount. Nothing else is "
	"there: no frappe.db, get_all or other frappe.* helpers, no other record, no macros, includes or imports, no "
	"|safe, and no names that start with _; values are escaped, and scripts, forms and outside pictures "
	"are taken out. For a value from another record, print the field that links to it. How it should "
	"look: start from print_layout's starting_layout (or the format being changed) and change only what "
	"was asked. Unless they ask for a look of their own, it prints in the house style, the standard print "
	"style spaced and toned as One draws a page, so leave css out. When they do ask for a look (a "
	"colour, a font, a feel), write it as css over the print classes (.print-format-doc, .print-heading, "
	".section, .section-label, .field, .field .label, .field .value, .child-table .table th and td, "
	"[data-fieldname=...]) and it replaces the house style; with house_style true it is added over the "
	"house style instead, for a change to it. Their taste wins over the house's. The party and its "
	"address go on the left and the dates and references on the right; the items are one table, the "
	"description widest and the figures narrower; the totals sit under it on the right, in a "
	"labels_beside section with spread fields, and the amount in words on the left; terms and notes come "
	"last, each in a labelled section. The letter head already prints the company, so the body does not "
	"repeat it. A field the standard formats leave off the page says not printed; print it only when "
	"asked. Build it in this order, so the person can go on changing it in the builder: first the "
	"builder's own blocks, which cover most of any page; then, for a part they cannot draw (a stamp, a "
	"grid of terms, a figure worked out from the rows), one html block in its place among them; and "
	"only for a page designed from end to end, one html block across the whole body, with css. Never "
	"html for what a block already prints. In an html block the record's own number is doc.name, never "
	"its naming_series, and a figure, a date or a quantity is printed through get_formatted, never as "
	"the raw value."
)


def _how() -> str:
	"""LAYOUT_HELP, with every property of frappe's builder a block, a table, a
	section or the page may take by its own name, and the house's parts for
	an html block."""
	from onedesk.one_studio import print_props, print_recipes

	return (
		f"{LAYOUT_HELP} {print_props.described()} Any of these may be set on the block, section, column or "
		"table column they belong to, beside the shorter words above; the print format builder shows every one "
		"of them, so the person can go on changing them there. Whatever a property sets (a table's "
		"header colour is table_header_bg, a field's colour value_color, a section's background "
		"background) is set by the property, never by css, which the standard print style overrides. "
		"An html block in the house style is "
		f"built of the house's own classes and nothing else: {print_recipes.HOUSE_PARTS}. A look of "
		"their own writes its own classes in css instead."
	)


FIELD_OPTIONS = ("label", "show_label", "align", "bold", "show_empty", "spread")
ALIGN = ("left", "center", "right")

SHORT = {"field", "fieldname", "table", "columns", "bordered", "striped", "html", "text", "space", "image"}
SHORT |= {"barcode", "format", "spread", "linked", "repeater", "divider", "value"}

NOT_A_BLOCK = (
	"A block is a fieldname, '---', or one of table, text, space, barcode, image, linked, repeater, divider "
	"or html."
)


def _block(one) -> dict:
	"""One block as a model writes it, as the builder stores it: the shorter
	words below, and any of frappe's own properties of that kind of block by
	their own names (print_props), each checked."""
	from onedesk.one_studio import print_props

	if isinstance(one, str):
		return {"fieldtype": "Divider"} if one.strip("- ") == "" else {"fieldname": one.strip()}
	if not isinstance(one, dict):
		frappe.throw(_(NOT_A_BLOCK))
	if one.get("columns") and not one.get("table") and (one.get("field") or one.get("fieldname")):
		one = {**one, "table": one.get("field") or one.get("fieldname")}
	if one.get("columns") and not one.get("table"):
		frappe.throw(
			_("A table block names its table: {table: 'items', columns: ['item_name:45', 'qty:15']}.")
		)
	where = str(one.get("table") or one.get("field") or one.get("fieldname") or "")
	if one.get("table"):
		columns = []
		for column in one.get("columns") or []:
			fieldname, _sep, rest = _column(column).partition(":")
			width, _sep, label = rest.partition(":")
			columns.append(
				{
					"fieldname": fieldname.strip(),
					**({"width": _share(width)} if _share(width) else {}),
					**({"label": label.strip()} if label.strip() else {}),
					**(
						print_props.taken(
							column, print_props.TABLE_COLUMN, f"{where}.{fieldname.strip()}", ours=SHORT
						)
						if isinstance(column, dict)
						else {}
					),
				}
			)
		if not columns:
			frappe.throw(_("The table {0} needs its columns.").format(one["table"]))
		return {
			"fieldname": one["table"],
			"table_columns": columns,
			**({} if one.get("show_label") else {"show_label": "hide"}),
			"table_bordered": 1 if one.get("bordered") else 0,
			**({"table_style": "striped"} if one.get("striped") else {}),
			**print_props.taken(
				{
					key: value
					for key, value in one.items()
					if key != "show_label" or value in ("show", "hide")
				},
				print_props.TABLE,
				where,
				ours=SHORT,
			),
		}
	own = lambda kind: print_props.taken(one, print_props.BLOCKS[kind], kind, ours=SHORT)  # noqa: E731
	if "html" in one:
		return {"fieldtype": "HTML", "html": str(one["html"]), **own("HTML")}
	if "text" in one:
		return {"fieldtype": "Static Text", "text": str(one["text"]), **own("Static Text")}
	if "space" in one:
		return {"fieldtype": "Spacer", "height": frappe.utils.cint(one["space"]) or 10, **own("Spacer")}
	if one.get("divider"):
		return {"fieldtype": "Divider", **own("Divider")}
	if "image" in one:
		return {"fieldtype": "Image", "image_url": str(one["image"]), **own("Image")}
	if "barcode" in one:
		kind = str(one.get("format") or one.get("barcode_format") or "CODE128").upper()
		return {
			"fieldtype": "Barcode",
			"barcode_field": str(one.get("barcode") or ""),
			**({"barcode_value": str(one["value"])} if one.get("value") else {}),
			**own("Barcode"),
			"barcode_format": print_props.taken(
				{"barcode_format": kind}, print_props.BLOCKS["Barcode"], "barcode"
			)["barcode_format"],
		}
	if one.get("linked"):
		return {"fieldtype": "Linked Field", "link_path": str(one["linked"]), **own("Linked Field")}
	if one.get("repeater"):
		return {"fieldtype": "Repeater", "source": str(one["repeater"]), **own("Repeater")}
	fieldname = one.get("field") or one.get("fieldname")
	if fieldname:
		name = str(fieldname).strip()
		block = {
			"fieldname": name,
			**print_props.taken(
				{key: value for key, value in one.items() if key not in ("show_label", "spread")},
				print_props.FIELD,
				name,
				ours=SHORT,
			),
		}
		if one.get("spread"):
			block["label_justify"] = "space-between"
		said = one.get("show_label")
		if said in ("inline", "show"):
			block["show_label"] = said
		elif said in (False, 0, "hide", "false"):
			block["show_label"] = "hide"
		return block
	frappe.throw(_(NOT_A_BLOCK))


def _parsed(text: str):
	"""Sections written as JSON text, or as the Python a model sometimes writes
	instead: True, False and None outside a string are JSON's words for them."""
	try:
		return json.loads(text)
	except ValueError:
		pass
	loose = json.JSONDecoder(strict=False)
	text = re.sub(r"\\(.)", lambda m: m[0] if m[1] in '"\\/bfnrtu' else "\\\\" + m[1], text, flags=re.S)
	try:
		return loose.raw_decode(text.strip())[0]
	except ValueError:
		pass
	parts = re.split(r'("(?:[^"\\]|\\.)*")', text)
	mended = "".join(
		part
		if n % 2
		else re.sub(r"\bTrue\b", "true", re.sub(r"\bFalse\b", "false", re.sub(r"\bNone\b", "null", part)))
		for n, part in enumerate(parts)
	)
	try:
		return loose.raw_decode(mended.strip())[0]
	except ValueError as e:
		frappe.throw(_("sections is not JSON: {0}.").format(str(e)))


def _share(value) -> int:
	"""A width as a share of the page: 45, "45" and "45%" alike."""
	return frappe.utils.cint(str(value or "").strip().rstrip("%").strip())


def _column(column) -> str:
	"""A table column as 'fieldname:width:Heading', however it was written:
	{field: 'qty', width: 15, label: 'Qty'} is the same column spelled out."""
	if not isinstance(column, dict):
		return str(column)
	fieldname, _sep, rest = str(column.get("field") or column.get("fieldname") or "").partition(":")
	width, _sep, label = rest.partition(":")
	width = str(_share(column.get("width") or width) or "")
	label = str(column.get("label") or label)
	return ":".join((fieldname, width, label)).rstrip(":")


def _linked(meta, path: str) -> list[str]:
	"""What is wrong with a linked field's path: one hop, a Link of this kind
	to a field of the kind it links to."""
	link, _sep, target = path.partition(".")
	field = meta.get_field(link)
	if not field or field.fieldtype != "Link" or not target:
		return [
			_("{0} is not a link field and one of its fields, such as customer.customer_group").format(path)
		]
	if not frappe.get_meta(field.options).has_field(target):
		return [_("{0} has no field {1}").format(field.options, target)]
	return []


def _repeated(meta, block: dict) -> list[str]:
	"""What is wrong with a repeater: its source a table of this kind, and every
	field its columns print a field of that table's rows."""
	source = meta.get_field(block.get("source"))
	if not source or source.fieldtype not in frappe.model.table_fields:
		return [_("{0} is not a table to repeat").format(block.get("source"))]
	rows = frappe.get_meta(source.options)
	return [
		_("{0} has no field {1}").format(source.options, part["v"])
		for column in block.get("repeater_columns") or []
		for part in column.get("template") or []
		if part.get("t") == "f" and not rows.has_field(part["v"])
	]


def _paired(column: list) -> list:
	"""A column as a model meant it: a table's fieldname written just before
	its columns, as "items", {"columns": [...]}, is that table once."""
	out = []
	for one in column:
		before = out[-1] if out else None
		if isinstance(one, dict) and one.get("columns") and isinstance(before, str):
			if one.get("table") in (None, before.strip()):
				out[-1] = {**one, "table": before.strip()}
				continue
		out.append(one)
	return out


def _built(sections, heading: str | None, doctype: str | None = None) -> dict:
	"""The builder's layout from sections as a model writes them, checked for
	what would print badly: an empty section, a table without columns or wider
	than the page, a field that is not a table given columns, a barcode of a
	field the kind does not have."""
	from frappe.printing.doctype.print_format.classic_converter import DEFAULT_PRINT_HEADING

	from onedesk.one_studio import print_props, print_recipes

	if isinstance(sections, str):
		sections = _parsed(sections)
	if not isinstance(sections, list) or not sections:
		frappe.throw(_("sections is a list of sections, each a list of columns."))
	meta = frappe.get_meta(doctype) if doctype else None
	problems = []
	built = []
	for n, section in enumerate(sections, 1):
		label, keep, beside, props = "", False, False, {}
		if isinstance(section, dict):
			label, keep, beside = (
				section.get("label") or "",
				section.get("keep_together"),
				section.get("labels_beside"),
			)
			props = print_props.taken(
				section,
				print_props.SECTION,
				_("section {0}").format(label or n),
				ours={"label", "columns", "keep_together", "labels_beside"},
			)
			section = section.get("columns") or []
		if not isinstance(section, list):
			frappe.throw(_("A section is a list of columns, each a list of blocks."))
		widths = []
		columns = []
		for column in section:
			if isinstance(column, dict) and "blocks" in column:
				print_props.taken(column, print_props.COLUMN, _("a column"), ours={"blocks"})
				widths.append(_share(column.get("width")))
				column = column["blocks"]
			else:
				widths.append(0)
			columns.append(column if isinstance(column, list) else [column])
		blocks = [[_block(b) for b in _paired(c)] for c in columns]
		if not any(blocks):
			problems.append(_("section {0} is empty").format(label or n))
		for column in blocks:
			for block in column:
				if meta and block.get("table_columns"):
					field = meta.get_field(block["fieldname"])
					if field and field.fieldtype not in frappe.model.table_fields:
						problems.append(_("{0} is not a table").format(block["fieldname"]))
					width = sum(frappe.utils.cint(c.get("width")) for c in block["table_columns"])
					if width > 100:
						problems.append(
							_("the columns of {0} come to {1}%, more than the page").format(
								block["fieldname"], width
							)
						)
				elif meta and block.get("fieldname") and not block.get("fieldtype"):
					field = meta.get_field(block["fieldname"])
					if field and field.fieldtype in frappe.model.table_fields:
						problems.append(_("{0} is a table: give it its columns").format(block["fieldname"]))
				if (
					meta
					and block.get("fieldtype") == "Barcode"
					and block.get("barcode_field") not in ("", "name")
					and not meta.has_field(block["barcode_field"])
				):
					problems.append(_("there is no field {0} for the barcode").format(block["barcode_field"]))
				if meta and block.get("fieldtype") == "Linked Field":
					problems.extend(_linked(meta, block.get("link_path") or ""))
				if meta and block.get("fieldtype") == "Repeater":
					problems.extend(_repeated(meta, block))
		built.append(
			{
				"label": label,
				**({"keep_together": 1} if keep else {}),
				**({"field_orientation": "left-right"} if beside else {}),
				**props,
				"columns": [
					{"label": "", "fields": column, **({"width": width} if width else {})}
					for column, width in zip(blocks, widths, strict=True)
				],
			}
		)
	if doctype:
		printed = {
			block.get("fieldname") for section in built for c in section["columns"] for block in c["fields"]
		}
		written = " ".join(
			str(block.get("html") or block.get("text") or "")
			for section in built
			for c in section["columns"]
			for block in c["fields"]
		) + str(heading or "")
		missing = [
			one for one in print_recipes.essentials(doctype) if one not in printed and one not in written
		]
		if missing:
			problems.append(_("it does not print {0}").format(", ".join(missing)))
	if problems:
		frappe.throw(_("The layout would print badly: {0}.").format("; ".join(problems)))
	top = heading or DEFAULT_PRINT_HEADING
	return {
		"header": {"columns": [{"label": "", "fields": [{"fieldtype": "HTML", "label": "", "html": top}]}]},
		"sections": built,
		"footer": {"columns": [{"label": "", "fields": []}]},
	}


def _written(layout, meta=None) -> dict | None:
	"""A builder layout as a model writes one (_built's inverse): its sections,
	and its heading when it is not frappe's own."""
	from frappe.printing.doctype.print_format.classic_converter import DEFAULT_PRINT_HEADING

	if not isinstance(layout, dict):
		return None

	from onedesk.one_studio import print_props

	def block(one: dict):
		kind = one.get("fieldtype")
		if one.get("table_columns"):
			rows = frappe.get_meta(one["options"]) if one.get("options") else None

			def column(c):
				said = [c.get("fieldname"), str(c.get("width") or "")]
				own = rows.get_field(c.get("fieldname")) if rows else None
				if c.get("label") and own and c["label"] != own.label:
					said.append(c["label"])
				written = ":".join(said).rstrip(":")
				more = print_props.stored(c, print_props.TABLE_COLUMN, left=("label", "width"))
				return {"field": written, **more} if more else written

			return {
				"table": one.get("fieldname"),
				"columns": [column(c) for c in one["table_columns"]],
				**({"bordered": True} if one.get("table_bordered") not in (0, False) else {}),
				**({"striped": True} if one.get("table_style") == "striped" else {}),
				**({"show_label": True} if one.get("show_label") not in (None, "hide") else {}),
				**print_props.stored(
					one, print_props.TABLE, left=("label", "show_label", "table_bordered", "table_style")
				),
			}
		more = print_props.stored(one, print_props.BLOCKS.get(kind) or {})
		if kind == "HTML":
			return {"html": one.get("html") or "", **more}
		if kind == "Static Text":
			return {"text": one.get("text") or "", **more}
		if kind == "Divider":
			return {"divider": True, **more} if more else "---"
		if kind == "Spacer":
			return {
				"space": one.get("height") or 10,
				**print_props.stored(one, print_props.BLOCKS[kind], ("height",)),
			}
		if kind == "Image":
			return {"image": one.get("image_url") or "", **more}
		if kind == "Barcode":
			return {
				"barcode": one.get("barcode_field") or "",
				"format": one.get("barcode_format") or "CODE128",
				**({"value": one["barcode_value"]} if one.get("barcode_value") else {}),
				**print_props.stored(one, print_props.BLOCKS[kind], ("barcode_format", "barcode_value")),
			}
		if kind == "Linked Field":
			return {"linked": one.get("link_path") or "", **more}
		if kind == "Repeater":
			return {"repeater": one.get("source") or "", **more}
		own = meta.get_field(one.get("fieldname")) if meta and one.get("fieldname") else None
		options = print_props.stored(one, print_props.FIELD, left=("label", "show_label", "label_justify"))
		if one.get("show_label") == "hide":
			options["show_label"] = False
		elif one.get("show_label") == "inline":
			options["show_label"] = "inline"
		if own and one.get("label") and one["label"] != own.label:
			options["label"] = one["label"]
		if one.get("label_justify") == "space-between":
			options["spread"] = True
		elif one.get("label_justify"):
			options["label_justify"] = one["label_justify"]
		return {"field": one.get("fieldname"), **options} if options else one.get("fieldname")

	sections = []
	for section in layout.get("sections") or []:
		columns = []
		for column in section.get("columns") or []:
			said = [
				b for b in (block(one) for one in column.get("fields") or [] if isinstance(one, dict)) if b
			]
			columns.append({"width": column["width"], "blocks": said} if column.get("width") else said)
		if any(one.get("blocks") if isinstance(one, dict) else one for one in columns):
			beside = section.get("field_orientation") == "left-right"
			more = print_props.stored(
				section, print_props.SECTION, left=("label", "keep_together", "field_orientation")
			)
			if section.get("label") or section.get("keep_together") or beside or more:
				sections.append(
					{
						"label": section.get("label") or "",
						"columns": columns,
						**({"keep_together": True} if section.get("keep_together") else {}),
						**({"labels_beside": True} if beside else {}),
						**more,
					}
				)
			else:
				sections.append(columns)
	top = [
		one.get("html")
		for column in (layout.get("header") or {}).get("columns") or []
		for one in column.get("fields") or []
		if one.get("fieldtype") == "HTML"
	]
	heading = top[0] if top and top[0] != DEFAULT_PRINT_HEADING else None
	return {"sections": sections, **({"heading": heading} if heading else {})}


def _laid_out(doctype: str, sections, heading: str | None, existing) -> dict:
	"""The layout a design prints: the sections given; without them, a changed
	format's own layout as the builder left it (a restyle changes only its
	css), or a new one's starting layout."""
	from onedesk.one_studio import print_recipes

	if sections:
		return _built(sections, heading, doctype)
	if existing and existing.format_data:
		if not heading:
			return json.loads(existing.format_data)
		written = _written(json.loads(existing.format_data), frappe.get_meta(doctype))
		return _built(written["sections"], heading, doctype)
	return _built(print_recipes.starting_layout(doctype), heading, doctype)


def _redo(doctype: str, error: str) -> dict:
	"""A design that did not hold, handed back with what to start again from,
	so a model that skipped print_layout, or wrote a block wrong, mends it in
	the next round rather than telling the person what went wrong inside."""
	from onedesk.one_studio import print_recipes

	try:
		start = print_recipes.starting_layout(doctype)
	except (frappe.ValidationError, frappe.PermissionError, frappe.DoesNotExistError):
		frappe.clear_last_message()
		start = None
	return {
		"error": error,
		"mend": "design_print_format",
		"next": "Mend the sections and call design_print_format again; this is for you, not for them. Start "
		"from starting_layout and change only what they asked, or leave sections out for the starting "
		"layout as it is. When they asked for a look rather than a layout, leave sections out and send only "
		"css (over the classes css names) and font.",
		**({"starting_layout": start} if start else {}),
		"how": _how(),
	}


def _styled(css: str | None, house: bool | None, before: str | None) -> str | None:
	"""The css a format prints with: the house style unless a look was asked
	for, that look alone, or the house style with it over the top. A changed
	format left without css keeps its own."""
	from onedesk.one_studio.print_recipes import HOUSE_CSS

	css = (css or "").strip()
	if house:
		return f"{HOUSE_CSS}\n{css}" if css else HOUSE_CSS
	if css:
		return css
	return before if before is not None else HOUSE_CSS


def _style_of(css: str | None) -> dict:
	"""A format's css as print_layout tells it: whether it is the house style,
	and whatever it carries beyond it."""
	from onedesk.one_studio.print_recipes import HOUSE_CSS

	css = css or ""
	if css.startswith(HOUSE_CSS):
		return {"house_style": True, "css": css[len(HOUSE_CSS) :].strip() or None}
	return {"house_style": False, "css": css or None}


def print_layout(
	doctype: Annotated[str, "The kind of record, such as Sales Invoice."],
	print_format: Annotated[str, "A format of that kind to start from; its default when left out."]
	| None = None,
) -> dict:
	"""A kind of record's fields, the layout a format of it starts from, and one
	of its builder formats as sections, the way design_print_format takes them:
	read it before designing one. Workspace administrators only."""
	from onedesk.one import roles
	from onedesk.one_ai import kind
	from onedesk.one_studio import print_recipes, printing

	if not roles.administers():
		return {"error": "Only a workspace administrator designs how documents are printed."}
	try:
		printing._doctype(doctype)
		meta = frappe.get_meta(doctype)
		name = print_format or next(iter(printing.starts(doctype)), frappe._dict()).get("name")
		held = (
			frappe.db.get_value(
				"Print Format", name, ["doc_type", "format_data", "css", "page_number", "font"], as_dict=True
			)
			if name
			else None
		)
		if held and held.doc_type != doctype:
			return {"error": f"{name} is not a format of {doctype}."}
		return {
			"doctype": doctype,
			"fields": kind.fields(meta, printing=True),
			"starting_layout": print_recipes.starting_layout(doctype),
			"format": name,
			"written": _written(json.loads(held.format_data), meta) if held and held.format_data else None,
			**(_style_of(held.css) if held else {"house_style": True, "css": None}),
			"page_number": held.page_number if held else None,
			"font": held.font if held else None,
			"how": _how(),
		}
	except (frappe.ValidationError, frappe.PermissionError) as e:
		frappe.clear_last_message()
		return {"error": str(e)}


def design_print_format(
	doctype: Annotated[str, "The kind of record the format prints, such as Sales Invoice."],
	name: Annotated[str, "The format's name: a new one, or one of the workspace's own formats to change."],
	sections: Annotated[
		str,
		"The sections as JSON text, top to bottom: each a list of columns, each a list of blocks, as "
		"print_layout's how says: its starting_layout with only what they asked changed. Leave out to "
		"print the starting layout as it is, which is what a plain request for a good format wants, or, "
		"changing a format, to keep its layout and change only its look.",
	]
	| None = None,
	heading: Annotated[
		str, "The title at the top, as an HTML template of the record; the standard one if left out."
	]
	| None = None,
	css: Annotated[
		str,
		"Leave out for the house style (a changed format keeps its own). Only for a look they asked for: "
		"css that replaces the house style, written over the print classes and nothing else: "
		".print-format-doc (the page), .print-heading h2 and .print-heading .sub-heading (the title), "
		".section, .section-label, .field .label, .field .value, .child-table .table th, .child-table "
		".table td, .child-table .table tr.even td (every other row), and .field[data-fieldname=grand_total] "
		"for one field. No imports or outside URLs; a typeface is font.",
	]
	| None = None,
	font: Annotated[
		str,
		"A Google Font the whole page prints in, by its name, such as Playfair Display or Lora, when they "
		"ask for a typeface; the standard Inter when left out.",
	]
	| None = None,
	page: Annotated[
		dict,
		"The page's own settings, when they ask: font_size (the body, in pixels), margin_top, "
		"margin_bottom, margin_left, margin_right (in millimetres), show_label_colon, label_color and "
		"value_color (#rrggbb). Leave out to keep them.",
	]
	| None = None,
	house_style: Annotated[
		bool,
		"True to print in the house style with css added over it, for a change to the house look rather "
		"than a look of their own.",
	]
	| None = None,
	page_number: Annotated[
		str,
		"Where the page number prints on every page: Hide, Top Left, Top Center, Top Right, Bottom Left, "
		"Bottom Center or Bottom Right. Leave out to keep the format's own.",
	]
	| None = None,
	letter_head: Annotated[str, "The letter head it prints with, if not the default."] | None = None,
	make_default: Annotated[bool, "True to make it the one this kind prints with."] | None = None,
	why: Annotated[str, "In a sentence, what the design is for."] | None = None,
) -> dict:
	"""Suggest a print format for any kind of record, as a card a workspace
	administrator approves: laid out as the print format builder lays one
	out, from sections of columns of blocks. Read print_layout first. It is
	checked as the builder's own save checks it; the card shows the page on
	the kind's latest record before it is approved, and the format then opens
	in the builder like any other. Workspace administrators only."""
	from onedesk.one import roles
	from onedesk.one_ai import proposals
	from onedesk.one_studio import printing

	if not roles.administers():
		return {"error": "Only a workspace administrator designs how documents are printed."}
	name = (name or "").strip()
	if not name:
		return {"error": "Give the format a name."}
	try:
		existing = frappe.db.get_value(
			"Print Format", name, ["standard", "doc_type", "css", "format_data"], as_dict=True
		)
		if existing and (existing.standard == "Yes" or existing.doc_type != doctype):
			return {"error": f"{name} is not a format of {doctype} this workspace made; choose another name."}
		doc = printing.format_doc(
			doctype,
			name,
			_laid_out(doctype, sections, heading, existing),
			_styled(css, house_style, (existing.css or "") if existing else None),
			letter_head,
			page_number,
			font,
			page,
		)
	except (frappe.ValidationError, frappe.PermissionError) as e:
		frappe.clear_last_message()
		return _redo(doctype, str(e))
	summary = [
		{"label": _("Changed Format") if existing else _("New Format"), "value": name},
		{"label": _("Sections"), "value": str(len(frappe.parse_json(doc.format_data).get("sections") or []))},
	]
	if make_default:
		summary.append({"label": _("Prints With"), "value": name})
	return {
		"proposal": proposals.propose(
			"Printing",
			doctype,
			changes={
				"state": printing.state(doctype, name),
				"format": {
					"doctype": doctype,
					"name": name,
					"format_data": doc.format_data,
					"css": doc.css,
					**({"page_number": doc.page_number} if page_number else {}),
					**({"font": doc.font} if font else {}),
					**({"page": page} if page else {}),
				},
				"default_format": name if make_default else None,
				"summary": summary,
			},
			why=why,
		),
		"state": "Proposed",
		"next": "Tell them See the Page on the card shows it on their latest record, and that once approved "
		"it opens in the print format builder from the record's Settings > Print Formats.",
	}




print_layout.action = design_print_format.action = "print_design"
