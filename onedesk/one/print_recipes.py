"""A kind of record's starting print layout, for OneAI to adjust rather than invent.

OneAI designs a print format as the builder lays one out (ai.design_print_format).
Left to itself, two requests for the same invoice came out as two different
pages. So print_layout offers a starting layout made from the kind's own fields,
in the order a reader looks for them, and OneAI changes only what was asked.
The look is frappe's own print style with HOUSE_CSS over it: the same page,
spaced and toned the way frappe-ui draws one, so it still reads like every
other format the workspace prints. A format made to a look somebody asked for
carries their css instead, never this one as well.

Two shapes cover what a workspace prints:

- a document of trade (an invoice, a quotation, an order, a delivery note, a
  bill): who it is for and where on the left, its dates and references on the
  right, the items as one table, the amount in words beside the totals, and the
  terms last;
- anything else: its main fields in two columns, each of its tables with the
  columns its list shows, and its long text last, each under its label.

Every layout is written as ai.LAYOUT_HELP describes: sections of columns of
blocks.
"""

import frappe
from frappe import _

#: The house finish over frappe's print style, in frappe's own classes and its
#: grey scale: labels small and muted, room between sections, tables lined
#: rather than boxed under a soft header, the totals as label and figure on one
#: line and the grand total set off above them. Sizes are em, as frappe's are.
HOUSE_CSS = """\
.print-format-doc { line-height: 1.5; }
.print-format-doc .document-header-content { margin: 1.25em 0 0.5em; }
.print-format-doc .print-heading { border-bottom: none; padding-bottom: 0; margin-bottom: 0.75em; }
.print-format-doc .print-heading h2 { font-size: 1.6em; font-weight: 600; letter-spacing: -0.01em; color: var(--gray-900); }
.print-format-doc .print-heading .sub-heading { display: block; font-size: 0.55em; font-weight: 400; letter-spacing: 0; color: var(--gray-600); margin-top: 0.25em; }
.print-format-doc .section + .section { margin-top: 1.5em; }
.print-format-doc .section-label { font-size: 0.9em; font-weight: 600; color: var(--gray-800); border-bottom: 1px solid var(--gray-200); padding-bottom: 0.4em; margin-bottom: 0.8em; }
.print-format-doc .field + .field { margin-top: 0.75em; }
.print-format-doc .field .label { font-size: 0.85em; color: var(--gray-600); margin-bottom: 0.15em; }
.print-format-doc .field.left-right + .field.left-right { margin-top: 0.35em; }
.print-format-doc .field.left-right .label, .print-format-doc .field.field-inline .label { font-size: 1em; color: var(--gray-600); }
.print-format-doc .child-table { --pfb-radius: 6px; --pfb-header-bg: var(--gray-100); margin-top: 0; }
.print-format-doc .child-table .table th { color: var(--gray-600); font-weight: 500; font-size: 0.85em; }
.print-format-doc .child-table--lined .table td { border-bottom-color: var(--gray-200) !important; }
.print-format-doc .child-table .table td { padding-top: 0.6em; padding-bottom: 0.6em; }
.print-format-doc .field[data-fieldname="grand_total"] { font-weight: 600; color: var(--gray-900); border-top: 1px solid var(--gray-300); padding-top: 0.5em; margin-top: 0.5em; }
.print-format-doc .field[data-fieldname="rounded_total"] { font-weight: 600; }
.print-format-doc .field[data-fieldname="grand_total"] .label, .print-format-doc .field[data-fieldname="rounded_total"] .label { color: var(--gray-900); }
.print-format-doc .one-label { font-size: 0.85em; color: var(--gray-600); margin-bottom: 0.15em; }
.print-format-doc .one-muted { font-size: 0.85em; color: var(--gray-600); }
.print-format-doc .one-value { color: var(--gray-900); }
.print-format-doc .one-figure { font-size: 1.75em; font-weight: 600; letter-spacing: -0.01em; line-height: 1.2; color: var(--gray-900); }
.print-format-doc .one-title { font-size: 1.15em; font-weight: 600; color: var(--gray-900); }
.print-format-doc .one-card { border: 1px solid var(--gray-200); border-radius: var(--radius, 8px); padding: 0.9em 1em; }
.print-format-doc .one-note { background: var(--gray-50); border-radius: var(--radius, 8px); padding: 0.75em 1em; color: var(--gray-700); }
.print-format-doc .one-grid { display: flex; gap: 1.25em; }
.print-format-doc .one-grid > * { flex: 1 1 0; min-width: 0; }
.print-format-doc .one-kv { display: flex; justify-content: space-between; gap: 1em; padding: 0.35em 0; }
.print-format-doc .one-kv + .one-kv { border-top: 1px solid var(--gray-100); }
.print-format-doc .one-kv > :first-child { color: var(--gray-600); }
.print-format-doc .one-rule { border-top: 1px solid var(--gray-200); margin: 1em 0; }
.print-format-doc .one-badge { display: inline-block; padding: 0.15em 0.6em; border-radius: 9999px; font-size: 0.8em; font-weight: 500; background: var(--gray-100); color: var(--gray-700); }
.print-format-doc .one-badge--green { background: var(--green-100); color: var(--green-700); }
.print-format-doc .one-badge--red { background: var(--red-100); color: var(--red-700); }
.print-format-doc .one-badge--orange { background: var(--orange-100); color: var(--orange-700); }
.print-format-doc .one-badge--blue { background: var(--blue-100); color: var(--blue-700); }
.print-format-doc .one-stamp { display: inline-block; border: 0.15em solid currentColor; border-radius: 0.3em; padding: 0.15em 0.6em; font-size: 1.6em; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; transform: rotate(-8deg); color: var(--red-600); opacity: 0.85; }
.print-format-doc .one-stamp--green { color: var(--green-600); }
.print-format-doc .one-table { width: 100%; border-collapse: separate; border-spacing: 0; font-size: 0.9em; }
.print-format-doc .one-table th { background: var(--gray-100); color: var(--gray-600); font-weight: 500; font-size: 0.85em; text-align: left; padding: 0.5em 0.65em; }
.print-format-doc .one-table th:first-child { border-radius: 6px 0 0 6px; }
.print-format-doc .one-table th:last-child { border-radius: 0 6px 6px 0; }
.print-format-doc .one-table td { padding: 0.6em 0.65em; border-bottom: 1px solid var(--gray-200); vertical-align: top; }
.print-format-doc .one-table tr:last-child td { border-bottom: none; }
.print-format-doc .one-num, .print-format-doc .one-table .one-num { text-align: right; font-variant-numeric: tabular-nums; }
.print-format-doc .one-center { text-align: center; }
.print-format-doc .one-right { text-align: right; }
"""

#: The house's own parts for an html block, as LAYOUT_HELP names them to a
#: model: frappe-ui's look on paper, in the same greys and colours.
HOUSE_PARTS = (
	"one-title (a heading), one-label and one-value (a label above its value), one-muted (small grey "
	"text), one-figure (a large amount), one-card (a bordered box), one-note (a grey callout), one-grid "
	"(children side by side), one-kv (a row of label and value, the value at the right), one-rule (a "
	"line), one-badge with one-badge--green, --red, --orange or --blue (a status), one-stamp or "
	"one-stamp--green (a stamp such as PAID), one-table with one-num on figures (a table like the "
	"builder's), one-center and one-right"
)

#: Who a document of trade is for, the first a kind has.
PARTY = ("customer_name", "supplier_name", "party_name", "customer", "supplier")

#: The address printed under the party.
ADDRESS = ("address_display",)

#: When it is dated, and what it is due or valid until.
DATED = ("posting_date", "transaction_date")
UNTIL = ("due_date", "valid_till", "delivery_date", "schedule_date")

#: The party's own reference, printed beside the dates.
REFERENCE = ("po_no", "supplier_delivery_note", "bill_no")

#: An item row's columns, each with its share of the width: the description
#: widest, the figures narrower.
ITEM_COLUMNS = (
	(("item_name", "item_code", "description"), 45),
	(("qty",), 15),
	(("rate",), 20),
	(("amount",), 20),
)

#: The totals, top to bottom, those the kind has.
TOTALS = ("net_total", "discount_amount", "total_taxes_and_charges", "grand_total", "rounded_total")

#: Long text printed last, each in a section of its own.
LONG = ("Text Editor", "Small Text", "Text", "Long Text", "Markdown Editor")

#: Fields a layout never starts with: how the form is laid out, and what only
#: the desk needs.
SKIPPED = frozenset(
	(
		"Section Break",
		"Column Break",
		"Tab Break",
		"HTML",
		"Button",
		"Fold",
		"Heading",
		"Password",
		"Attach",
		"Attach Image",
		"Signature",
		"Geolocation",
		"JSON",
		"Code",
		"Check",
	)
)

#: Fields that say how the record is kept rather than what it says.
KEEPING = frozenset(("naming_series", "amended_from", "company"))

#: How many of its tables a plain layout starts with, and how much long text.
TABLES, LONG_TEXTS = 3, 3


def starting_layout(doctype: str) -> list:
	"""The layout a format of this kind starts from."""
	meta = frappe.get_meta(doctype)
	return _trade(meta) or _plain(meta)


def essentials(doctype: str) -> list[str]:
	"""What a page of this kind must print to be read at all: a document of
	trade says who it is for and what it comes to. Anything else, nothing."""
	meta = frappe.get_meta(doctype)
	if not _trade(meta):
		return []
	total = _first(meta, ("grand_total", "rounded_total"))
	return [one for one in (_first(meta, PARTY), total) if one]


def _first(meta, names) -> str | None:
	return next((name for name in names if meta.has_field(name)), None)


def _trade(meta) -> list | None:
	items = meta.get_field("items")
	party = _first(meta, PARTY)
	if not items or items.fieldtype not in frappe.model.table_fields or not party:
		return None
	rows = frappe.get_meta(items.options)
	columns = []
	for names, share in ITEM_COLUMNS:
		found = _first(rows, names)
		if found:
			columns.append(f"{found}:{share}")
	who = [party, *(one for one in ADDRESS if meta.has_field(one))]
	when = [one for one in (_first(meta, DATED), _first(meta, UNTIL), _first(meta, REFERENCE)) if one]
	# The totals read as a column of label and figure, each on its line, the
	# label at the column's left edge and the figure at its right.
	totals = [{"field": one, "spread": True} for one in TOTALS if meta.has_field(one)]
	layout = [
		[who, when],
		[[{"table": "items", "columns": columns}]],
	]
	if totals:
		layout.append(
			{
				"labels_beside": True,
				"keep_together": True,
				"columns": [
					{"width": 55, "blocks": ["in_words"] if meta.has_field("in_words") else []},
					{"width": 45, "blocks": totals},
				],
			}
		)
	if meta.has_field("terms"):
		layout.append({"label": _("Terms"), "columns": [["terms"]]})
	return layout


def _plain(meta) -> list:
	main, long, tables = [], [], []
	for field in meta.fields:
		if field.hidden or field.print_hide or field.fieldtype in SKIPPED or field.fieldname in KEEPING:
			continue
		if field.fieldtype in frappe.model.table_fields:
			tables.append(field)
		elif field.fieldtype in LONG:
			long.append(field)
		elif field.reqd or field.in_list_view or field.bold:
			main.append(field.fieldname)
	main = main[:12]
	half = (len(main) + 1) // 2
	layout = [[main[:half], main[half:]]] if main else []
	for table in tables[:TABLES]:
		rows = frappe.get_meta(table.options)
		shown = [
			one.fieldname
			for one in rows.fields
			if one.in_list_view and not one.hidden and one.fieldtype not in SKIPPED
		][:5]
		if shown:
			share = 100 // len(shown)
			columns = [f"{one}:{share}" for one in shown]
			block = [[{"table": table.fieldname, "columns": columns}]]
			layout.append({"label": _(table.label), "columns": block} if table.label else block)
	for field in long[:LONG_TEXTS]:
		layout.append({"label": _(field.label or field.fieldname), "columns": [[field.fieldname]]})
	return layout
