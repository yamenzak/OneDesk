"""Writes the print formats One ships out of frappe's own builder pieces:
for now the Sales Invoice's master and a version of each one ERPNext ships.
A change made in the builder to one of these belongs here too, or the next
run puts it back. Run: python3 scripts/print_formats.py "<modified>"."""

import copy
import json
import os
import sys

APP = os.path.join(os.path.dirname(__file__), "..", "onedesk")
MUTED = "#6b7280"
INK = "#111827"
LINE = "#e5e7eb"
SOFT = "#f9fafb"
DATE = "dd MMM yyyy"
HEAD = f"font-size:9.5px;letter-spacing:0.08em;text-transform:uppercase;color:{MUTED};font-weight:600;margin-bottom:6px;"

#: What the builder's own controls cannot say: amounts kept on one line, and
#: the second line of a merged cell no heavier than the first.
CSS = """.child-table td[data-fieldtype="Currency"] { white-space: nowrap; }
.child-table td[data-fieldname="one_vat_amount"] .cell-line--primary,
.child-table td[data-fieldname="qty"] .cell-line--primary { font-weight: 400; }
"""


def text(words, **kw):
	return {"fieldtype": "Static Text", "custom": 1, "fieldname": "", "label": "Static Text", "text": words, **kw}


def heading(words, **kw):
	return text(words, custom_style=HEAD + kw.pop("custom_style", ""), **kw)


def field(fieldname, fieldtype, label, **kw):
	return {"fieldname": fieldname, "fieldtype": fieldtype, "label": label, **kw}


def row(fieldname, fieldtype, label, **kw):
	"""A label on the left and its value on the right, ruled underneath."""
	return field(fieldname, fieldtype, label, label_justify="space-between", hide_colon=1,
		custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};" + kw.pop("custom_style", ""), **kw)


def linked(path, label, **kw):
	return {"fieldtype": "Linked Field", "custom": 1, "fieldname": "", "label": label, "link_path": path, **kw}


def section(*columns, widths=None, top=0, **kw):
	cols = []
	for i, fields in enumerate(columns):
		col = {"label": "", "fields": list(fields)}
		if widths:
			col["width"] = widths[i]
		cols.append(col)
	return {"label": "", "show_label": "hide", "columns": cols, "margin": {"top": top, "right": 0, "bottom": 0, "left": 0}, **kw}


def table(fieldname, label, columns, **kw):
	return {"fieldname": fieldname, "fieldtype": "Table", "label": label, "show_label": "hide", "table_style": "lined",
		"table_bordered": False, "table_header": "plain", "table_cell_padding": 8, "table_columns": columns, **kw}


PILL = "display:inline-block;margin-top:6px;padding:2px 9px;border-radius:999px;font-size:10px;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;"
STATES = (
	("Paid", "#dcfce7", "#166534"),
	("Partly Paid", "#fef3c7", "#92400e"),
	("Unpaid", "#e0f2fe", "#075985"),
	("Overdue", "#fee2e2", "#991b1b"),
	("Return", "#f3f4f6", "#374151"),
	("Credit Note Issued", "#f3f4f6", "#374151"),
)
TITLES = (
	("Tax Invoice", "doc.company_tax_id and not doc.is_return"),
	("Tax Credit Note", "doc.company_tax_id and doc.is_return"),
	("Invoice", "not doc.company_tax_id and not doc.is_return"),
	("Credit Note", "not doc.company_tax_id and doc.is_return"),
)


def titles(size=24, words=TITLES):
	return [text(w, visible_if=when, font_size=size, bold=1, custom_style="letter-spacing:-0.01em;line-height:1.1;") for w, when in words]


def pills():
	return [text(s, visible_if=f'doc.docstatus == 1 and doc.status == "{s}"', custom_style=PILL + f"background:{bg};color:{ink};") for s, bg, ink in STATES]


def title_section(words=TITLES):
	return section(
		titles(words=words) + pills(),
		[
			field("name", "Data", "Number", show_label="hide", align="right", bold=1, font_size=14),
			field("company_tax_id", "Data", "TRN", align="right", hide_colon=1, custom_style="margin-top:4px;"),
		],
		widths=[60, 40], top=6, field_orientation="left-right",
	)


def bill_to():
	return [
		heading("Bill To"),
		field("customer_name", "Data", "Customer", show_label="hide", bold=1, font_size=13),
		field("address_display", "Small Text", "Address", show_label="hide", custom_style="color:#374151;line-height:1.5;margin-top:2px;"),
		field("tax_id", "Data", "TRN", hide_colon=1, custom_style="margin-top:6px;"),
	]


def detail_rows():
	return [
		row("posting_date", "Date", "Date", date_format=DATE),
		row("due_date", "Date", "Due Date", date_format=DATE, visible_if="not doc.is_return"),
		row("return_against", "Link", "Against Invoice"),
		linked("project.project_name", "Project", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};"),
		row("po_no", "Data", "Your Reference"),
	]


def party_section():
	return section(bill_to(), detail_rows(), widths=[55, 45], gap=48, top=26, field_orientation="left-right")


TAXED = "doc.total_taxes_and_charges"


def item_column(image=False, code=False, width=31):
	merged = []
	if image:
		merged.append({"fieldname": "image", "fieldtype": "Attach Image", "label": "Image"})
	if code:
		merged.append({"fieldname": "item_code", "fieldtype": "Link", "label": "Item Code", "style": "muted-sm"})
	merged.append({"fieldname": "one_size", "fieldtype": "Data", "label": "Size", "style": "muted-sm"})
	merged.append({"fieldname": "description", "fieldtype": "Text Editor", "label": "Description", "style": "muted-sm"})
	col = {"fieldname": "item_name", "fieldtype": "Data", "label": "Description", "width": width, "merged_fields": merged}
	if image:
		col["image_size"] = 36
	return col


def line_columns(image=False, code=False):
	return [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(image=image, code=code),
		{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "width": 9, "align": "right",
			"merged_fields": [{"fieldname": "uom", "fieldtype": "Link", "label": "UOM", "style": "muted-sm"}]},
		{"fieldname": "rate", "fieldtype": "Currency", "label": "Unit Price", "width": 13, "align": "right"},
		{"fieldname": "net_amount", "fieldtype": "Currency", "label": "Taxable", "width": 14, "align": "right"},
		{"fieldname": "one_vat_amount", "fieldtype": "Currency", "label": "VAT", "width": 12, "align": "right", "column_condition": TAXED,
			"merged_fields": [{"fieldname": "one_vat_rate", "fieldtype": "Percent", "label": "VAT Rate", "style": "muted-sm"}]},
		{"fieldname": "one_line_total", "fieldtype": "Currency", "label": "Amount", "width": 16, "align": "right", "column_condition": TAXED},
	]


def lines_section(columns=None, **look):
	return section([table("items", "Items", columns or line_columns(),
		# Retention held is said under the totals, not as lines.
		row_condition="not row.one_held", **look)], top=28)


#: An invoice priced by the hour bills exactly its time; a retainer's fee does not.
PRICED = "doc.total_billing_amount == doc.total"


def time_section(**look):
	return section(
		[
			heading("Time Billed", visible_if=PRICED),
			heading("Time Spent", visible_if=f"not ({PRICED})"),
			table("timesheets", "Time Spent", [
				{"fieldname": "from_time", "fieldtype": "Date", "label": "Date", "width": 16, "date_format": DATE},
				{"fieldname": "activity_type", "fieldtype": "Link", "label": "Activity", "width": 24},
				{"fieldname": "description", "fieldtype": "Small Text", "label": "Description", "width": 30},
				{"fieldname": "billing_hours", "fieldtype": "Float", "label": "Hours", "width": 12, "align": "right"},
				{"fieldname": "billing_amount", "fieldtype": "Currency", "label": "Amount", "width": 18, "align": "right", "column_condition": PRICED},
			], table_cell_padding=6, **look),
			field("total_billing_hours", "Float", "Total Hours", align="right", hide_colon=1, bold=1, custom_style="padding:6px 0;"),
		],
		top=18, visible_if="doc.timesheets", field_orientation="left-right",
	)


def schedule(**look):
	return [
		heading("Payment Schedule", visible_if="doc.payment_schedule[1:]"),
		table("payment_schedule", "Payment Schedule", [
			{"fieldname": "due_date", "fieldtype": "Date", "label": "Due Date", "width": 32, "date_format": DATE},
			{"fieldname": "invoice_portion", "fieldtype": "Percent", "label": "Invoice Portion", "width": 30, "align": "right"},
			{"fieldname": "payment_amount", "fieldtype": "Currency", "label": "Amount", "width": 38, "align": "right"},
		], visible_if="doc.payment_schedule[1:]", table_cell_padding=6, **look),
	]


def total_rows(words=True):
	rows = [
		# Taxed when released: the work, the retention taken off it, and what's taxed.
		row("one_work_billed", "Currency", "Work Billed", visible_if="doc.one_work_billed"),
		row("one_retention_held", "Currency", "Less Retention", visible_if="doc.one_work_billed"),
		row("net_total", "Currency", "Subtotal"),
		row("total_taxes_and_charges", "Currency", "VAT"),
		row("grand_total", "Currency", "Total", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
		# Taxed with the invoice: the retention is part of the total, asked for later.
		row("one_retention_held", "Currency", "Retention Held", visible_if="doc.one_retention_held and not doc.one_work_billed"),
		row("one_due_now", "Currency", "Due Now", bold=1, visible_if="doc.one_due_now and doc.one_retention_held and doc.outstanding_amount == (doc.rounded_total or doc.grand_total)"),
		row("outstanding_amount", "Currency", "Balance Due", bold=1, visible_if='doc.status in ("Partly Paid", "Overdue") and doc.outstanding_amount != doc.grand_total'),
	]
	if words:
		rows.append(field("in_words", "Data", "In Words", show_label="hide", align="right", custom_style=f"color:{MUTED};font-size:10px;margin-top:6px;"))
	return rows


def totals_section(left=None, words=True, **look):
	return section(left if left is not None else schedule(**look), total_rows(words), widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")


def bank_section():
	return section(
		[
			heading("Pay To"),
			linked("one_pay_into.bank", "Bank", hide_colon=1, custom_style="padding:2px 0;"),
			linked("one_pay_into.account_name", "Account", hide_colon=1, custom_style="padding:2px 0;"),
			linked("one_pay_into.iban", "IBAN", hide_colon=1, custom_style="padding:2px 0;font-variant-numeric:tabular-nums;"),
		],
		[], widths=[52, 48], top=22, field_orientation="left-right",
		visible_if="doc.one_pay_into and not doc.is_return and doc.status != 'Paid'", keep_together=1,
	)


def terms_section():
	return section([heading("Terms"), field("terms", "Text Editor", "Terms", show_label="hide", custom_style="color:#374151;font-size:10.5px;line-height:1.55;")], top=22, visible_if="doc.terms", keep_together=1)


def layout(*sections):
	return {"header": {"columns": [{"label": "", "fields": []}]}, "footer": {"columns": [{"label": "", "fields": []}]}, "sections": list(sections)}


# -- The versions --------------------------------------------------------------

def master():
	"""ERPNext's Modern, its UAE Tax Invoice and its Return, in one."""
	return layout(title_section(), party_section(), lines_section(), time_section(), totals_section(), bank_section(), terms_section())


def classic():
	"""ERPNext's Classic: who it's for on the left, the invoice's own details
	in a shaded panel on the right, and the lines in a rounded table under a
	shaded head, each with its item code."""
	look = {"table_header": "styled", "table_header_bg": "#f3f4f6", "table_bordered": True, "table_radius": 8}
	panel = section(
		bill_to(),
		titles(size=17) + pills() + [
			row("name", "Data", "Number", bold=1),
			row("company_tax_id", "Data", "Our TRN"),
			*detail_rows(),
		],
		widths=[52, 48], gap=40, top=8, field_orientation="left-right",
	)
	panel["columns"][1]["fields"][-1]["custom_style"] = "padding:5px 0;"
	words = section([field("in_words", "Data", "In Words", hide_colon=1, label_gap=10)], top=14, background=SOFT, radius=6,
		padding={"top": 9, "right": 12, "bottom": 9, "left": 12}, field_orientation="left-right")
	return layout(panel, lines_section(line_columns(code=True), **look), time_section(**look), totals_section(words=False, **look), words, bank_section(), terms_section())


def bordered():
	"""ERPNext's Bordered: the heading facts in ruled boxes, from whom and to
	whom side by side, and the lines in a full grid."""
	grid = {"field_borders": 1, "grid_borders": "all", "border_color": LINE, "cell_padding": 10, "radius": 6}
	facts = section(
		[field("customer_name", "Data", "Customer", bold=1), field("posting_date", "Date", "Date", date_format=DATE)],
		[field("name", "Data", "Invoice No", bold=1), field("due_date", "Date", "Due Date", date_format=DATE)],
		top=20, **grid,
	)
	parties = section(
		[heading("Bill From"), field("company", "Link", "Company", show_label="hide", bold=1),
			field("company_address_display", "Small Text", "Address", show_label="hide", custom_style="color:#374151;line-height:1.5;"),
			field("company_tax_id", "Data", "TRN", hide_colon=1, show_label="inline")],
		[heading("Bill To"), field("customer_name", "Data", "Customer", show_label="hide", bold=1),
			field("address_display", "Small Text", "Address", show_label="hide", custom_style="color:#374151;line-height:1.5;"),
			field("tax_id", "Data", "TRN", hide_colon=1, show_label="inline")],
		widths=[50, 50], gap=24, top=10, radius=6, padding={"top": 14, "right": 16, "bottom": 14, "left": 16},
		custom_style=f"border:1px solid {LINE};",
	)
	look = {"table_bordered": True, "table_header": "styled", "table_header_bg": SOFT, "table_radius": 6}
	return layout(section(titles() + pills(), top=6), facts, parties, lines_section(**look), time_section(**look), totals_section(**look), bank_section(), terms_section())


def with_images():
	"""ERPNext's Modern with Images: the master, each line led by its item's picture."""
	return layout(title_section(), party_section(), lines_section(line_columns(image=True)), time_section(), totals_section(), bank_section(), terms_section())


SIMPLE = (
	("Simplified Tax Invoice", "not doc.is_return"),
	("Simplified Tax Credit Note", "doc.is_return"),
)


def simplified():
	"""The FTA's simplified tax invoice (Executive Regulation, Article 60),
	ERPNext's Simplified Tax Invoice: who sold, their TRN, when, what, and the
	total with the tax in it. Nothing of the buyer is asked for."""
	head = section(
		titles(size=20, words=SIMPLE),
		[field("name", "Data", "Number", show_label="hide", align="right", bold=1, font_size=13),
			field("posting_date", "Date", "Date", align="right", hide_colon=1, date_format=DATE, custom_style="margin-top:4px;"),
			field("company_tax_id", "Data", "TRN", align="right", hide_colon=1, custom_style="margin-top:2px;")],
		widths=[60, 40], top=6, field_orientation="left-right",
	)
	sold = table("items", "Items", [
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Description", "width": 60},
		{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "width": 15, "align": "right"},
		{"fieldname": "one_line_total", "fieldtype": "Currency", "label": "Amount incl. VAT", "width": 25, "align": "right"},
	], row_condition="not row.one_held")
	end = section([], [
		row("grand_total", "Currency", "Total incl. VAT", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
		row("total_taxes_and_charges", "Currency", "VAT Included"),
	], widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")
	return layout(head, section([field("customer_name", "Data", "Customer", hide_colon=1)], top=18, field_orientation="left-right", visible_if="doc.customer_name"), section([sold], top=16), end)


def detailed():
	"""ERPNext's Detailed Tax Invoice: the master, each line with its item
	code, every tax charged with its rate and what it was charged on, and the
	amounts again in the company's currency when the invoice is in another."""
	taxes = section([
		heading("Taxes"),
		table("taxes", "Taxes", [
			{"fieldname": "description", "fieldtype": "Small Text", "label": "Tax", "width": 40},
			{"fieldname": "rate", "fieldtype": "Float", "label": "Rate", "width": 15, "align": "right"},
			{"fieldname": "net_amount", "fieldtype": "Currency", "label": "Taxable", "width": 22, "align": "right"},
			{"fieldname": "tax_amount", "fieldtype": "Currency", "label": "Tax", "width": 23, "align": "right"},
		], table_cell_padding=6),
	], top=18, visible_if="doc.taxes")
	base = section([], [
		heading("In Company Currency"),
		row("base_net_total", "Currency", "Subtotal"),
		row("base_total_taxes_and_charges", "Currency", "VAT"),
		row("base_grand_total", "Currency", "Total", bold=1),
		row("conversion_rate", "Float", "Exchange Rate"),
	], widths=[52, 48], gap=48, top=12, field_orientation="left-right", visible_if="doc.conversion_rate != 1")
	return layout(title_section(), party_section(), lines_section(line_columns(code=True)), taxes, time_section(), totals_section(), base, bank_section(), terms_section())


def voucher():
	"""ERPNext's Sales Auditing Voucher, for the books rather than the
	customer: what was posted where. Each line names the income account and
	cost center it was credited to, each tax its account, and the customer's
	account is debited with the total. Room to sign under it."""
	head = section(
		titles(size=20, words=(("Sales Voucher", "not doc.is_return"), ("Credit Note Voucher", "doc.is_return"))),
		[field("name", "Data", "Voucher No", align="right", bold=1, hide_colon=1),
			field("posting_date", "Date", "Date", align="right", hide_colon=1, date_format=DATE, custom_style="margin-top:4px;")],
		widths=[60, 40], top=6, field_orientation="left-right",
	)
	who = section(
		[row("customer_name", "Data", "Customer"), row("debit_to", "Link", "Debit To"), linked("project.project_name", "Project", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};")],
		[row("grand_total", "Currency", "Debited", bold=1), row("net_total", "Currency", "Income Credited"), row("total_taxes_and_charges", "Currency", "Tax Credited")],
		widths=[50, 50], gap=40, top=20, field_orientation="left-right",
	)
	look = {"table_bordered": True, "table_header": "styled", "table_header_bg": SOFT, "table_cell_padding": 6}
	lines = section([heading("Income"), table("items", "Items", [
		{"fieldname": "item_code", "fieldtype": "Link", "label": "Item", "width": 16},
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Description", "width": 24},
		{"fieldname": "income_account", "fieldtype": "Link", "label": "Account", "width": 22},
		{"fieldname": "cost_center", "fieldtype": "Link", "label": "Cost Center", "width": 16},
		{"fieldname": "net_amount", "fieldtype": "Currency", "label": "Credit", "width": 22, "align": "right"},
	], **look)], top=22)
	taxes = section([heading("Tax"), table("taxes", "Taxes", [
		{"fieldname": "account_head", "fieldtype": "Link", "label": "Account", "width": 40},
		{"fieldname": "cost_center", "fieldtype": "Link", "label": "Cost Center", "width": 22},
		{"fieldname": "rate", "fieldtype": "Float", "label": "Rate", "width": 16, "align": "right"},
		{"fieldname": "tax_amount", "fieldtype": "Currency", "label": "Credit", "width": 22, "align": "right"},
	], **look)], top=16, visible_if="doc.taxes")
	remarks = section([heading("Remarks"), field("remarks", "Small Text", "Remarks", show_label="hide")], top=16, visible_if="doc.remarks and doc.remarks != 'No Remarks'")
	sign = "padding-top:40px;border-bottom:1px solid #9ca3af;margin-bottom:6px;"
	signs = section(
		[text("", custom_style=sign), text("Prepared By", custom_style=f"color:{MUTED};font-size:10px;"), field("owner", "Link", "Prepared By", show_label="hide", custom_style="font-size:10px;")],
		[text("", custom_style=sign), text("Checked By", custom_style=f"color:{MUTED};font-size:10px;")],
		[text("", custom_style=sign), text("Approved By", custom_style=f"color:{MUTED};font-size:10px;")],
		gap=32, top=36, keep_together=1,
	)
	return layout(head, who, lines, taxes, remarks, signs)


# -- Documents that trade: quotations, orders, deliveries -----------------------

#: What each prints, as One's blocks did: its title, who it's for, its own
#: details, whether its lines are priced, and who signs it.
TRADE = {
	"Quotation": {
		"module": "one_crm",
		"titles": (("Quotation", ""),),
		"number": "Quotation No",
		"party": ("Prepared For", "customer_name"),
		# A quotation may be for a lead, so it keeps no tax ID of its own.
		"tax": None,
		"details": (("transaction_date", "Date", "Date"), ("valid_till", "Date", "Valid Until")),
		"schedule": True,
		"signs": (("For", "company"), ("Accepted By", "customer_name")),
	},
	"Sales Order": {
		"module": "one_crm",
		"titles": (("Sales Order", ""),),
		"number": "Order No",
		"party": ("Bill To", "customer_name"),
		"ship": True,
		"details": (
			("transaction_date", "Date", "Date"),
			("delivery_date", "Date", "Delivery Date"),
			("po_no", "Data", "Your Reference"),
			("project", "Project", "Project"),
		),
		"schedule": True,
		"advance": True,
		"bank": True,
	},
	"Delivery Note": {
		"module": "one_inventory",
		"titles": (("Delivery Note", "not doc.is_return"), ("Return", "doc.is_return")),
		"number": "Delivery No",
		"party": ("Deliver To", "customer_name"),
		"delivered": True,
		"details": (
			("posting_date", "Date", "Date"),
			("po_no", "Data", "Your Reference"),
			("project", "Project", "Project"),
			("transporter_name", "Data", "Transporter"),
			("vehicle_no", "Data", "Vehicle"),
			("driver_name", "Data", "Driver"),
		),
		"priced": False,
		"signs": (("Delivered By", None), ("Received By", "customer_name")),
	},
}


def _titles(spec, size=24):
	return [text(w, visible_if=when, font_size=size, bold=1, custom_style="letter-spacing:-0.01em;line-height:1.1;") if when
		else text(w, font_size=size, bold=1, custom_style="letter-spacing:-0.01em;line-height:1.1;") for w, when in spec["titles"]]


def _company_trn(**kw):
	return linked("company.tax_id", "TRN", hide_colon=1, **kw)


def trade_title(spec):
	return section(
		_titles(spec),
		[field("name", "Data", spec["number"], show_label="hide", align="right", bold=1, font_size=14),
			_company_trn(align="right", custom_style="margin-top:4px;")],
		widths=[60, 40], top=6, field_orientation="left-right",
	)


def trade_party(spec):
	words, name = spec["party"]
	found = [heading(words), field(name, "Data", "Customer", show_label="hide", bold=1, font_size=13)]
	style = "color:#374151;line-height:1.5;margin-top:2px;"
	if spec.get("delivered"):
		found += [
			field("shipping_address", "Small Text", "Address", show_label="hide", custom_style=style, visible_if="doc.shipping_address"),
			field("address_display", "Small Text", "Address", show_label="hide", custom_style=style, visible_if="not doc.shipping_address"),
		]
	else:
		found.append(field("address_display", "Small Text", "Address", show_label="hide", custom_style=style))
	if spec.get("tax", "tax_id"):
		found.append(field(spec.get("tax", "tax_id"), "Data", "TRN", hide_colon=1, custom_style="margin-top:6px;"))
	found.append(field("contact_display", "Data", "Contact", hide_colon=1, custom_style="margin-top:2px;"))
	if spec.get("ship"):
		elsewhere = "doc.shipping_address_name and doc.shipping_address_name != doc.customer_address"
		found += [
			heading("Ship To", visible_if=elsewhere, custom_style="margin-top:14px;"),
			field("shipping_address", "Small Text", "Ship To", show_label="hide", custom_style=style, visible_if=elsewhere),
		]
	return found


def trade_details(spec):
	found = []
	for fieldname, fieldtype, label in spec["details"]:
		if fieldtype == "Project":
			found.append(linked("project.project_name", label, label_justify="space-between", hide_colon=1,
				custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};"))
		else:
			found.append(row(fieldname, fieldtype, label, **({"date_format": DATE} if fieldtype == "Date" else {})))
	return found


def trade_columns(spec, image=False, code=False):
	found = [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(image=image, code=code, width=45 if spec.get("priced", True) else 75),
		{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "width": 12 if spec.get("priced", True) else 20, "align": "right",
			"merged_fields": [{"fieldname": "uom", "fieldtype": "Link", "label": "UOM", "style": "muted-sm"}]},
	]
	if spec.get("priced", True):
		found += [
			{"fieldname": "rate", "fieldtype": "Currency", "label": "Unit Price", "width": 18, "align": "right"},
			{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "width": 20, "align": "right"},
		]
	return found


def trade_lines(spec, columns=None, **look):
	return section([table("items", "Items", columns or trade_columns(spec), **look)], top=28)


def trade_totals(spec, words=True, **look):
	rows = [
		row("total", "Currency", "Subtotal"),
		row("discount_amount", "Currency", "Discount", visible_if="doc.discount_amount"),
		row("total_taxes_and_charges", "Currency", "VAT", visible_if="doc.total_taxes_and_charges"),
		row("grand_total", "Currency", "Total", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
	]
	if spec.get("advance"):
		rows.append(row("advance_paid", "Currency", "Paid in Advance", visible_if="doc.advance_paid"))
	if words:
		rows.append(field("in_words", "Data", "In Words", show_label="hide", align="right", custom_style=f"color:{MUTED};font-size:10px;margin-top:6px;"))
	left = schedule(**look) if spec.get("schedule") else []
	return section(left, rows, widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")


def trade_bank():
	found = bank_section()
	found["visible_if"] = "doc.one_pay_into"
	return found


def signs_section(signs):
	line = "padding-top:44px;border-bottom:1px solid #9ca3af;margin-bottom:6px;"
	small = f"color:{MUTED};font-size:10px;"
	columns = []
	for words, fieldname in signs:
		column = [text("", custom_style=line), text(words, custom_style=small)]
		if fieldname:
			column.append(field(fieldname, "Data", words, show_label="hide", custom_style="font-size:10.5px;font-weight:600;"))
		columns.append(column)
	return section(*columns, gap=48, top=36, keep_together=1)


def trade_rest(spec):
	found = [terms_section()]
	if spec.get("bank"):
		found.insert(0, trade_bank())
	if spec.get("signs"):
		found.append(signs_section(spec["signs"]))
	return found


def trade_master(spec):
	return layout(
		trade_title(spec),
		section(trade_party(spec), trade_details(spec), widths=[55, 45], gap=48, top=26, field_orientation="left-right"),
		trade_lines(spec),
		*([trade_totals(spec)] if spec.get("priced", True) else []),
		*trade_rest(spec),
	)


def trade_classic(spec):
	look = {"table_header": "styled", "table_header_bg": "#f3f4f6", "table_bordered": True, "table_radius": 8}
	panel = section(
		trade_party(spec),
		[*_titles(spec, size=17), row("name", "Data", spec["number"], bold=1), linked("company.tax_id", "Our TRN", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};"), *trade_details(spec)],
		widths=[52, 48], gap=40, top=8, field_orientation="left-right",
	)
	found = [panel, trade_lines(spec, trade_columns(spec, code=True), **look)]
	if spec.get("priced", True):
		found.append(trade_totals(spec, words=False, **look))
		found.append(section([field("in_words", "Data", "In Words", hide_colon=1, label_gap=10)], top=14, background=SOFT, radius=6,
			padding={"top": 9, "right": 12, "bottom": 9, "left": 12}, field_orientation="left-right"))
	return layout(*found, *trade_rest(spec))


def trade_bordered(spec):
	grid = {"field_borders": 1, "grid_borders": "all", "border_color": LINE, "cell_padding": 10, "radius": 6}
	first, second = spec["details"][0], spec["details"][1]

	def fact(one):
		fieldname, fieldtype, label = one
		if fieldtype == "Project":
			return linked("project.project_name", label)
		return field(fieldname, fieldtype, label, **({"date_format": DATE} if fieldtype == "Date" else {}))

	words, name = spec["party"]
	facts = section(
		[field(name, "Data", words, bold=1), fact(first)],
		[field("name", "Data", spec["number"], bold=1), fact(second)],
		top=20, **grid,
	)
	style = "color:#374151;line-height:1.5;"
	parties = section(
		[heading("From"), field("company", "Link", "Company", show_label="hide", bold=1),
			field("company_address_display", "Small Text", "Address", show_label="hide", custom_style=style),
			_company_trn(show_label="inline")],
		trade_party(spec),
		widths=[50, 50], gap=24, top=10, radius=6, padding={"top": 14, "right": 16, "bottom": 14, "left": 16},
		custom_style=f"border:1px solid {LINE};", field_orientation="left-right",
	)
	look = {"table_bordered": True, "table_header": "styled", "table_header_bg": SOFT, "table_radius": 6}
	found = [section(_titles(spec), top=6), facts, parties, trade_lines(spec, **look)]
	if spec.get("priced", True):
		found.append(trade_totals(spec, **look))
	return layout(*found, *trade_rest(spec))


def trade_images(spec):
	found = trade_master(spec)
	for one in found["sections"]:
		for column in one["columns"]:
			for df in column["fields"]:
				if df.get("fieldname") == "items" and df.get("fieldtype") == "Table":
					df["table_columns"] = trade_columns(spec, image=True)
	return found


def proforma():
	"""ERPNext's Proforma Invoice: the order as the invoice it will become,
	to be paid ahead, with the bank to pay into."""
	spec = {**TRADE["Sales Order"], "titles": (("Proforma Invoice", ""),), "number": "Proforma No"}
	return trade_master(spec)


def _trade(doctype, make):
	return lambda: make(TRADE[doctype])


#: Each version: its doctype, the module it ships in, and what draws it.
VERSIONS = {
	"One Sales Invoice": ("Sales Invoice", "one_book", master),
	"One Sales Invoice Classic": ("Sales Invoice", "one_book", classic),
	"One Sales Invoice Bordered": ("Sales Invoice", "one_book", bordered),
	"One Sales Invoice with Images": ("Sales Invoice", "one_book", with_images),
	"One Simplified Tax Invoice": ("Sales Invoice", "one_book", simplified),
	"One Detailed Tax Invoice": ("Sales Invoice", "one_book", detailed),
	"One Sales Voucher": ("Sales Invoice", "one_book", voucher),
	"One Proforma Invoice": ("Sales Order", "one_crm", proforma),
}
for _doctype, _spec in TRADE.items():
	VERSIONS[f"One {_doctype}"] = (_doctype, _spec["module"], _trade(_doctype, trade_master))
	VERSIONS[f"One {_doctype} Classic"] = (_doctype, _spec["module"], _trade(_doctype, trade_classic))
	VERSIONS[f"One {_doctype} Bordered"] = (_doctype, _spec["module"], _trade(_doctype, trade_bordered))
	VERSIONS[f"One {_doctype} with Images"] = (_doctype, _spec["module"], _trade(_doctype, trade_images))

MODULES = {"one_book": "One Book", "one_crm": "One CRM", "one_inventory": "One Inventory", "one_hr": "One HR", "one_project": "One Project"}


def write(modified):
	base = json.load(open(f"{APP}/one_book/print_format/one_sales_invoice/one_sales_invoice.json"))
	for name, (doctype, module, make) in VERSIONS.items():
		scrub = name.lower().replace(" ", "_")
		folder = f"{APP}/{module}/print_format/{scrub}"
		os.makedirs(folder, exist_ok=True)
		path = f"{folder}/{scrub}.json"
		doc = json.load(open(path)) if os.path.exists(path) else {**copy.deepcopy(base), "creation": modified}
		new = {
			**doc,
			"name": name,
			"doc_type": doctype,
			"module": MODULES[module],
			"format_data": json.dumps(make()),
			"font": "Inter",
			"font_size": 11,
			"show_label_colon": 0,
			"label_color": MUTED,
			"value_color": INK,
			"print_format_builder_beta": 1,
			"css": CSS,
			"absolute_value": 0,
		}
		if new != doc:
			new["modified"] = modified
			json.dump(new, open(path, "w"), indent=1, ensure_ascii=False)
			open(path, "a").write("\n")
			print("wrote", name)


if __name__ == "__main__":
	write(sys.argv[1])
