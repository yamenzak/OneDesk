"""Every property frappe's print format builder sets, by where it lives, so
OneAI can set any of them by frappe's own name (ai.design_print_format).

Read from frappe's builder (public/js/print_format_builder: field_properties.js,
SectionPropertiesPanel.vue, TableFieldInspector.vue, BarcodeRows.vue and the
rest of the inspector) and checked against what its renderer reads
(templates/print_format/print_format.html, macros.html and macros/*): a
property the builder sets and the page never reads is left out, and so is one
the page reads that nothing sets. What each accepts is what the builder's own
control offers.

A value is checked here for its shape; a style for what it may load
(printing._style), and a condition for its grammar. frappe runs a condition in
its own safe_eval with the record and the print settings, as the builder's own
do.
"""

import re

import frappe
from frappe import _

ALIGN = ("left", "center", "right")

#: Where a condition may be written, and what frappe hands it.
CONDITIONS = ("visible_if", "row_condition", "column_condition")

#: A colour as the builder's colour control writes one, or one of frappe's own.
COLOUR = re.compile(
	r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})|var\(--[a-z]+-[0-9]{2,3}\)|transparent"
)

#: A width in pixels, as the builder's size control writes one.
PIXELS = re.compile(r"[0-9]{1,3}px")

#: Every block may carry these.
EVERY = {"custom_style": "css", "visible_if": "condition"}

SECTION = {
	"label": "text",
	"show_label": ("show", "hide"),
	"field_orientation": ("top", "left-right"),
	"justify": ("space-between", "space-evenly", "center", "right-end"),
	"gap": "int",
	"background": "colour",
	"radius": "int",
	"padding": "box",
	"margin": "box",
	"field_borders": "bool",
	"grid_borders": ("all", "rows", "columns"),
	"cell_padding": "int",
	"border_color": "colour",
	"keep_together": "bool",
	"page_break": "bool",
	**EVERY,
}

COLUMN = {"width": "int"}

FIELD = {
	"label": "text",
	"show_label": ("show", "hide", "inline"),
	"align": ALIGN,
	"width": "pixels",
	"label_justify": ("space-between", "space-evenly"),
	"label_gap": "int",
	"allow_page_break": "bool",
	"bold": "bool",
	"font_size": "int",
	"label_color": "colour",
	"value_color": "colour",
	"hide_colon": "bool",
	"show_empty": "bool",
	**EVERY,
}

TABLE = {
	"label": "text",
	"show_label": ("show", "hide"),
	"table_style": ("lined", "striped", "plain"),
	"table_bordered": "bool",
	"table_header": ("styled", "plain", "none"),
	"table_cell_padding": "int",
	"table_radius": "int",
	"table_min_height": "int",
	"table_header_bg": "colour",
	"table_border_color": "colour",
	"row_condition": "condition",
	**EVERY,
}

TABLE_COLUMN = {
	"label": "text",
	"width": "int",
	"merged_fields": "merged",
	"merge_direction": ("vertical", "horizontal"),
	"image_size": "int",
	"column_condition": "condition",
}

#: The builder's own blocks, by fieldtype.
BLOCKS = {
	"HTML": dict(EVERY),
	"Static Text": {"bold": "bool", "font_size": "int", "align": ALIGN, **EVERY},
	"Spacer": {"height": "int", **EVERY},
	"Divider": dict(EVERY),
	"Image": {"width": "pixels", "align": ALIGN, **EVERY},
	"Barcode": {
		"barcode_value": "text",
		"barcode_format": ("CODE128", "CODE39", "QR"),
		"show_text": "bool",
		"width": "pixels",
		"align": ALIGN,
		**EVERY,
	},
	"Linked Field": {key: value for key, value in FIELD.items() if key not in ("label_justify", "label_gap")},
	"Repeater": {
		"label": "text",
		"show_label": ("show", "hide"),
		"repeater_columns": "repeater",
		"row_condition": "condition",
		"custom_style": "css",
	},
}

#: The format's own settings the builder sets (Print Format's fields).
PAGE = {
	"font_size": "int",
	"margin_top": "number",
	"margin_bottom": "number",
	"margin_left": "number",
	"margin_right": "number",
	"show_label_colon": "bool",
	"label_color": "hex",
	"value_color": "hex",
}

#: How a merged line in a table cell reads.
MERGED_STYLES = ("primary", "secondary", "mono-sm", "muted-sm")


def taken(given: dict, allowed: dict, where: str, ours=()) -> dict:
	"""The properties of `allowed` in `given`, each checked, by frappe's names.
	A key that is neither one of them nor one of `ours` (the shorter words a
	model may write instead) is refused with the list, so it is mended."""
	out = {}
	for key, value in given.items():
		if key in ours:
			continue
		if key not in allowed:
			frappe.throw(
				_("{0} has no property {1}; it takes {2}.").format(where, key, ", ".join(sorted(allowed)))
			)
		if value is None or value == "":
			continue
		out[key] = _value(key, value, allowed[key], where)
	return out


def stored(block: dict, allowed: dict, left=()) -> dict:
	"""The properties a stored block carries, as a model writes them back: the
	inverse of taken, less what `left` already says another way."""
	return {
		key: block[key]
		for key in allowed
		if key in block and key not in left and block[key] not in (None, "")
	}


def _value(key: str, value, kind, where: str):
	wrong = lambda wants: frappe.throw(_("{0}: {1} is {2}.").format(where, key, wants))  # noqa: E731
	if isinstance(kind, tuple):
		if value not in kind:
			wrong(_("one of {0}").format(", ".join(kind)))
		return value
	if kind == "text":
		return str(value)
	if kind == "bool":
		return 1 if value in (True, 1, "1", "true", "yes") else 0
	if kind in ("int", "number"):
		try:
			number = float(str(value).strip().rstrip("px").strip())
		except ValueError:
			wrong(_("a number"))
		if number < 0 or number > 2000:
			wrong(_("a number from 0 to 2000"))
		return int(number) if kind == "int" else number
	if kind == "pixels":
		said = f"{value}px" if isinstance(value, int | float) else str(value).strip()
		if not PIXELS.fullmatch(said):
			wrong(_("a width in pixels, such as 120px"))
		return said
	if kind == "colour":
		if not COLOUR.fullmatch(str(value).strip()):
			wrong(_("a colour such as #0f766e or var(--gray-100)"))
		return str(value).strip()
	if kind == "hex":
		if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(value).strip()):
			wrong(_("a colour such as #0f766e"))
		return str(value).strip()
	if kind == "css":
		from onedesk.one import printing

		printing._style(str(value), where)
		return str(value)
	if kind == "condition":
		try:
			compile(str(value), key, "eval")
		except SyntaxError:
			wrong(_("a Python expression of doc (and row, for rows), such as doc.discount_amount > 0"))
		return str(value)
	if kind == "box":
		if not isinstance(value, dict) or set(value) - {"top", "right", "bottom", "left"}:
			wrong(_("{top, right, bottom, left} in pixels"))
		return {side: _value(key, px, "int", where) for side, px in value.items()}
	if kind == "merged":
		if not isinstance(value, list):
			wrong(_("a list of {fieldname, style}"))
		return [
			{
				"fieldname": str(one.get("fieldname") or one.get("field") or ""),
				"style": _value("style", one.get("style") or "muted-sm", MERGED_STYLES, where),
			}
			for one in value
			if isinstance(one, dict)
		]
	if kind == "repeater":
		if not isinstance(value, list):
			wrong(_("a list of columns, each {template, width, align}"))
		columns = []
		for one in value:
			template = [
				{"t": "f" if part.get("t") == "f" else "s", "v": str(part.get("v") or "")}
				for part in (one.get("template") or [])
				if isinstance(part, dict)
			]
			column = {"template": template}
			if one.get("width"):
				column["width"] = _value("width", one["width"], "int", where)
			if one.get("align"):
				column["align"] = _value("align", one["align"], ALIGN, where)
			if one.get("color"):
				column["color"] = _value("color", one["color"], "hex", where)
			columns.append(column)
		return columns
	return value


def described() -> str:
	"""The properties, for LAYOUT_HELP: where each lives and what it takes."""

	def said(allowed: dict) -> str:
		return ", ".join(
			f"{key} ({'|'.join(kind)})" if isinstance(kind, tuple) else f"{key} ({kind})"
			for key, kind in allowed.items()
		)

	return (
		f"A section may also take {said(SECTION)}. A column: {said(COLUMN)}. A field: {said(FIELD)}. A "
		f"table: {said(TABLE)}; each of its columns, written as {{field, ...}}: {said(TABLE_COLUMN)}, "
		f"merged_fields being [{{fieldname, style: {'|'.join(MERGED_STYLES)}}}] of the row's fields printed "
		"under the column's own. "
		+ " ".join(f"A {kind} block: {said(allowed)}." for kind, allowed in BLOCKS.items() if allowed)
		+ f" The page: {said(PAGE)}. A condition is a Python expression of doc (and row, in row_condition), "
		"run by frappe with nothing else in reach; box is {top, right, bottom, left} in pixels."
	)
