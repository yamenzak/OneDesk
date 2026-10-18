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
.child-table td[data-fieldname="qty"] .cell-line--primary,
.child-table td[data-fieldname="received_qty"] .cell-line--primary,
.child-table td[data-fieldname="required_qty"] .cell-line--primary,
.child-table td[data-fieldname="consumed_qty"] .cell-line--primary { font-weight: 400; }
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


def contact_lines():
	"""Who to talk to there, and how."""
	small = "margin-top:2px;"
	return [
		field("contact_display", "Data", "Contact", hide_colon=1, custom_style="margin-top:6px;"),
		field("contact_email", "Data", "Email", hide_colon=1, custom_style=small),
		field("contact_mobile", "Data", "Phone", hide_colon=1, custom_style=small),
	]


def bill_to():
	return [
		heading("Bill To"),
		field("customer_name", "Data", "Customer", show_label="hide", bold=1, font_size=13),
		field("address_display", "Small Text", "Address", show_label="hide", custom_style="color:#374151;line-height:1.5;margin-top:2px;"),
		field("tax_id", "Data", "TRN", hide_colon=1, custom_style="margin-top:6px;"),
		*contact_lines(),
	]


def detail_rows():
	return [
		row("posting_date", "Date", "Date", date_format=DATE),
		row("due_date", "Date", "Due Date", date_format=DATE, visible_if="not doc.is_return"),
		row("return_against", "Link", "Against Invoice"),
		linked("project.project_name", "Project", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};"),
		row("po_no", "Data", "Your Reference"),
		row("payment_terms_template", "Link", "Payment Terms"),
		row("incoterm", "Link", "Delivery Terms"),
	]


def party_section():
	return section(bill_to(), detail_rows(), widths=[55, 45], gap=48, top=26, field_orientation="left-right")


TAXED = "doc.total_taxes_and_charges"


def item_column(image=False, code=False, width=31, describe=True):
	merged = []
	if image:
		merged.append({"fieldname": "image", "fieldtype": "Attach Image", "label": "Image"})
	if code:
		merged.append({"fieldname": "item_code", "fieldtype": "Link", "label": "Item Code", "style": "muted-sm"})
	merged.append({"fieldname": "one_size", "fieldtype": "Data", "label": "Size", "style": "muted-sm"})
	if describe:
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
		"details": (("transaction_date", "Date", "Date"), ("valid_till", "Date", "Valid Until"), ("payment_terms_template", "Link", "Payment Terms"), ("incoterm", "Link", "Delivery Terms")),
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
			("payment_terms_template", "Link", "Payment Terms"),
			("incoterm", "Link", "Delivery Terms"),
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
			("incoterm", "Link", "Delivery Terms"),
		),
		"priced": False,
		"signs": (("Delivered By", None), ("Received By", "customer_name")),
	},
}


def _rfq_party(spec):
	"""A request goes to every supplier listed, and the goods come to us."""
	style = "color:#374151;line-height:1.5;margin-top:2px;"
	return [
		heading("Requested From"),
		table("suppliers", "Suppliers", [{"fieldname": "supplier_name", "fieldtype": "Data", "label": "Supplier", "width": 100}],
			table_header="none", table_style="plain", table_cell_padding=2),
		heading("Deliver To", custom_style="margin-top:14px;", visible_if="doc.shipping_address_display"),
		field("shipping_address_display", "Small Text", "Deliver To", show_label="hide", custom_style=style, visible_if="doc.shipping_address_display"),
	]


TRADE.update({
	"Purchase Order": {
		# A buyer's own address is the one it's billed at.
		"our_address": "billing_address_display",
		"module": "one_inventory",
		"titles": (("Purchase Order", ""),),
		"number": "Order No",
		"party": ("Supplier", "supplier_name"),
		"tax": None,
		"deliver": True,
		"details": (
			("transaction_date", "Date", "Date"),
			("schedule_date", "Date", "Required By"),
			("project", "Project", "Project"),
			("payment_terms_template", "Link", "Payment Terms"),
			("incoterm", "Link", "Delivery Terms"),
		),
		"schedule": True,
		"advance": True,
	},
	"Purchase Invoice": {
		# A buyer's own address is the one it's billed at.
		"our_address": "billing_address_display",
		"module": "one_book",
		"titles": (("Purchase Invoice", "not doc.is_return"), ("Debit Note", "doc.is_return")),
		"number": "Invoice No",
		"party": ("Supplier", "supplier_name"),
		"us": "Billed To",
		"details": (
			("posting_date", "Date", "Date"),
			("bill_no", "Data", "Supplier Invoice No"),
			("bill_date", "Date", "Supplier Invoice Date"),
			("due_date", "Date", "Due Date"),
			("return_against", "Link", "Against Invoice"),
			("project", "Project", "Project"),
			("payment_terms_template", "Link", "Payment Terms"),
			("incoterm", "Link", "Delivery Terms"),
		),
		"schedule": True,
	},
	"Request for Quotation": {
		# A buyer's own address is the one it's billed at.
		"our_address": "billing_address_display",
		"module": "one_inventory",
		"titles": (("Request for Quotation", ""),),
		"number": "Request No",
		"party_fields": _rfq_party,
		"details": (("transaction_date", "Date", "Date"), ("schedule_date", "Date", "Required By"), ("incoterm", "Link", "Delivery Terms")),
		"priced": False,
		"columns": (
			{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "width": 14, "align": "right",
				"merged_fields": [{"fieldname": "uom", "fieldtype": "Link", "label": "UOM", "style": "muted-sm"}]},
			{"fieldname": "schedule_date", "fieldtype": "Date", "label": "Required By", "width": 18, "align": "right", "date_format": DATE},
		),
		"message": "message_for_supplier",
		"contacts": False,
		"counted": False,
	},
	"Purchase Receipt": {
		# A buyer's own address is the one it's billed at.
		"our_address": "billing_address_display",
		"module": "one_inventory",
		"titles": (("Goods Received Note", "not doc.is_return"), ("Goods Returned", "doc.is_return")),
		"number": "Receipt No",
		"party": ("Received From", "supplier_name"),
		"tax": None,
		"us": "Received By",
		"details": (
			("posting_date", "Date", "Date"),
			("supplier_delivery_note", "Data", "Their Delivery Note"),
			("set_warehouse", "Link", "Into"),
			("transporter_name", "Data", "Transporter"),
			("lr_no", "Data", "Vehicle"),
			("project", "Project", "Project"),
			("incoterm", "Link", "Delivery Terms"),
		),
		"priced": False,
		"columns": (
			{"fieldname": "received_qty", "fieldtype": "Float", "label": "Received", "width": 14, "align": "right",
				"merged_fields": [{"fieldname": "uom", "fieldtype": "Link", "label": "UOM", "style": "muted-sm"}]},
			{"fieldname": "qty", "fieldtype": "Float", "label": "Accepted", "width": 13, "align": "right"},
			{"fieldname": "rejected_qty", "fieldtype": "Float", "label": "Rejected", "width": 13, "align": "right"},
		),
		"signs": (("Delivered By", "supplier_name"), ("Received By", None)),
	},
})


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
	if spec.get("party_fields"):
		return spec["party_fields"](spec)
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
	if spec.get("contacts", True):
		found += contact_lines()
	if spec.get("deliver"):
		found += [
			heading("Deliver To", visible_if="doc.shipping_address_display", custom_style="margin-top:14px;"),
			field("shipping_address_display", "Small Text", "Deliver To", show_label="hide", custom_style=style, visible_if="doc.shipping_address_display"),
		]
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
	if spec.get("columns"):
		rest = [dict(one) for one in spec["columns"]]
		width = 100 - 5 - sum(one["width"] for one in rest)
		return [{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5}, item_column(image=image, code=code, width=width), *rest]
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
	if spec.get("message"):
		found.insert(0, section([heading("Message"), field(spec["message"], "Text Editor", "Message", show_label="hide", custom_style="line-height:1.55;")],
			top=22, visible_if=f"doc.{spec['message']}"))
	if spec.get("bank"):
		found.insert(0, trade_bank())
	if spec.get("signs"):
		found.append(signs_section(spec["signs"]))
	return found


def trade_count(spec):
	"""A document without prices ends its lines with how many in all."""
	if spec.get("priced", True) or not spec.get("counted", True):
		return []
	return [section([], [row("total_qty", "Float", "Total Qty", bold=1)], widths=[52, 48], gap=48, top=8, field_orientation="left-right")]


def trade_master(spec):
	return layout(
		trade_title(spec),
		section(trade_party(spec), trade_details(spec), widths=[55, 45], gap=48, top=26, field_orientation="left-right"),
		trade_lines(spec),
		*([trade_totals(spec)] if spec.get("priced", True) else trade_count(spec)),
		*trade_rest(spec),
	)


def trade_classic(spec):
	look = {"table_header": "styled", "table_header_bg": "#f3f4f6", "table_bordered": True, "table_radius": 8}
	panel = section(
		trade_party(spec),
		[*_titles(spec, size=17), row("name", "Data", spec["number"], bold=1), linked("company.tax_id", "Our TRN", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};"), *trade_details(spec)],
		widths=[52, 48], gap=40, top=8, field_orientation="left-right",
	)
	found = [panel, trade_lines(spec, trade_columns(spec, code=True), **look), *trade_count(spec)]
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

	words, name = spec.get("party") or ("Date", None)
	facts = section(
		[field(name, "Data", words, bold=1) if name else fact(first), fact(first) if name else field("status", "Data", "Status")],
		[field("name", "Data", spec["number"], bold=1), fact(second)],
		top=20, **grid,
	)
	style = "color:#374151;line-height:1.5;"
	parties = section(
		[heading(spec.get("us", "From")), field("company", "Link", "Company", show_label="hide", bold=1),
			field(spec.get("our_address", "company_address_display"), "Small Text", "Address", show_label="hide", custom_style=style),
			_company_trn(show_label="inline")],
		trade_party(spec),
		widths=[50, 50], gap=24, top=10, radius=6, padding={"top": 14, "right": 16, "bottom": 14, "left": 16},
		custom_style=f"border:1px solid {LINE};", field_orientation="left-right",
	)
	look = {"table_bordered": True, "table_header": "styled", "table_header_bg": SOFT, "table_radius": 6}
	found = [section(_titles(spec), top=6), facts, parties, trade_lines(spec, **look), *trade_count(spec)]
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
	found = trade_master(spec)
	# ERPNext's own Proforma Invoice prints its order through this format, on
	# a copy it gives the proforma's number and date and, for a proforma by
	# amount, the word to leave out the quantities and rates.
	drawn = 'doc.get("proforma_no")'
	number = found["sections"][0]["columns"][1]["fields"]
	number[0]["visible_if"] = f"not {drawn}"
	number[:0] = [field("proforma_no", "Data", "Proforma No", show_label="hide", align="right", bold=1, font_size=14, visible_if=drawn),
		field("name", "Data", "Against Order", align="right", hide_colon=1, custom_style="margin-top:4px;", visible_if=drawn)]
	details = found["sections"][1]["columns"][1]["fields"]
	details[0]["visible_if"] = f"not {drawn}"
	details.insert(0, row("proforma_date", "Date", "Date", date_format=DATE, visible_if=drawn))
	for one in found["sections"][3]["columns"][1]["fields"]:
		# Said for the whole order, not the part asked for.
		if one["fieldname"] == "in_words":
			one["visible_if"] = f"not {drawn}"
	for column in found["sections"][2]["columns"][0]["fields"][0]["table_columns"]:
		if column["fieldname"] in ("qty", "rate"):
			column["column_condition"] = 'not doc.get("hide_item_qty")'
	return found


def purchase_voucher():
	"""ERPNext's Purchase Auditing Voucher, for the books: the supplier's
	account credited with the total, and each line's expense account and
	cost center and each tax's account debited, with room to sign."""
	head = section(
		titles(size=20, words=(("Purchase Voucher", "not doc.is_return"), ("Debit Note Voucher", "doc.is_return"))),
		[field("name", "Data", "Voucher No", align="right", bold=1, hide_colon=1),
			field("posting_date", "Date", "Date", align="right", hide_colon=1, date_format=DATE, custom_style="margin-top:4px;"),
			field("bill_no", "Data", "Supplier Invoice No", align="right", hide_colon=1, custom_style="margin-top:2px;")],
		widths=[60, 40], top=6, field_orientation="left-right",
	)
	who = section(
		[row("supplier_name", "Data", "Supplier"), row("credit_to", "Link", "Credit To"),
			linked("project.project_name", "Project", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};")],
		[row("grand_total", "Currency", "Credited", bold=1), row("net_total", "Currency", "Expense Debited"), row("total_taxes_and_charges", "Currency", "Tax Debited")],
		widths=[50, 50], gap=40, top=20, field_orientation="left-right",
	)
	look = {"table_bordered": True, "table_header": "styled", "table_header_bg": SOFT, "table_cell_padding": 6}
	lines = section([heading("Expense"), table("items", "Items", [
		{"fieldname": "item_code", "fieldtype": "Link", "label": "Item", "width": 16},
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Description", "width": 24},
		{"fieldname": "expense_account", "fieldtype": "Link", "label": "Account", "width": 22},
		{"fieldname": "cost_center", "fieldtype": "Link", "label": "Cost Center", "width": 16},
		{"fieldname": "net_amount", "fieldtype": "Currency", "label": "Debit", "width": 22, "align": "right"},
	], **look)], top=22)
	taxes = section([heading("Tax"), table("taxes", "Taxes", [
		{"fieldname": "account_head", "fieldtype": "Link", "label": "Account", "width": 40},
		{"fieldname": "cost_center", "fieldtype": "Link", "label": "Cost Center", "width": 22},
		{"fieldname": "rate", "fieldtype": "Float", "label": "Rate", "width": 16, "align": "right"},
		{"fieldname": "tax_amount", "fieldtype": "Currency", "label": "Debit", "width": 22, "align": "right"},
	], **look)], top=16, visible_if="doc.taxes")
	remarks = section([heading("Remarks"), field("remarks", "Small Text", "Remarks", show_label="hide")], top=16, visible_if="doc.remarks and doc.remarks != 'No Remarks'")
	return layout(head, who, lines, taxes, remarks, signs_section((("Prepared By", "owner"), ("Checked By", None), ("Approved By", None))))


def receipt_with_serials():
	"""ERPNext's Purchase Receipt Serial and Batch Bundle Print: the receipt,
	each line with the batch and serial numbers it came in under, as the line
	keeps them."""
	spec = TRADE["Purchase Receipt"]
	columns = [
		{"fieldname": "qty", "fieldtype": "Float", "label": "Accepted", "width": 13, "align": "right",
			"merged_fields": [{"fieldname": "uom", "fieldtype": "Link", "label": "UOM", "style": "muted-sm"}]},
		{"fieldname": "batch_no", "fieldtype": "Link", "label": "Batch", "width": 16},
		{"fieldname": "serial_no", "fieldtype": "Small Text", "label": "Serial Numbers", "width": 26},
	]
	return trade_master({**spec, "columns": columns})


# -- Money moved and asked for, and goods picked --------------------------------

RECEIVED = 'doc.payment_type == "Receive"'
PAID = 'doc.payment_type == "Pay"'


def _numbered(words, number, size=24, details=()):
	return section(
		[text(w, visible_if=when, font_size=size, bold=1, custom_style="letter-spacing:-0.01em;line-height:1.1;") if when
			else text(w, font_size=size, bold=1, custom_style="letter-spacing:-0.01em;line-height:1.1;") for w, when in words],
		[field("name", "Data", number, show_label="hide", align="right", bold=1, font_size=14), *details],
		widths=[60, 40], top=6, field_orientation="left-right",
	)


def _settles(**look):
	return [
		heading("Settles", visible_if="doc.references"),
		table("references", "Settles", [
			{"fieldname": "reference_doctype", "fieldtype": "Link", "label": "Document", "width": 22},
			{"fieldname": "reference_name", "fieldtype": "Dynamic Link", "label": "Number", "width": 28},
			{"fieldname": "due_date", "fieldtype": "Date", "label": "Due Date", "width": 16, "date_format": DATE},
			{"fieldname": "total_amount", "fieldtype": "Currency", "label": "Total", "width": 17, "align": "right"},
			{"fieldname": "allocated_amount", "fieldtype": "Currency", "label": "Paid", "width": 17, "align": "right"},
		], row_condition="row.allocated_amount", visible_if="doc.references", table_cell_padding=6, **look),
	]


def payment_receipt():
	"""A payment received prints as a receipt and one made as a payment: who
	from or to, how and when, the amount large, and what it settles."""
	head = _numbered(
		(("Receipt", RECEIVED), ("Payment", PAID), ("Transfer", 'doc.payment_type == "Internal Transfer"')),
		"Receipt No",
		details=[_company_trn(align="right", custom_style="margin-top:4px;")],
	)
	style = "color:#374151;line-height:1.5;margin-top:2px;"
	who = section(
		[
			heading("Received From", visible_if=RECEIVED),
			heading("Paid To", visible_if=PAID),
			field("party_name", "Data", "Party", show_label="hide", bold=1, font_size=13),
			field("contact_email", "Data", "Email", show_label="hide", custom_style=style),
		],
		[
			row("posting_date", "Date", "Date", date_format=DATE),
			row("mode_of_payment", "Link", "Paid By"),
			row("reference_no", "Data", "Reference"),
			row("reference_date", "Date", "Reference Date", date_format=DATE),
			linked("project.project_name", "Project", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};"),
		],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	big = "font-size:22px;font-weight:700;letter-spacing:-0.01em;"
	amount = section(
		[
			heading("Amount Received", visible_if=RECEIVED),
			heading("Amount Paid", visible_if=f"not ({RECEIVED})"),
			field("paid_amount", "Currency", "Amount Received", show_label="hide", visible_if=RECEIVED, custom_style=big),
			field("received_amount", "Currency", "Amount Paid", show_label="hide", visible_if=f"not ({RECEIVED})", custom_style=big),
			field("in_words", "Data", "In Words", show_label="hide", custom_style=f"color:{MUTED};margin-top:4px;"),
			row("unallocated_amount", "Currency", "Kept on Account", visible_if="doc.unallocated_amount"),
		],
		top=24, background=SOFT, radius=8, padding={"top": 16, "right": 18, "bottom": 16, "left": 18},
	)
	return layout(head, who, amount, section(_settles(), top=22), signs_section((("For", "company"),)))


def payment_voucher():
	"""ERPNext's Bank and Cash Payment Voucher, for the books: the accounts
	paid from and to, the amounts, what it settles and any deductions, with
	room to sign."""
	head = _numbered((("Payment Voucher", PAID), ("Receipt Voucher", RECEIVED), ("Transfer Voucher", 'doc.payment_type == "Internal Transfer"')), "Voucher No", size=20,
		details=[field("posting_date", "Date", "Date", align="right", hide_colon=1, date_format=DATE, custom_style="margin-top:4px;")])
	who = section(
		[row("party_name", "Data", "Party"), row("mode_of_payment", "Link", "Paid By"), row("reference_no", "Data", "Reference"),
			row("reference_date", "Date", "Reference Date", date_format=DATE)],
		[row("paid_from", "Link", "Paid From"), row("paid_to", "Link", "Paid To"), row("paid_amount", "Currency", "Amount", bold=1),
			row("total_taxes_and_charges", "Currency", "Tax", visible_if="doc.total_taxes_and_charges")],
		widths=[50, 50], gap=40, top=20, field_orientation="left-right",
	)
	look = {"table_bordered": True, "table_header": "styled", "table_header_bg": SOFT}
	deductions = section([heading("Deductions"), table("deductions", "Deductions", [
		{"fieldname": "account", "fieldtype": "Link", "label": "Account", "width": 45},
		{"fieldname": "cost_center", "fieldtype": "Link", "label": "Cost Center", "width": 30},
		{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "width": 25, "align": "right"},
	], table_cell_padding=6, **look)], top=16, visible_if="doc.deductions")
	remarks = section([heading("Remarks"), field("remarks", "Small Text", "Remarks", show_label="hide")], top=16, visible_if="doc.remarks")
	return layout(head, who, section(_settles(**look), top=22), deductions, remarks,
		signs_section((("Prepared By", "owner"), ("Checked By", None), ("Approved By", None))))


def journal_voucher():
	"""ERPNext's Journal Auditing Voucher: each account debited and credited,
	with its party and cost center, the totals that agree, the remark, and
	room to sign."""
	head = _numbered((("Journal Voucher", ""),), "Voucher No", size=20,
		details=[field("posting_date", "Date", "Date", align="right", hide_colon=1, date_format=DATE, custom_style="margin-top:4px;"),
			field("voucher_type", "Data", "Type", align="right", hide_colon=1, custom_style="margin-top:2px;")])
	look = {"table_bordered": True, "table_header": "styled", "table_header_bg": SOFT, "table_cell_padding": 6}
	lines = section([table("accounts", "Accounts", [
		{"fieldname": "account", "fieldtype": "Link", "label": "Account", "width": 30,
			"merged_fields": [{"fieldname": "user_remark", "fieldtype": "Small Text", "label": "Remark", "style": "muted-sm"}]},
		{"fieldname": "party", "fieldtype": "Dynamic Link", "label": "Party", "width": 20},
		{"fieldname": "cost_center", "fieldtype": "Link", "label": "Cost Center", "width": 16},
		{"fieldname": "debit", "fieldtype": "Currency", "label": "Debit", "width": 17, "align": "right"},
		{"fieldname": "credit", "fieldtype": "Currency", "label": "Credit", "width": 17, "align": "right"},
	], **look)], top=24)
	totals = section([], [row("total_debit", "Currency", "Total Debit", bold=1), row("total_credit", "Currency", "Total Credit", bold=1)],
		widths=[52, 48], gap=48, top=10, field_orientation="left-right")
	refs = section([row("cheque_no", "Data", "Reference"), row("cheque_date", "Date", "Reference Date", date_format=DATE)], [],
		widths=[52, 48], top=12, field_orientation="left-right", visible_if="doc.cheque_no")
	remark = section([heading("Remark"), field("user_remark", "Small Text", "Remark", show_label="hide")], top=16, visible_if="doc.user_remark")
	return layout(head, lines, totals, refs, remark, signs_section((("Prepared By", "owner"), ("Checked By", None), ("Approved By", None))))


def journal_credit_note():
	"""ERPNext's Credit Note on a journal entry: to whom the credit is given,
	what for, and how much, from the entry's lines that name a party."""
	head = _numbered((("Credit Note", ""),), "Credit Note No",
		details=[field("posting_date", "Date", "Date", align="right", hide_colon=1, date_format=DATE, custom_style="margin-top:4px;"),
			_company_trn(align="right", custom_style="margin-top:2px;")])
	who = section([heading("To"), field("pay_to_recd_from", "Data", "Party", show_label="hide", bold=1, font_size=13)], [],
		widths=[55, 45], top=26, visible_if="doc.pay_to_recd_from")
	lines = section([table("accounts", "Accounts", [
		{"fieldname": "party", "fieldtype": "Dynamic Link", "label": "Credited To", "width": 34},
		{"fieldname": "reference_name", "fieldtype": "Dynamic Link", "label": "Against", "width": 26},
		{"fieldname": "user_remark", "fieldtype": "Small Text", "label": "For", "width": 20},
		{"fieldname": "credit_in_account_currency", "fieldtype": "Currency", "label": "Amount", "width": 20, "align": "right"},
	], row_condition="row.party and row.credit_in_account_currency")], top=24)
	total = section([], [row("total_amount", "Currency", "Total", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
		field("total_amount_in_words", "Data", "In Words", show_label="hide", align="right", custom_style=f"color:{MUTED};font-size:10px;margin-top:6px;")],
		widths=[52, 48], gap=48, top=14, field_orientation="left-right")
	remark = section([heading("Remarks"), field("user_remark", "Small Text", "Remarks", show_label="hide", visible_if="doc.user_remark"),
		field("remark", "Small Text", "Remarks", show_label="hide", visible_if="not doc.user_remark")], top=16, visible_if="doc.user_remark or doc.remark")
	return layout(head, who, lines, total, remark, signs_section((("For", "company"),)))


def payment_reminder():
	"""A dunning, as a letter: who it's to, the letter, each invoice overdue
	and by how long, what's owed with any fee and interest, the closing
	words and the bank to pay into."""
	head = _numbered((("Payment Reminder", ""),), "Reminder No", details=[_company_trn(align="right", custom_style="margin-top:4px;")])
	who = section(
		[heading("To"), field("customer_name", "Data", "Customer", show_label="hide", bold=1, font_size=13),
			field("address_display", "Small Text", "Address", show_label="hide", custom_style="color:#374151;line-height:1.5;margin-top:2px;"),
			field("contact_display", "Data", "Contact", hide_colon=1, custom_style="margin-top:6px;")],
		[row("posting_date", "Date", "Date", date_format=DATE), row("dunning_type", "Link", "Reminder")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	letter = section([field("body_text", "Text Editor", "Letter", show_label="hide", custom_style="line-height:1.6;")], top=22, visible_if="doc.body_text")
	overdue = section([table("overdue_payments", "Overdue", [
		{"fieldname": "sales_invoice", "fieldtype": "Link", "label": "Invoice", "width": 26},
		{"fieldname": "due_date", "fieldtype": "Date", "label": "Due Date", "width": 18, "date_format": DATE},
		{"fieldname": "overdue_days", "fieldtype": "Data", "label": "Days Late", "width": 14, "align": "right"},
		{"fieldname": "outstanding", "fieldtype": "Currency", "label": "Outstanding", "width": 22, "align": "right"},
		{"fieldname": "interest", "fieldtype": "Currency", "label": "Interest", "width": 20, "align": "right"},
	])], top=20)
	totals = section([], [
		row("total_outstanding", "Currency", "Outstanding"),
		row("dunning_fee", "Currency", "Fee", visible_if="doc.dunning_fee"),
		row("total_interest", "Currency", "Interest", visible_if="doc.total_interest"),
		row("grand_total", "Currency", "Total Due", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
	], widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")
	closing = section([field("closing_text", "Text Editor", "Closing", show_label="hide", custom_style="line-height:1.6;")], top=18, visible_if="doc.closing_text")
	pay = bank_section()
	pay["visible_if"] = "doc.one_pay_into"
	return layout(head, who, letter, overdue, totals, closing, pay)


def pick_list():
	"""What to pick, from where, for which order, and two to sign that it
	was picked and checked."""
	head = _numbered((("Pick List", ""),), "Pick List No")
	who = section(
		[heading("For", visible_if="doc.customer_name"), field("customer_name", "Data", "Customer", show_label="hide", bold=1, font_size=13, visible_if="doc.customer_name")],
		[row("purpose", "Data", "Purpose"), row("parent_warehouse", "Link", "From"), row("work_order", "Link", "Work Order")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("locations", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=27),
		{"fieldname": "warehouse", "fieldtype": "Link", "label": "From", "width": 16},
		{"fieldname": "batch_no", "fieldtype": "Link", "label": "Batch", "width": 10},
		{"fieldname": "serial_no", "fieldtype": "Small Text", "label": "Serial Numbers", "width": 10},
		{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "width": 7, "align": "right",
			"merged_fields": [{"fieldname": "uom", "fieldtype": "Link", "label": "UOM", "style": "muted-sm"}]},
		{"fieldname": "picked_qty", "fieldtype": "Float", "label": "Picked", "width": 9, "align": "right"},
		{"fieldname": "sales_order", "fieldtype": "Link", "label": "Order", "width": 16},
	])], top=28)
	return layout(head, who, lines, signs_section((("Picked By", None), ("Checked By", None))))


# -- People: pay and letters ----------------------------------------------------

PAID_LINE = "row.amount and not row.statistical_component and not row.do_not_include_in_total"


def _pay_lines(fieldname, words, year=False, padding=6):
	columns = [{"fieldname": "salary_component", "fieldtype": "Link", "label": words, "width": 60 if not year else 46},
		{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "width": 40 if not year else 27, "align": "right"}]
	if year:
		columns.append({"fieldname": "year_to_date", "fieldtype": "Currency", "label": "Year to Date", "width": 27, "align": "right"})
	return table(fieldname, words, columns, row_condition=PAID_LINE, table_cell_padding=padding)


def _employee(size=13):
	return [
		heading("Employee"),
		field("employee_name", "Data", "Employee", show_label="hide", bold=1, font_size=size),
		field("designation", "Link", "Designation", show_label="hide", custom_style="color:#374151;margin-top:2px;"),
		field("department", "Link", "Department", show_label="hide", custom_style="color:#374151;"),
		linked("employee.employee", "Employee No", hide_colon=1, custom_style="margin-top:6px;"),
		linked("employee.date_of_joining", "Joined", hide_colon=1, custom_style="margin-top:2px;"),
	]


def _period():
	return [
		row("start_date", "Date", "From", date_format=DATE),
		row("end_date", "Date", "To", date_format=DATE),
		row("posting_date", "Date", "Paid On", date_format=DATE),
		row("payment_days", "Float", "Days Paid"),
		row("leave_without_pay", "Float", "Unpaid Leave", visible_if="doc.leave_without_pay"),
	]


def _net(words=True):
	found = [heading("Net Pay"), field("rounded_total", "Currency", "Net Pay", show_label="hide", custom_style="font-size:22px;font-weight:700;letter-spacing:-0.01em;")]
	if words:
		found.append(field("total_in_words", "Data", "In Words", show_label="hide", custom_style=f"color:{MUTED};margin-top:4px;"))
	return section(found, top=22, background=SOFT, radius=8, padding={"top": 16, "right": 18, "bottom": 16, "left": 18}, keep_together=1)


def _paid_into():
	"""Where the pay went, as HRMS copied it from the employee onto the slip."""
	return section([
		heading("Paid Into"),
		row("mode_of_payment", "Link", "Paid By"),
		row("bank_name", "Data", "Bank"),
		row("bank_account_no", "Data", "Account"),
	], [], widths=[52, 48], top=18, field_orientation="left-right", visible_if="doc.bank_account_no or doc.bank_name or doc.mode_of_payment")

def payslip():
	"""HRMS's Salary Slip Classic: who and for when, what was earned and what
	was taken, side by side, the net pay large with its words, and where it
	was paid."""
	return layout(
		_numbered((("Payslip", ""),), "Payslip No"),
		section(_employee(), _period(), widths=[55, 45], gap=48, top=26, field_orientation="left-right"),
		section(
			[_pay_lines("earnings", "Earnings"), row("gross_pay", "Currency", "Gross Pay", bold=1)],
			[_pay_lines("deductions", "Deductions"), row("total_deduction", "Currency", "Total Deductions", bold=1)],
			widths=[50, 50], gap=32, top=24, field_orientation="left-right",
		),
		_net(),
		_paid_into(),
	)


def payslip_compact():
	"""HRMS's Salary Slip Compact: the same on half a page, the person and
	the period on one line each, no words for the sum."""
	head = section(
		[field("employee_name", "Data", "Employee", show_label="hide", bold=1, font_size=13),
			field("designation", "Link", "Designation", show_label="hide", custom_style="color:#374151;"),
			linked("employee.employee", "Employee No", hide_colon=1, custom_style="margin-top:4px;"),
			field("payment_days", "Float", "Days Paid", hide_colon=1)],
		[field("name", "Data", "Payslip No", show_label="hide", align="right", bold=1),
			field("start_date", "Date", "From", align="right", hide_colon=1, date_format=DATE),
			field("end_date", "Date", "To", align="right", hide_colon=1, date_format=DATE)],
		widths=[60, 40], top=6, field_orientation="left-right",
	)
	pay = section(
		[_pay_lines("earnings", "Earnings", padding=4), row("gross_pay", "Currency", "Gross Pay", bold=1)],
		[_pay_lines("deductions", "Deductions", padding=4), row("total_deduction", "Currency", "Total Deductions", bold=1)],
		widths=[50, 50], gap=28, top=16, field_orientation="left-right",
	)
	net = section([], [row("rounded_total", "Currency", "Net Pay", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;")],
		widths=[52, 48], gap=48, top=10, field_orientation="left-right")
	return layout(head, pay, net)


def salary_statement():
	"""HRMS's Salary Slip Detailed, a salary statement: the payslip with
	each line's year to date, the payroll period, any income tax worked out,
	and the leave taken and left."""
	tax = "doc.total_income_tax or doc.current_month_income_tax"
	return layout(
		_numbered((("Salary Statement", ""),), "Payslip No", details=[field("current_payroll_period", "Link", "Payroll Period", align="right", hide_colon=1, custom_style="margin-top:4px;")]),
		section(_employee(), [*_period(), row("total_working_days", "Float", "Working Days")], widths=[55, 45], gap=48, top=26, field_orientation="left-right"),
		section(
			[_pay_lines("earnings", "Earnings", year=True), row("gross_pay", "Currency", "Gross Pay", bold=1), row("gross_year_to_date", "Currency", "Gross Year to Date")],
			[_pay_lines("deductions", "Deductions", year=True), row("total_deduction", "Currency", "Total Deductions", bold=1)],
			widths=[50, 50], gap=32, top=24, field_orientation="left-right",
		),
		section([heading("Income Tax"), row("annual_taxable_amount", "Currency", "Taxable This Year"), row("total_income_tax", "Currency", "Tax This Year"),
			row("income_tax_deducted_till_date", "Currency", "Deducted So Far"), row("current_month_income_tax", "Currency", "Deducted Now")], [],
			widths=[52, 48], top=20, field_orientation="left-right", visible_if=tax),
		section([heading("Leave"), table("leave_details", "Leave", [
			{"fieldname": "leave_type", "fieldtype": "Link", "label": "Leave", "width": 40},
			{"fieldname": "total_allocated_leaves", "fieldtype": "Float", "label": "Allocated", "width": 20, "align": "right"},
			{"fieldname": "used_leaves", "fieldtype": "Float", "label": "Taken", "width": 20, "align": "right"},
			{"fieldname": "available_leaves", "fieldtype": "Float", "label": "Left", "width": 20, "align": "right"},
		], table_cell_padding=5)], top=20, visible_if="doc.leave_details"),
		_net(),
		_paid_into(),
	)


def _letter_head(words, number, dated, label):
	return _numbered(((words, ""),), number, details=[field(dated, "Date", label, align="right", hide_colon=1, date_format=DATE, custom_style="margin-top:4px;")])


def job_offer():
	"""HRMS's Job Offer, as a letter: to whom, the position, each term of
	the offer, the terms and conditions, and both sides to sign."""
	who = section([heading("To"), field("applicant_name", "Data", "Applicant", show_label="hide", bold=1, font_size=13),
		field("applicant_email", "Data", "Email", show_label="hide", custom_style="color:#374151;")],
		[row("designation", "Link", "Position", bold=1)], widths=[55, 45], gap=48, top=26, field_orientation="left-right")
	offer = section([heading("The Offer"), table("offer_terms", "Offer", [
		{"fieldname": "offer_term", "fieldtype": "Link", "label": "Term", "width": 40},
		{"fieldname": "value", "fieldtype": "Small Text", "label": "Value", "width": 60},
	], table_header="none", table_cell_padding=7)], top=24, visible_if="doc.offer_terms")
	return layout(_letter_head("Job Offer", "Offer No", "offer_date", "Date"), who, offer, terms_section(),
		signs_section((("For", "company"), ("Accepted By", "applicant_name"))))


def appointment_letter():
	"""HRMS's Standard Appointment Letter: to whom, the opening words, each
	term with what it says, the closing words, and both sides to sign."""
	who = section([heading("To"), field("applicant_name", "Data", "Applicant", show_label="hide", bold=1, font_size=13)], [],
		widths=[55, 45], top=26)
	opening = section([field("introduction", "Long Text", "Introduction", show_label="hide", custom_style="line-height:1.6;")], top=20, visible_if="doc.introduction")
	terms = section([table("terms", "Terms", [
		{"fieldname": "title", "fieldtype": "Data", "label": "Term", "width": 100,
			"merged_fields": [{"fieldname": "description", "fieldtype": "Long Text", "label": "Description", "style": "secondary"}]},
	], table_header="none", table_style="plain", table_cell_padding=6)], top=16, visible_if="doc.terms")
	closing = section([field("closing_notes", "Text", "Closing", show_label="hide", custom_style="line-height:1.6;")], top=16, visible_if="doc.closing_notes")
	return layout(_letter_head("Appointment Letter", "Letter No", "appointment_date", "Date"), who, opening, terms, closing,
		signs_section((("For", "company"), ("Accepted By", "applicant_name"))))


# -- Records that move goods, make things and do work ---------------------------

ADDRESS = "color:#374151;line-height:1.5;margin-top:2px;"
TRANSFER = 'doc.purpose in ("Material Transfer", "Material Transfer for Manufacture", "Send to Subcontractor")'


def _who(words, name, *rest, visible_if=None, size=13):
	"""A heading over a name and the lines under it."""
	head = heading(words, visible_if=visible_if) if visible_if else heading(words)
	first = name if isinstance(name, dict) else field(name, "Data", words, show_label="hide", bold=1, font_size=size)
	if visible_if:
		first = {**first, "visible_if": visible_if}
	return [head, first, *rest]


def _qty(fieldname="qty", unit="uom", label="Qty", width=12):
	return {"fieldname": fieldname, "fieldtype": "Float", "label": label, "width": width, "align": "right",
		"merged_fields": [{"fieldname": unit, "fieldtype": "Link", "label": "Unit", "style": "muted-sm"}]}


def packing_slip():
	"""What's in each case of a delivery: the delivery it belongs to and who
	it goes to, the cases, each item with its weight, and both sides to sign."""
	who = section(
		_who("Deliver To", linked("delivery_note.customer_name", "Customer", show_label="hide", bold=1, font_size=13),
			linked("delivery_note.shipping_address", "Address", show_label="hide", custom_style=ADDRESS)),
		[row("delivery_note", "Link", "Delivery No"), row("from_case_no", "Int", "From Case"), row("to_case_no", "Int", "To Case"),
			row("net_weight_pkg", "Float", "Net Weight"), row("gross_weight_pkg", "Float", "Gross Weight"), row("gross_weight_uom", "Link", "Weighed In")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=49),
		{"fieldname": "batch_no", "fieldtype": "Link", "label": "Batch", "width": 14},
		_qty(unit="stock_uom", width=14),
		{"fieldname": "net_weight", "fieldtype": "Float", "label": "Net Weight", "width": 18, "align": "right",
			"merged_fields": [{"fieldname": "weight_uom", "fieldtype": "Link", "label": "Unit", "style": "muted-sm"}]},
	])], top=28)
	return layout(_numbered((("Packing Slip", ""),), "Slip No"),
		who, lines, signs_section((("Packed By", None), ("Received By", None))))


def stock_entry():
	"""Goods moved, used or received: a transfer note, an issue note or a
	goods receipt by what it's for, where they go with that place's address,
	each line from where to where, and both sides to sign."""
	titles = (
		("Transfer Note", TRANSFER),
		("Issue Note", 'doc.purpose == "Material Issue"'),
		("Goods Receipt", 'doc.purpose == "Material Receipt"'),
		("Production Note", 'doc.purpose == "Manufacture"'),
		("Stock Movement", f'not ({TRANSFER}) and doc.purpose not in ("Material Issue", "Material Receipt", "Manufacture")'),
	)
	going = "doc.to_warehouse"
	who = section(
		_who("Deliver To", "to_warehouse",
			field("target_address_display", "Small Text", "Address", show_label="hide", custom_style=ADDRESS, visible_if="doc.target_address_display"),
			# Else the store's own address, as a site keeps it.
			linked("to_warehouse.address_line_1", "Address", show_label="hide", custom_style=ADDRESS, visible_if="not doc.target_address_display"),
			linked("to_warehouse.address_line_2", "Address", show_label="hide", custom_style=ADDRESS, visible_if="not doc.target_address_display"),
			linked("to_warehouse.city", "City", show_label="hide", custom_style=ADDRESS, visible_if="not doc.target_address_display"),
			linked("to_warehouse.phone_no", "Phone", hide_colon=1, custom_style="margin-top:4px;", visible_if="not doc.target_address_display"),
			visible_if=going),
		[row("posting_date", "Date", "Date", date_format=DATE), row("stock_entry_type", "Link", "Type"), row("from_warehouse", "Link", "From"),
			row("to_warehouse", "Link", "To"), row("work_order", "Link", "Work Order"),
			linked("project.project_name", "Project", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=37),
		{"fieldname": "s_warehouse", "fieldtype": "Link", "label": "From", "width": 17},
		{"fieldname": "t_warehouse", "fieldtype": "Link", "label": "To", "width": 17},
		{"fieldname": "batch_no", "fieldtype": "Link", "label": "Batch", "width": 12},
		_qty(width=12),
	])], top=28)
	remarks = section([heading("Remarks"), field("remarks", "Small Text", "Remarks", show_label="hide")], top=16, visible_if="doc.remarks")
	return layout(_numbered(titles, "Movement No"), who, lines, remarks, signs_section((("Sent By", None), ("Received By", None))))


def blanket_order():
	"""A price and a quantity agreed for a time: with whom, from when to
	when, each item at its rate with how much is ordered so far, and the
	terms."""
	selling = 'doc.blanket_order_type == "Selling"'
	who = section(
		[heading("Agreed With"), field("customer_name", "Data", "Customer", show_label="hide", bold=1, font_size=13, visible_if=selling),
			field("supplier_name", "Data", "Supplier", show_label="hide", bold=1, font_size=13, visible_if=f"not ({selling})")],
		[row("order_date", "Date", "Date", date_format=DATE), row("from_date", "Date", "From", date_format=DATE), row("to_date", "Date", "To", date_format=DATE),
			row("order_no", "Data", "Their Reference")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=41, describe=False),
		{"fieldname": "party_item_code", "fieldtype": "Data", "label": "Their Code", "width": 14},
		_qty(unit="stock_uom", label="Agreed", width=12),
		{"fieldname": "rate", "fieldtype": "Currency", "label": "Rate", "width": 15, "align": "right"},
		{"fieldname": "ordered_qty", "fieldtype": "Float", "label": "Ordered", "width": 13, "align": "right"},
	])], top=28)
	return layout(_numbered((("Blanket Order", ""),), "Agreement No", details=[_company_trn(align="right", custom_style="margin-top:4px;")]),
		who, lines, terms_section())


def work_order():
	"""What to make, how many, for whom and by when, the materials it takes
	and where from, and each step with where and how long."""
	who = section(
		[heading("Made For", visible_if="doc.project or doc.sales_order"),
			linked("project.customer", "Customer", show_label="hide", bold=1, font_size=13),
			linked("project.project_name", "Project", hide_colon=1, custom_style="margin-top:2px;"),
			field("sales_order", "Link", "Sales Order", hide_colon=1, custom_style="margin-top:2px;")],
		[row("planned_start_date", "Datetime", "Starts On", date_format=DATE), row("expected_delivery_date", "Date", "Wanted By", date_format=DATE),
			row("status", "Data", "Status"), row("bom_no", "Link", "Bill of Materials")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	make = section(
		[heading("Make"), field("item_name", "Data", "Item", show_label="hide", bold=1, font_size=15),
			field("production_item", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};")],
		[row("qty", "Float", "Quantity", bold=1), row("stock_uom", "Link", "Unit"), row("produced_qty", "Float", "Made So Far"), row("fg_warehouse", "Link", "Into")],
		widths=[55, 45], gap=48, top=22, background=SOFT, radius=8, padding={"top": 14, "right": 16, "bottom": 14, "left": 16}, field_orientation="left-right",
	)
	materials = section([heading("Materials"), table("required_items", "Materials", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Material", "width": 45,
			"merged_fields": [{"fieldname": "item_code", "fieldtype": "Link", "label": "Item Code", "style": "muted-sm"}]},
		{"fieldname": "source_warehouse", "fieldtype": "Link", "label": "From", "width": 22},
		_qty(fieldname="required_qty", unit="stock_uom", label="Needed", width=14),
		{"fieldname": "transferred_qty", "fieldtype": "Float", "label": "Sent", "width": 14, "align": "right"},
	], table_cell_padding=6)], top=22, visible_if="doc.required_items")
	steps = section([heading("Steps"), table("operations", "Steps", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "operation", "fieldtype": "Link", "label": "Step", "width": 35},
		{"fieldname": "workstation", "fieldtype": "Link", "label": "Where", "width": 26},
		{"fieldname": "time_in_mins", "fieldtype": "Float", "label": "Minutes", "width": 17, "align": "right"},
		{"fieldname": "completed_qty", "fieldtype": "Float", "label": "Done", "width": 17, "align": "right"},
	], table_cell_padding=6)], top=18, visible_if="doc.operations")
	notes = section([heading("Notes"), field("description", "Text Editor", "Notes", show_label="hide")], top=16, visible_if="doc.description")
	return layout(_numbered((("Work Order", ""),), "Order No"), who, make, materials, steps, notes,
		signs_section((("Issued By", None), ("Made By", None))))


def equipment_handover():
	"""Equipment handed over or put away: each piece, from whom or where to
	whom or where, and both sides to sign."""
	who = section([], [row("transaction_date", "Datetime", "Date", date_format=DATE), row("purpose", "Data", "Purpose")],
		widths=[55, 45], gap=48, top=22, field_orientation="left-right")
	lines = section([table("assets", "Equipment", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "asset_name", "fieldtype": "Data", "label": "Equipment", "width": 31},
		{"fieldname": "from_employee", "fieldtype": "Link", "label": "From", "width": 16},
		{"fieldname": "source_location", "fieldtype": "Link", "label": "Was At", "width": 16},
		{"fieldname": "to_employee", "fieldtype": "Link", "label": "Handed To", "width": 16},
		{"fieldname": "target_location", "fieldtype": "Link", "label": "Kept At", "width": 16},
	])], top=24)
	words = section([text("I have received the equipment above in good order. I will look after it, and give it back when I am asked.",
		custom_style="font-size:10.5px;")], top=16, visible_if="[one for one in doc.assets if one.to_employee]")
	return layout(_numbered((("Equipment Handover", ""),), "Handover No"), who, lines, words,
		signs_section((("Handed Over By", None), ("Received By", None))))


def timesheet():
	"""Whose hours, for whom and when, each day's work, the hours billable,
	and the customer to approve them."""
	who = section(
		[*_who("Employee", "employee_name"), field("department", "Link", "Department", show_label="hide", custom_style=ADDRESS),
			field("customer", "Link", "Customer", hide_colon=1, custom_style="margin-top:6px;")],
		[row("start_date", "Date", "From", date_format=DATE), row("end_date", "Date", "To", date_format=DATE),
			linked("parent_project.project_name", "Project", label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};"),
			row("total_hours", "Float", "Hours"), row("total_billable_hours", "Float", "Billable Hours", bold=1)],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("time_logs", "Time", [
		{"fieldname": "from_time", "fieldtype": "Date", "label": "Date", "width": 14, "date_format": DATE},
		{"fieldname": "activity_type", "fieldtype": "Link", "label": "Activity", "width": 20,
			"merged_fields": [{"fieldname": "task", "fieldtype": "Link", "label": "Task", "style": "muted-sm"}]},
		{"fieldname": "description", "fieldtype": "Small Text", "label": "Work", "width": 40},
		{"fieldname": "hours", "fieldtype": "Float", "label": "Hours", "width": 12, "align": "right"},
		{"fieldname": "billing_hours", "fieldtype": "Float", "label": "Billable", "width": 14, "align": "right"},
	], table_cell_padding=6)], top=24)
	notes = section([heading("Notes"), field("note", "Text Editor", "Notes", show_label="hide")], top=16, visible_if="doc.note")
	return layout(_numbered((("Timesheet", ""),), "Timesheet No"), who, lines, notes, signs_section((("For", "company"), ("Approved By", "customer"))))


def contract():
	"""An agreement: with whom, from when to when and what for, its terms in
	full, what it requires and by when, and both sides to sign."""
	who = section(
		_who("Agreed With", "party_full_name"),
		[row("start_date", "Date", "Starts On", date_format=DATE), row("end_date", "Date", "Ends On", date_format=DATE),
			row("one_notice_period", "Data", "Notice"), row("document_name", "Dynamic Link", "For"), row("signed_on", "Datetime", "Signed On", date_format=DATE)],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	body = section([field("contract_terms", "Text Editor", "Terms", show_label="hide", custom_style="line-height:1.6;")], top=24)
	fulfil = section([heading("To Be Fulfilled"), row("fulfilment_deadline", "Date", "By", date_format=DATE),
		table("fulfilment_terms", "Fulfilment", [
			{"fieldname": "requirement", "fieldtype": "Data", "label": "Requirement", "width": 70},
			{"fieldname": "fulfilled", "fieldtype": "Check", "label": "Done", "width": 30, "align": "right"},
		], table_cell_padding=6)], top=18, visible_if="doc.requires_fulfilment", field_orientation="left-right")
	return layout(_numbered((("Contract", ""),), "Contract No"),
		who, body, fulfil, signs_section((("Authorised Signatory", None), ("For", "party_full_name"))))


def maintenance_plan():
	"""A year of visits: for whom and where, what's maintained and how often,
	and each visit, when it's due, when it was done and by whom."""
	who = section(
		[*_who("Prepared For", "customer_name"), field("address_display", "Small Text", "Address", show_label="hide", custom_style=ADDRESS), *contact_lines()],
		[row("transaction_date", "Date", "Date", date_format=DATE), row("status", "Data", "Status")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	what = section([heading("What's Maintained"), table("items", "Items", [
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Item", "width": 34,
			"merged_fields": [{"fieldname": "description", "fieldtype": "Text Editor", "label": "Description", "style": "muted-sm"}]},
		{"fieldname": "start_date", "fieldtype": "Date", "label": "From", "width": 16, "date_format": DATE},
		{"fieldname": "end_date", "fieldtype": "Date", "label": "To", "width": 16, "date_format": DATE},
		{"fieldname": "periodicity", "fieldtype": "Data", "label": "How Often", "width": 18},
		{"fieldname": "no_of_visits", "fieldtype": "Int", "label": "Visits", "width": 16, "align": "right"},
	], table_cell_padding=6)], top=24)
	visits = section([heading("Visits"), table("schedules", "Visits", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 6},
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Visit", "width": 30},
		{"fieldname": "scheduled_date", "fieldtype": "Date", "label": "Due", "width": 18, "date_format": DATE},
		{"fieldname": "actual_date", "fieldtype": "Date", "label": "Done On", "width": 18, "date_format": DATE},
		{"fieldname": "sales_person", "fieldtype": "Link", "label": "By", "width": 28},
	], table_cell_padding=6)], top=18)
	return layout(_numbered((("Maintenance Plan", ""),), "Plan No", details=[_company_trn(align="right", custom_style="margin-top:4px;")]), who, what, visits)


def service_report():
	"""A visit done: for whom and when, what kind and how it ended, each item
	seen to and the work done on it, what the customer said, and both sides
	to sign."""
	who = section(
		[*_who("Customer", "customer_name"), field("address_display", "Small Text", "Address", show_label="hide", custom_style=ADDRESS), *contact_lines()],
		[row("mntc_date", "Date", "Date", date_format=DATE), row("mntc_time", "Time", "Time"), row("maintenance_type", "Data", "Type"),
			row("completion_status", "Data", "Status", bold=1), row("maintenance_schedule", "Link", "Plan")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	work = section([table("purposes", "Work", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Item", "width": 27,
			"merged_fields": [{"fieldname": "serial_no", "fieldtype": "Link", "label": "Serial No", "style": "muted-sm"}]},
		{"fieldname": "description", "fieldtype": "Text Editor", "label": "Asked For", "width": 24},
		{"fieldname": "work_done", "fieldtype": "Small Text", "label": "Work Done", "width": 28},
		{"fieldname": "service_person", "fieldtype": "Link", "label": "By", "width": 16},
	], table_cell_padding=7)], top=24)
	said = section([heading("Customer's Feedback"), field("customer_feedback", "Small Text", "Feedback", show_label="hide", custom_style="font-style:italic;")],
		top=18, visible_if="doc.customer_feedback")
	return layout(_numbered((("Service Report", ""),), "Report No"), who, work, said,
		signs_section((("Serviced By", None), ("Accepted By", "customer_name"))))


def _project(label="Project"):
	return linked("project.project_name", label, label_justify="space-between", hide_colon=1, custom_style=f"padding:5px 0;border-bottom:1px solid {LINE};")


def _remarks(fieldname="remarks", words="Remarks"):
	return section([heading(words), field(fieldname, "Small Text", words, show_label="hide")], top=16, visible_if=f"doc.{fieldname}")


def installation_note():
	"""Goods installed at a customer's: where, when, each item with its serial
	numbers and the delivery it came on, and the customer to accept it."""
	who = section(
		[*_who("Installed For", "customer_name"), field("address_display", "Small Text", "Address", show_label="hide", custom_style=ADDRESS), *contact_lines()],
		[row("inst_date", "Date", "Date", date_format=DATE), row("inst_time", "Time", "Time"), _project()],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "one_item_name", "fieldtype": "Data", "label": "Item", "width": 45,
			"merged_fields": [{"fieldname": "item_code", "fieldtype": "Link", "label": "Item Code", "style": "muted-sm"},
				{"fieldname": "one_size", "fieldtype": "Data", "label": "Size", "style": "muted-sm"},
				{"fieldname": "description", "fieldtype": "Text Editor", "label": "Description", "style": "muted-sm"}]},
		{"fieldname": "serial_no", "fieldtype": "Small Text", "label": "Serial No", "width": 22},
		{"fieldname": "prevdoc_docname", "fieldtype": "Data", "label": "Delivery No", "width": 16},
		{"fieldname": "qty", "fieldtype": "Float", "label": "Qty", "width": 12, "align": "right"},
	])], top=28)
	words = section([text("The items above have been installed and work as they should.", custom_style="font-size:10.5px;")], top=16)
	return layout(_numbered((("Installation Note", ""),), "Note No"), who, lines, _remarks(), words,
		signs_section((("Installed By", None), ("Accepted By", "customer_name"))))


def _materials(fieldname, words, columns, **kw):
	return section([heading(words), table(fieldname, words, columns, table_cell_padding=6)], top=22, visible_if=f"doc.{fieldname}", **kw)


def subcontracting_order():
	"""Work sent out to be done: to whom, by when and where to, what they make
	at what cost, the materials we send them for it, and both sides to sign."""
	who = section(
		[*_who("Supplier", "supplier_name"), field("address_display", "Small Text", "Address", show_label="hide", custom_style=ADDRESS), *contact_lines(),
			heading("Deliver To", visible_if="doc.shipping_address_display", custom_style="margin-top:14px;"),
			field("shipping_address_display", "Small Text", "Deliver To", show_label="hide", custom_style=ADDRESS, visible_if="doc.shipping_address_display")],
		[row("transaction_date", "Date", "Date", date_format=DATE), row("schedule_date", "Date", "Required By", date_format=DATE),
			row("purchase_order", "Link", "Purchase Order"), row("supplier_warehouse", "Link", "Materials At"), _project()],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=39),
		{"fieldname": "schedule_date", "fieldtype": "Date", "label": "Required By", "width": 14, "date_format": DATE},
		_qty(unit="stock_uom", width=12),
		{"fieldname": "rate", "fieldtype": "Currency", "label": "Rate", "width": 14, "align": "right"},
		{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "width": 16, "align": "right"},
	])], top=28)
	totals = section([], [
		row("total_qty", "Float", "Total Qty"),
		row("total_additional_costs", "Currency", "Other Costs", visible_if="doc.total_additional_costs"),
		row("total", "Currency", "Total", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
	], widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")
	sent = _materials("supplied_items", "Materials We Send", [
		{"fieldname": "rm_item_code", "fieldtype": "Link", "label": "Material", "width": 40},
		{"fieldname": "main_item_code", "fieldtype": "Link", "label": "For", "width": 30},
		_qty(fieldname="required_qty", unit="stock_uom", label="Needed", width=15),
		{"fieldname": "supplied_qty", "fieldtype": "Float", "label": "Sent", "width": 15, "align": "right"},
	])
	return layout(_numbered((("Subcontracting Order", ""),), "Order No", details=[_company_trn(align="right", custom_style="margin-top:4px;")]),
		who, lines, totals, sent, signs_section((("For", "company"), ("Accepted By", "supplier_name"))))


def subcontracting_receipt():
	"""Work done and come back: from whom and into where, what was received,
	accepted and turned away at what cost, the materials it used, and both
	sides to sign."""
	who = section(
		[*_who("Received From", "supplier_name"), field("address_display", "Small Text", "Address", show_label="hide", custom_style=ADDRESS), *contact_lines()],
		[row("posting_date", "Date", "Date", date_format=DATE), row("supplier_delivery_note", "Data", "Their Delivery Note"),
			row("bill_no", "Data", "Their Invoice No"), row("return_against", "Link", "Against Receipt"), row("set_warehouse", "Link", "Into"),
			row("rejected_warehouse", "Link", "Rejected Into"), row("transporter_name", "Data", "Transporter"), row("lr_no", "Data", "Vehicle"), _project()],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{**item_column(code=True, width=33), "merged_fields": [*item_column(code=True)["merged_fields"],
			{"fieldname": "batch_no", "fieldtype": "Link", "label": "Batch", "style": "muted-sm"},
			{"fieldname": "serial_no", "fieldtype": "Small Text", "label": "Serial No", "style": "muted-sm"}]},
		_qty(fieldname="received_qty", unit="stock_uom", label="Received", width=13),
		{"fieldname": "qty", "fieldtype": "Float", "label": "Accepted", "width": 12, "align": "right"},
		{"fieldname": "rejected_qty", "fieldtype": "Float", "label": "Rejected", "width": 11, "align": "right",
			"column_condition": "[one for one in doc.items if one.rejected_qty]"},
		{"fieldname": "rate", "fieldtype": "Currency", "label": "Rate", "width": 12, "align": "right"},
		{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "width": 14, "align": "right"},
	])], top=28)
	totals = section([], [
		row("total_qty", "Float", "Total Qty"),
		row("total_additional_costs", "Currency", "Other Costs", visible_if="doc.total_additional_costs"),
		row("total", "Currency", "Total", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
		field("in_words", "Data", "In Words", show_label="hide", align="right", custom_style=f"color:{MUTED};font-size:10px;margin-top:6px;"),
	], widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")
	used = _materials("supplied_items", "Materials Used", [
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Material", "width": 40,
			"merged_fields": [{"fieldname": "rm_item_code", "fieldtype": "Link", "label": "Item Code", "style": "muted-sm"}]},
		{"fieldname": "main_item_code", "fieldtype": "Link", "label": "For", "width": 28},
		{"fieldname": "batch_no", "fieldtype": "Link", "label": "Batch", "width": 16},
		_qty(fieldname="consumed_qty", unit="stock_uom", label="Used", width=16),
	])
	titles = (("Subcontracting Receipt", "not doc.is_return"), ("Subcontracting Return", "doc.is_return"))
	return layout(_numbered(titles, "Receipt No", details=[_company_trn(align="right", custom_style="margin-top:4px;")]), who, lines, totals, used, _remarks(),
		signs_section((("Delivered By", "supplier_name"), ("Received By", None))))


def subcontracting_inward_order():
	"""Work a customer sends us to do: for whom and from which order, what we
	make and how far it has got, the materials they send for it and what has
	come in, and both sides to sign."""
	who = section(
		[*_who("Customer", "customer_name"), linked("sales_order.address_display", "Address", show_label="hide", custom_style=ADDRESS),
			linked("sales_order.contact_display", "Contact", hide_colon=1, custom_style="margin-top:6px;")],
		[row("transaction_date", "Date", "Date", date_format=DATE), row("sales_order", "Link", "Sales Order"),
			row("customer_warehouse", "Link", "Their Materials At"), row("set_delivery_warehouse", "Link", "Delivered From")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=41, describe=False),
		{"fieldname": "bom", "fieldtype": "Link", "label": "Made To", "width": 18},
		_qty(unit="stock_uom", width=12),
		{"fieldname": "produced_qty", "fieldtype": "Float", "label": "Made", "width": 12, "align": "right"},
		{"fieldname": "delivered_qty", "fieldtype": "Float", "label": "Delivered", "width": 12, "align": "right"},
	])], top=28)
	received = _materials("received_items", "Their Materials", [
		{"fieldname": "rm_item_code", "fieldtype": "Link", "label": "Material", "width": 36},
		{"fieldname": "main_item_code", "fieldtype": "Link", "label": "For", "width": 24},
		_qty(fieldname="required_qty", unit="stock_uom", label="Needed", width=14),
		{"fieldname": "received_qty", "fieldtype": "Float", "label": "Received", "width": 13, "align": "right"},
		{"fieldname": "consumed_qty", "fieldtype": "Float", "label": "Used", "width": 13, "align": "right"},
	])
	return layout(_numbered((("Subcontracting Inward Order", ""),), "Order No", details=[_company_trn(align="right", custom_style="margin-top:4px;")]),
		who, lines, received, signs_section((("For", "company"), ("Accepted By", "customer_name"))))


def payment_order():
	"""An instruction to our bank: the account to pay from, and each payment
	with whom it goes to, into which account, for what and how much, signed
	twice as a bank asks."""
	who = section(
		[heading("To"), linked("company_bank_account.bank", "Bank", show_label="hide", bold=1, font_size=13),
			linked("company_bank_account.branch_code", "Branch", hide_colon=1, custom_style="margin-top:2px;"),
			heading("Pay From", custom_style="margin-top:14px;"), linked("company_bank_account.account_name", "Account", show_label="hide"),
			linked("company_bank_account.iban", "IBAN", hide_colon=1, custom_style="margin-top:2px;font-variant-numeric:tabular-nums;"),
			linked("company_bank_account.bank_account_no", "Account No", hide_colon=1, custom_style="margin-top:2px;font-variant-numeric:tabular-nums;")],
		[row("posting_date", "Date", "Date", date_format=DATE)],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	words = section([text("Please make the payments below from our account.", custom_style="font-size:10.5px;")], top=20)
	lines = section([table("references", "Payments", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "supplier", "fieldtype": "Link", "label": "Pay To", "width": 27,
			"merged_fields": [{"fieldname": "bank_account", "fieldtype": "Link", "label": "Into", "style": "muted-sm"}]},
		{"fieldname": "reference_name", "fieldtype": "Dynamic Link", "label": "For", "width": 22,
			"merged_fields": [{"fieldname": "reference_doctype", "fieldtype": "Link", "label": "Document", "style": "muted-sm"}]},
		{"fieldname": "payment_reference", "fieldtype": "Data", "label": "Reference", "width": 16},
		{"fieldname": "mode_of_payment", "fieldtype": "Link", "label": "By", "width": 13},
		{"fieldname": "amount", "fieldtype": "Currency", "label": "Amount", "width": 17, "align": "right"},
	])], top=12)
	return layout(_numbered((("Payment Order", ""),), "Order No", details=[_company_trn(align="right", custom_style="margin-top:4px;")]),
		who, words, lines, section([_block("One Total")], top=12), signs_section((("Authorised Signatory", None), ("Authorised Signatory", None))))


def bank_guarantee():
	"""A guarantee a bank gives for us or to us: for whom, how much, from when
	to when and for what, the bank behind it, and what it cost."""
	given = 'doc.bg_type == "Providing"'
	who = section(
		[heading("Beneficiary"), field("name_of_beneficiary", "Data", "Beneficiary", show_label="hide", bold=1, font_size=13),
			field("customer", "Link", "Customer", hide_colon=1, custom_style="margin-top:6px;", visible_if="doc.customer != doc.name_of_beneficiary"),
			field("supplier", "Link", "Supplier", hide_colon=1, custom_style="margin-top:2px;", visible_if="doc.supplier != doc.name_of_beneficiary")],
		[row("amount", "Currency", "Amount", bold=1), row("start_date", "Date", "From", date_format=DATE), row("end_date", "Date", "Until", date_format=DATE),
			row("validity", "Int", "Days"), row("reference_docname", "Dynamic Link", "For"), _project()],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	bank = section(
		[heading("Issued By"), field("bank", "Link", "Bank", show_label="hide", bold=1, font_size=13),
			field("branch_code", "Data", "Branch", hide_colon=1, custom_style="margin-top:2px;"),
			field("swift_number", "Data", "SWIFT", hide_colon=1, custom_style="margin-top:2px;")],
		[row("bank_account_no", "Data", "Account No"), row("iban", "Data", "IBAN"), row("margin_money", "Currency", "Margin Money"),
			row("fixed_deposit_number", "Data", "Fixed Deposit"), row("charges", "Currency", "Charges")],
		widths=[55, 45], gap=48, top=22, background=SOFT, radius=8, padding={"top": 14, "right": 16, "bottom": 14, "left": 16}, field_orientation="left-right",
	)
	more = section([heading("Terms"), field("more_information", "Text Editor", "Terms", show_label="hide", custom_style="line-height:1.55;")],
		top=18, visible_if="doc.more_information")
	titles = (("Bank Guarantee Given", given), ("Bank Guarantee Received", f"not ({given})"))
	return layout(_numbered(titles, "Guarantee No", details=[field("bank_guarantee_number", "Data", "Bank's No", align="right", hide_colon=1, custom_style="margin-top:4px;")]),
		who, bank, more)


def material_request():
	"""Goods asked for: to buy, to move, to issue or to make by what it's
	for, where they go and by when, each item with how many, and who asked
	and who approved."""
	titles = (
		("Purchase Request", 'doc.material_request_type == "Purchase"'),
		("Transfer Request", 'doc.material_request_type == "Material Transfer"'),
		("Issue Request", 'doc.material_request_type == "Material Issue"'),
		("Production Request", 'doc.material_request_type == "Manufacture"'),
		("Subcontracting Request", 'doc.material_request_type == "Subcontracting"'),
		("Material Request", 'doc.material_request_type == "Customer Provided"'),
	)
	who = section(
		[heading("Deliver To", visible_if="doc.set_warehouse"), field("set_warehouse", "Link", "Deliver To", show_label="hide", bold=1, font_size=13),
			heading("From Customer", visible_if="doc.customer", custom_style="margin-top:14px;"),
			field("customer", "Link", "Customer", show_label="hide", bold=1, font_size=13)],
		[row("transaction_date", "Date", "Date", date_format=DATE), row("schedule_date", "Date", "Required By", date_format=DATE),
			row("set_from_warehouse", "Link", "From"), row("work_order", "Link", "Work Order"), row("job_card", "Link", "Job Card"), row("status", "Data", "Status")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("items", "Items", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=36),
		{"fieldname": "from_warehouse", "fieldtype": "Link", "label": "From", "width": 15},
		{"fieldname": "warehouse", "fieldtype": "Link", "label": "Into", "width": 16},
		{"fieldname": "schedule_date", "fieldtype": "Date", "label": "Required By", "width": 14, "date_format": DATE},
		_qty(width=14),
	])], top=28)
	return layout(_numbered(titles, "Request No"), who, lines, terms_section(), signs_section((("Requested By", None), ("Approved By", None))))


def delivery_trip():
	"""A driver's run: who drives what and when they leave, each stop in
	order with the customer, the address, who to ask for and what is
	dropped, room to mark each one done, and both sides to sign."""
	who = section(
		[*_who("Driver", "driver_name"), field("vehicle", "Link", "Vehicle", hide_colon=1, custom_style="margin-top:6px;")],
		[row("departure_time", "Datetime", "Leaves", date_format=DATE), row("total_distance", "Float", "Distance"), row("uom", "Link", "Measured In"),
			row("status", "Data", "Status")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	stops = section([table("delivery_stops", "Stops", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "customer", "fieldtype": "Link", "label": "Customer", "width": 33,
			"merged_fields": [{"fieldname": "customer_address", "fieldtype": "Small Text", "label": "Address", "style": "muted-sm"}]},
		{"fieldname": "customer_contact", "fieldtype": "Small Text", "label": "Ask For", "width": 18},
		{"fieldname": "delivery_note", "fieldtype": "Link", "label": "Delivery No", "width": 16,
			"merged_fields": [{"fieldname": "details", "fieldtype": "Small Text", "label": "Notes", "style": "muted-sm"}]},
		{"fieldname": "estimated_arrival", "fieldtype": "Datetime", "label": "Arrive By", "width": 16},
		{"fieldname": "visited", "fieldtype": "Check", "label": "Done", "width": 12, "align": "right"},
	], table_cell_padding=7)], top=28)
	return layout(_numbered((("Delivery Trip", ""),), "Trip No"), who, stops, signs_section((("Dispatched By", None), ("Driver", "driver_name"))))


def quality_inspection():
	"""An item checked: what and from where, when and by whom, each reading
	against what it should be, whether it passed, and both to sign."""
	passed = 'doc.status == "Accepted"'
	who = section(
		[heading("Item"), field("item_name", "Data", "Item", show_label="hide", bold=1, font_size=13),
			field("item_code", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};"),
			field("description", "Small Text", "Description", show_label="hide", custom_style=ADDRESS),
			field("batch_no", "Link", "Batch", hide_colon=1, custom_style="margin-top:6px;"),
			field("item_serial_no", "Link", "Serial No", hide_colon=1, custom_style="margin-top:2px;")],
		[row("report_date", "Date", "Date", date_format=DATE), row("inspection_type", "Data", "Inspection"), row("reference_name", "Dynamic Link", "For"),
			row("sample_size", "Float", "Sample Size"), row("inspected_by", "Link", "Inspected By"),
			text("Accepted", visible_if=passed, align="right", custom_style=PILL + "background:#dcfce7;color:#166534;"),
			text("Rejected", visible_if='doc.status == "Rejected"', align="right", custom_style=PILL + "background:#fee2e2;color:#991b1b;")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	measured = "[one for one in doc.readings if one.numeric]"
	readings = section([table("readings", "Readings", [
		{"fieldname": "specification", "fieldtype": "Link", "label": "Check", "width": 26},
		{"fieldname": "value", "fieldtype": "Data", "label": "Should Be", "width": 14},
		{"fieldname": "min_value", "fieldtype": "Float", "label": "Min", "width": 9, "align": "right", "column_condition": measured},
		{"fieldname": "max_value", "fieldtype": "Float", "label": "Max", "width": 9, "align": "right", "column_condition": measured},
		{"fieldname": "reading_1", "fieldtype": "Data", "label": "1", "width": 8, "align": "right"},
		{"fieldname": "reading_2", "fieldtype": "Data", "label": "2", "width": 8, "align": "right"},
		{"fieldname": "reading_3", "fieldtype": "Data", "label": "3", "width": 8, "align": "right"},
		{"fieldname": "reading_value", "fieldtype": "Data", "label": "Found", "width": 10},
		{"fieldname": "status", "fieldtype": "Data", "label": "Result", "width": 10, "align": "right"},
	], table_cell_padding=7)], top=28, visible_if="doc.readings")
	return layout(_numbered((("Quality Inspection", ""),), "Report No"), who, readings, _remarks(),
		signs_section((("Inspected By", None), ("Verified By", "verified_by"))))


def payment_request():
	"""A request to be paid, or to pay: to whom, for what, how much, how to
	pay it with the bank and a link, and the message."""
	inward = 'doc.payment_request_type == "Inward"'
	who = section(
		[heading("Bill To", visible_if=inward), heading("Pay To", visible_if=f"not ({inward})"),
			field("party_name", "Data", "Party", show_label="hide", bold=1, font_size=13),
			field("email_to", "Data", "Email", hide_colon=1, custom_style="margin-top:6px;"),
			field("phone_number", "Data", "Phone", hide_colon=1, custom_style="margin-top:2px;")],
		[row("transaction_date", "Date", "Date", date_format=DATE), row("reference_name", "Dynamic Link", "For"),
			row("mode_of_payment", "Link", "Pay By"),
			row("grand_total", "Currency", "Amount Due", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
			row("outstanding_amount", "Currency", "Still Owed", visible_if="doc.outstanding_amount and doc.outstanding_amount != doc.grand_total")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	# Its message is a template ERPNext renders only into the email, so the
	# paper says the request in its own words.
	message = section([text("Please pay the amount above, quoting this request's number.", custom_style="font-size:10.5px;")],
		top=22, visible_if=inward)
	bank = section(
		[heading("Pay Into"), field("bank", "Link", "Bank", hide_colon=1, custom_style="padding:2px 0;"),
			field("iban", "Data", "IBAN", hide_colon=1, custom_style="padding:2px 0;font-variant-numeric:tabular-nums;"),
			field("bank_account_no", "Data", "Account No", hide_colon=1, custom_style="padding:2px 0;"),
			field("swift_number", "Data", "SWIFT", hide_colon=1, custom_style="padding:2px 0;")],
		[heading("Pay Online", visible_if="doc.payment_url"), field("payment_url", "Data", "Link", show_label="hide", visible_if="doc.payment_url", custom_style="word-break:break-all;")],
		widths=[52, 48], gap=48, top=22, keep_together=1, field_orientation="left-right", visible_if=f"{inward} and (doc.bank or doc.payment_url)",
	)
	return layout(_numbered((("Payment Request", ""),), "Request No", details=[_company_trn(align="right", custom_style="margin-top:4px;")]), who, message, bank)


def expense_claim():
	"""What an employee spent for the company: each expense, what was
	claimed and what's approved, tax, any advance taken off, what's owed
	them, and both to sign."""
	who = section(
		[*_who("Employee", "employee_name"), field("department", "Link", "Department", show_label="hide", custom_style=ADDRESS)],
		[row("posting_date", "Date", "Date", date_format=DATE), row("expense_approver", "Link", "Approver"), row("approval_status", "Data", "Approval"),
			_project(), row("task", "Link", "Task")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	lines = section([table("expenses", "Expenses", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		{"fieldname": "expense_date", "fieldtype": "Date", "label": "Date", "width": 15, "date_format": DATE},
		{"fieldname": "expense_type", "fieldtype": "Link", "label": "Expense", "width": 46,
			"merged_fields": [{"fieldname": "description", "fieldtype": "Text Editor", "label": "Description", "style": "muted-sm"}]},
		{"fieldname": "amount", "fieldtype": "Currency", "label": "Claimed", "width": 17, "align": "right"},
		{"fieldname": "sanctioned_amount", "fieldtype": "Currency", "label": "Approved", "width": 17, "align": "right",
			"column_condition": "doc.total_sanctioned_amount"},
	])], top=28)
	advances = [heading("Advances", visible_if="doc.advances"), table("advances", "Advances", [
		{"fieldname": "employee_advance", "fieldtype": "Link", "label": "Advance", "width": 40},
		{"fieldname": "posting_date", "fieldtype": "Date", "label": "Date", "width": 30, "date_format": DATE},
		{"fieldname": "allocated_amount", "fieldtype": "Currency", "label": "Taken Off", "width": 30, "align": "right"},
	], visible_if="doc.advances", table_cell_padding=6)]
	totals = section(advances, [
		row("total_claimed_amount", "Currency", "Claimed"),
		row("total_sanctioned_amount", "Currency", "Approved", visible_if="doc.total_sanctioned_amount"),
		row("total_taxes_and_charges", "Currency", "Tax", visible_if="doc.total_taxes_and_charges"),
		row("total_advance_amount", "Currency", "Less Advance", visible_if="doc.total_advance_amount"),
		row("grand_total", "Currency", "To Pay", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
	], widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")
	return layout(_numbered((("Expense Claim", ""),), "Claim No"), who, lines, totals, _remarks("remark"),
		signs_section((("Claimed By", "employee_name"), ("Approved By", "expense_approver"))))


def employee_advance():
	"""Money given ahead to an employee: to whom, how much and what for, how
	it's paid, what has been spent against it and given back, and both to
	sign."""
	who = section(
		[*_who("Employee", "employee_name"), field("department", "Link", "Department", show_label="hide", custom_style=ADDRESS)],
		[row("posting_date", "Date", "Date", date_format=DATE), row("mode_of_payment", "Link", "Paid By"),
			row("advance_amount", "Currency", "Amount", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
			row("paid_amount", "Currency", "Paid", visible_if="doc.paid_amount"), row("claimed_amount", "Currency", "Spent", visible_if="doc.claimed_amount"),
			row("return_amount", "Currency", "Given Back", visible_if="doc.return_amount"),
			row("pending_amount", "Currency", "Still Out", bold=1, visible_if="doc.pending_amount")],
		widths=[55, 45], gap=48, top=26, field_orientation="left-right",
	)
	purpose = section([heading("For"), field("purpose", "Small Text", "Purpose", show_label="hide", custom_style="line-height:1.55;")], top=22)
	words = section([text("Whatever is not spent and not given back is taken from my salary.", custom_style="font-size:10.5px;")],
		top=14, visible_if="doc.repay_unclaimed_amount_from_salary")
	return layout(_numbered((("Employee Advance", ""),), "Advance No"), who, purpose, words,
		signs_section((("Received By", "employee_name"), ("Approved By", None))))


def job_card():
	"""One step of a work order on the floor: what's made and how many, the
	step and where, the materials it takes, each stretch of time and who
	worked it, and the operator and supervisor to sign."""
	make = section(
		[heading("Make"), field("item_name", "Data", "Item", show_label="hide", bold=1, font_size=15),
			field("production_item", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};")],
		[row("for_quantity", "Float", "Quantity", bold=1), row("stock_uom", "Link", "Unit"), row("total_completed_qty", "Float", "Done So Far")],
		widths=[55, 45], gap=48, top=22, background=SOFT, radius=8, padding={"top": 14, "right": 16, "bottom": 14, "left": 16}, field_orientation="left-right",
	)
	step = section(
		[heading("Step"), field("operation", "Link", "Step", show_label="hide", bold=1, font_size=13),
			field("workstation", "Link", "Where", hide_colon=1, custom_style="margin-top:4px;")],
		[row("work_order", "Link", "Work Order"), row("expected_start_date", "Datetime", "Starts", date_format=DATE),
			row("expected_end_date", "Datetime", "Ends", date_format=DATE), row("wip_warehouse", "Link", "Work In Progress At"), _project()],
		widths=[55, 45], gap=48, top=22, field_orientation="left-right",
	)
	materials = _materials("items", "Materials", [
		{"fieldname": "item_name", "fieldtype": "Data", "label": "Material", "width": 44,
			"merged_fields": [{"fieldname": "item_code", "fieldtype": "Link", "label": "Item Code", "style": "muted-sm"}]},
		{"fieldname": "source_warehouse", "fieldtype": "Link", "label": "From", "width": 24},
		_qty(fieldname="required_qty", unit="stock_uom", label="Needed", width=16),
		{"fieldname": "transferred_qty", "fieldtype": "Float", "label": "Sent", "width": 16, "align": "right"},
	])
	times = section([heading("Time"), table("time_logs", "Time", [
		{"fieldname": "from_time", "fieldtype": "Datetime", "label": "From", "width": 24},
		{"fieldname": "to_time", "fieldtype": "Datetime", "label": "To", "width": 24},
		{"fieldname": "employee", "fieldtype": "Link", "label": "Who", "width": 24},
		{"fieldname": "time_in_mins", "fieldtype": "Float", "label": "Minutes", "width": 14, "align": "right"},
		{"fieldname": "completed_qty", "fieldtype": "Float", "label": "Done", "width": 14, "align": "right"},
	], table_cell_padding=6), row("total_time_in_mins", "Float", "Total Minutes", bold=1)], top=18, field_orientation="left-right", visible_if="doc.time_logs")
	return layout(_numbered((("Job Card", ""),), "Card No"), make, step, materials, times, _remarks(),
		signs_section((("Operator", None), ("Supervisor", None))))


def bill_of_materials():
	"""How one thing is made: what and how many, each material at its cost,
	each step with where and how long, and what it all costs."""
	make = section(
		[heading("Makes"), field("item_name", "Data", "Item", show_label="hide", bold=1, font_size=15),
			field("item", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};"),
			field("description", "Small Text", "Description", show_label="hide", custom_style=ADDRESS)],
		[row("quantity", "Float", "Quantity", bold=1), row("uom", "Link", "Unit"), _project(), row("routing", "Link", "Routing")],
		widths=[55, 45], gap=48, top=22, background=SOFT, radius=8, padding={"top": 14, "right": 16, "bottom": 14, "left": 16}, field_orientation="left-right",
	)
	materials = section([heading("Materials"), table("items", "Materials", [
		{"fieldname": "idx", "fieldtype": "Int", "label": "No", "width": 5},
		item_column(code=True, width=45, describe=False),
		{"fieldname": "operation", "fieldtype": "Link", "label": "At Step", "width": 16},
		_qty(width=12),
		{"fieldname": "rate", "fieldtype": "Currency", "label": "Rate", "width": 10, "align": "right"},
		{"fieldname": "amount", "fieldtype": "Currency", "label": "Cost", "width": 12, "align": "right"},
	], table_cell_padding=6)], top=24)
	steps = _materials("operations", "Steps", [
		{"fieldname": "operation", "fieldtype": "Link", "label": "Step", "width": 32},
		{"fieldname": "workstation", "fieldtype": "Link", "label": "Where", "width": 26},
		{"fieldname": "time_in_mins", "fieldtype": "Float", "label": "Minutes", "width": 14, "align": "right"},
		{"fieldname": "hour_rate", "fieldtype": "Currency", "label": "Per Hour", "width": 14, "align": "right"},
		{"fieldname": "operating_cost", "fieldtype": "Currency", "label": "Cost", "width": 14, "align": "right"},
	])
	costs = section([], [
		row("raw_material_cost", "Currency", "Materials"),
		row("operating_cost", "Currency", "Steps", visible_if="doc.operating_cost"),
		row("total_cost", "Currency", "Total Cost", bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;"),
	], widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")
	return layout(_numbered((("Bill of Materials", ""),), "BOM No"), make, materials, steps, costs)


# -- The rest, drawn from a few parts ------------------------------------------

NUMERIC = ("Float", "Int", "Currency", "Percent")
DATED = ("Date", "Datetime")


def _r(fieldname, fieldtype, label, **kw):
	"""A ruled row, dated the One way when it's a date."""
	if fieldtype in DATED:
		kw.setdefault("date_format", DATE)
	return row(fieldname, fieldtype, label, **kw)


def _c(fieldname, fieldtype, label, width, *merged, **kw):
	"""A table column, numbers to the right, dates the One way, and the
	fields merged under it small and muted."""
	col = {"fieldname": fieldname, "fieldtype": fieldtype, "label": label, "width": width, **kw}
	if fieldtype in NUMERIC:
		col.setdefault("align", "right")
	if fieldtype in DATED:
		col.setdefault("date_format", DATE)
	if merged:
		col["merged_fields"] = [{"fieldname": f, "fieldtype": t, "label": words, "style": "muted-sm"} for f, t, words in merged]
	return col


def _pair(left, right, top=26, **kw):
	return section(left, right, widths=[55, 45], gap=48, top=top, field_orientation="left-right", **kw)


def _head(words, name, *rest, size=13):
	"""A heading over a name and the lines under it, each line shown only
	when it says something."""
	return [heading(words), field(name, "Data", words, show_label="hide", bold=1, font_size=size), *rest]


def _line(fieldname, fieldtype, label, **kw):
	return field(fieldname, fieldtype, label, hide_colon=1, custom_style="margin-top:4px;" + kw.pop("custom_style", ""), **kw)


def _muted(fieldname, fieldtype="Small Text", label="Description"):
	return field(fieldname, fieldtype, label, show_label="hide", custom_style=ADDRESS)


def _list(fieldname, words, columns, top=22, **kw):
	"""A heading over a table, both only when it has rows."""
	return section([heading(words), table(fieldname, words, columns, table_cell_padding=6)], top=top, visible_if=f"doc.{fieldname}", **kw)


def _lines(fieldname, words, columns, top=28):
	return section([table(fieldname, words, columns)], top=top, visible_if=f"doc.{fieldname}")


def _note(fieldname, words, fieldtype="Small Text"):
	return section([heading(words), field(fieldname, fieldtype, words, show_label="hide", custom_style="line-height:1.55;")],
		top=18, visible_if=f"doc.{fieldname}")


def _total(fieldname, label):
	return row(fieldname, "Currency", label, bold=1, label_color=INK, font_size=15, custom_style=f"border-bottom:2px solid {INK};padding:8px 0;")


def _sums(*rows, left=()):
	return section(list(left), list(rows), widths=[52, 48], gap=48, top=14, keep_together=1, field_orientation="left-right")


def _paper(words, number, *body, signs=None, trn=False):
	"""A title and its number, the body, and the people to sign."""
	if isinstance(words, str):
		words = ((words, ""),)
	details = [_company_trn(align="right", custom_style="margin-top:4px;")] if trn else ()
	found = [_numbered(words, number, details=details), *body]
	if signs:
		found.append(signs_section(signs))
	return layout(*found)


PREPARED = (("Prepared By", None), ("Approved By", None))


def asset():
	"""An asset's card: what it is and where, who keeps it, what it cost and
	is worth now, how it's written down, and its insurance."""
	return _paper("Asset Card", "Asset No",
		_pair(
			[*_head("Asset", "asset_name", size=15), field("item_code", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};"),
				_line("asset_category", "Link", "Category"), _line("location", "Link", "Kept At"), _line("custodian", "Link", "Kept By"),
				_line("department", "Link", "Department"), field("image", "Attach Image", "Image", show_label="hide", custom_style="margin-top:10px;max-width:160px;")],
			[_r("purchase_date", "Date", "Bought On"), _r("available_for_use_date", "Date", "In Use From"), _r("asset_quantity", "Int", "Quantity"),
				_r("net_purchase_amount", "Currency", "Bought For"), _r("additional_asset_cost", "Currency", "Added Since"),
				_r("total_asset_cost", "Currency", "Total Cost", bold=1), _r("value_after_depreciation", "Currency", "Worth Now", bold=1),
				_r("status", "Data", "Status"), _r("disposal_date", "Date", "Disposed On")],
		),
		_list("finance_books", "Written Down", [
			_c("depreciation_method", "Data", "Method", 28), _c("total_number_of_depreciations", "Int", "Times", 14),
			_c("frequency_of_depreciation", "Int", "Every (Months)", 18), _c("depreciation_start_date", "Date", "From", 18),
			_c("expected_value_after_useful_life", "Currency", "Worth at the End", 22)]),
		_pair([heading("Insurance", visible_if="doc.insurer"), field("insurer", "Data", "Insurer", show_label="hide", bold=1),
				_line("policy_number", "Data", "Policy No")],
			[_r("insured_value", "Data", "Insured For"), _r("insurance_start_date", "Date", "From"), _r("insurance_end_date", "Date", "Until")],
			top=22, visible_if="doc.insurer or doc.policy_number"),
		_note("purchase_invoice", "Bought On Invoice", "Link"),
	)


def asset_capitalization():
	"""Stock, assets and services put together into one asset: what it makes,
	each part with its value, and what it all comes to."""
	return _paper("Asset Capitalization", "Capitalization No",
		_pair(_head("Makes", "target_asset_name", field("target_item_code", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};")),
			[_r("posting_date", "Date", "Date"), _r("target_asset", "Link", "Asset"), _project()]),
		_list("stock_items", "Stock Used", [
			_c("item_name", "Data", "Item", 40, ("item_code", "Link", "Item Code"), ("batch_no", "Link", "Batch")),
			_c("warehouse", "Link", "From", 20), _qty(fieldname="stock_qty", unit="stock_uom", width=12),
			_c("valuation_rate", "Currency", "Rate", 13), _c("amount", "Currency", "Amount", 15)], top=24),
		_list("asset_items", "Assets Used", [
			_c("asset_name", "Data", "Asset", 60, ("asset", "Link", "Asset No")), _c("asset_value", "Currency", "Value", 40)]),
		_list("service_items", "Services", [
			_c("item_name", "Data", "Service", 48, ("item_code", "Link", "Item Code")), _qty(width=14),
			_c("rate", "Currency", "Rate", 18), _c("amount", "Currency", "Amount", 20)]),
		_sums(_r("stock_items_total", "Currency", "Stock", visible_if="doc.stock_items_total"),
			_r("asset_items_total", "Currency", "Assets", visible_if="doc.asset_items_total"),
			_r("service_items_total", "Currency", "Services", visible_if="doc.service_items_total"),
			_total("total_value", "Total")),
		signs=PREPARED,
	)


def asset_maintenance_log():
	"""A maintenance job on an asset: which, what was due and when, what was
	done and by whom, and both to sign."""
	return _paper("Maintenance Record", "Record No",
		_pair([heading("Asset"), field("item_name", "Data", "Item", show_label="hide", bold=1, font_size=13),
				field("asset_name", "Data", "Asset", show_label="hide", custom_style=f"color:{MUTED};")],
			[_r("task_name", "Data", "Task"), _r("maintenance_type", "Data", "Type"), _r("periodicity", "Data", "How Often"),
				_r("due_date", "Date", "Due"), _r("completion_date", "Date", "Done On"), _r("maintenance_status", "Data", "Status", bold=1),
				_r("assign_to_name", "Data", "Done By")]),
		_note("description", "What's Asked", "Text Editor"),
		_note("actions_performed", "What Was Done", "Text Editor"),
		signs=(("Done By", "assign_to_name"), ("Checked By", None)),
	)


def asset_repair():
	"""A repair: what failed and when, what was done and how long it was
	down, the parts used and the bills, what it all cost, and both to sign."""
	return _paper("Repair Record", "Repair No",
		_pair(_head("Asset", "asset_name", field("asset", "Link", "Asset No", show_label="hide", custom_style=f"color:{MUTED};")),
			[_r("failure_date", "Datetime", "Failed On"), _r("completion_date", "Datetime", "Fixed On"), _r("downtime", "Data", "Down For"),
				_r("repair_status", "Data", "Status", bold=1), _project()]),
		_note("description", "What Failed", "Long Text"),
		_note("actions_performed", "What Was Done", "Long Text"),
		_list("stock_items", "Parts Used", [
			_c("item_code", "Link", "Part", 36), _c("warehouse", "Link", "From", 22), _c("consumed_quantity", "Data", "Qty", 12, align="right"),
			_c("valuation_rate", "Currency", "Rate", 14), _c("total_value", "Currency", "Amount", 16)]),
		_list("invoices", "Bills", [_c("purchase_invoice", "Link", "Invoice", 60), _c("repair_cost", "Currency", "Amount", 40)]),
		_sums(_r("repair_cost", "Currency", "Repair", visible_if="doc.repair_cost"),
			_r("consumed_items_cost", "Currency", "Parts", visible_if="doc.consumed_items_cost"),
			_total("total_repair_cost", "Total")),
		signs=(("Repaired By", None), ("Accepted By", None)),
	)


def asset_shift_allocation():
	"""An asset written down by the shifts it works: each date, the shift
	and the amount."""
	return _paper("Shift Depreciation", "Allocation No",
		_pair([heading("Asset"), field("asset", "Link", "Asset", show_label="hide", bold=1, font_size=13)], [_r("finance_book", "Link", "Finance Book")]),
		_lines("depreciation_schedule", "Schedule", [
			_c("schedule_date", "Date", "Date", 22), _c("shift", "Link", "Shift", 22), _c("depreciation_amount", "Currency", "Written Down", 28),
			_c("accumulated_depreciation_amount", "Currency", "So Far", 28)]),
	)


def asset_value_adjustment():
	"""An asset's value changed: from what to what, the difference and where
	it's booked, and who approved it."""
	return _paper("Asset Value Adjustment", "Adjustment No",
		_pair([heading("Asset"), field("asset", "Link", "Asset", show_label="hide", bold=1, font_size=13), _line("asset_category", "Link", "Category")],
			[_r("date", "Date", "Date"), _r("current_asset_value", "Currency", "Was Worth"), _r("new_asset_value", "Currency", "Now Worth", bold=1),
				_r("difference_amount", "Currency", "Difference"), _r("difference_account", "Link", "Booked To"), _r("journal_entry", "Link", "Journal Entry")]),
		signs=PREPARED,
	)


def bom_creator():
	"""A product's whole tree of parts drafted at once: what it makes, each
	part with what it goes into, and what the materials cost."""
	return _paper("BOM Draft", "Draft No",
		_pair(_head("Makes", "item_name", field("item_code", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};"), size=15),
			[_r("qty", "Float", "Quantity", bold=1), _r("uom", "Link", "Unit"), _project(), _r("status", "Data", "Status")]),
		_lines("items", "Parts", [
			_c("item_name", "Data", "Part", 34, ("item_code", "Link", "Item Code")), _c("fg_item", "Link", "Goes Into", 22),
			_qty(width=14), _c("rate", "Currency", "Rate", 14), _c("amount", "Currency", "Amount", 16)]),
		_sums(_total("raw_material_cost", "Materials")),
		_note("remarks", "Notes", "Text Editor"),
	)


def bank_transaction():
	"""A line off the bank statement: when, in or out, from or to whom, and
	what it was matched to."""
	return _paper("Bank Transaction", "Transaction No",
		_pair([heading("Account"), field("bank_account", "Link", "Account", show_label="hide", bold=1, font_size=13),
				_muted("description"), _line("bank_party_name", "Data", "From or To"), _line("bank_party_iban", "Data", "Their IBAN")],
			[_r("date", "Date", "Date"), _r("deposit", "Currency", "In", bold=1, visible_if="doc.deposit"),
				_r("withdrawal", "Currency", "Out", bold=1, visible_if="doc.withdrawal"), _r("reference_number", "Small Text", "Reference"),
				_r("party", "Dynamic Link", "Party"), _r("status", "Data", "Status")]),
		_list("payment_entries", "Matched To", [
			_c("payment_document", "Link", "Document", 26), _c("payment_entry", "Dynamic Link", "Number", 30),
			_c("clearance_date", "Date", "Cleared On", 20), _c("allocated_amount", "Currency", "Amount", 24)], top=24),
		_sums(_r("allocated_amount", "Currency", "Matched"), _r("unallocated_amount", "Currency", "Not Matched", bold=1, visible_if="doc.unallocated_amount")),
	)


def budget():
	"""A budget: for what, which account, the years it covers, how much, and
	how it's spread."""
	return _paper("Budget", "Budget No",
		_pair([heading("For"), field("cost_center", "Link", "Cost Center", show_label="hide", bold=1, font_size=13),
				field("project", "Link", "Project", show_label="hide", bold=1, font_size=13), _line("account", "Link", "Account")],
			[_r("from_fiscal_year", "Link", "From Year"), _r("to_fiscal_year", "Link", "To Year"), _r("budget_start_date", "Date", "Starts"),
				_r("budget_end_date", "Date", "Ends"), _r("distribution_frequency", "Data", "Spread"), _total("budget_amount", "Budget")]),
		_list("budget_distribution", "Spread", [
			_c("start_date", "Date", "From", 25), _c("end_date", "Date", "To", 25), _c("percent", "Percent", "Share", 20), _c("amount", "Currency", "Amount", 30)], top=24),
		signs=PREPARED,
	)


def cost_center_allocation():
	"""A cost center's costs shared out: from when, and each share."""
	return _paper("Cost Allocation", "Allocation No",
		_pair([heading("Shared From"), field("main_cost_center", "Link", "Cost Center", show_label="hide", bold=1, font_size=13)],
			[_r("valid_from", "Date", "From")]),
		_lines("allocation_percentages", "Shares", [_c("cost_center", "Link", "To", 70), _c("percentage", "Percent", "Share", 30)]),
		signs=PREPARED,
	)


def exchange_rate_revaluation():
	"""Foreign balances valued again: each account at the old rate and the
	new, the gain or loss, and the total."""
	return _paper("Exchange Rate Revaluation", "Revaluation No",
		_pair([], [_r("posting_date", "Date", "Date")], top=18),
		_lines("accounts", "Accounts", [
			_c("account", "Link", "Account", 28, ("party", "Dynamic Link", "Party")), _c("account_currency", "Link", "Currency", 10),
			_c("balance_in_account_currency", "Currency", "Balance", 16), _c("current_exchange_rate", "Float", "Old Rate", 12),
			_c("new_exchange_rate", "Float", "New Rate", 12), _c("gain_loss", "Currency", "Gain or Loss", 22)], top=22),
		_sums(_r("gain_loss_booked", "Currency", "Booked", visible_if="doc.gain_loss_booked"),
			_r("gain_loss_unbooked", "Currency", "Not Booked", visible_if="doc.gain_loss_unbooked"), _total("total_gain_loss", "Total")),
		signs=PREPARED,
	)


def invoice_discounting():
	"""Invoices sold to a bank for cash now: the loan, each invoice, and the
	charges."""
	return _paper("Invoice Discounting", "Discounting No",
		_pair([heading("Bank"), field("bank_account", "Link", "Bank Account", show_label="hide", bold=1, font_size=13),
				_line("short_term_loan", "Link", "Loan Account")],
			[_r("posting_date", "Date", "Date"), _r("loan_start_date", "Date", "Loan From"), _r("loan_period", "Int", "Days"),
				_r("loan_end_date", "Date", "Loan Until"), _r("status", "Data", "Status")]),
		_lines("invoices", "Invoices", [
			_c("sales_invoice", "Link", "Invoice", 26), _c("customer", "Link", "Customer", 32), _c("posting_date", "Date", "Date", 18),
			_c("outstanding_amount", "Currency", "Owed", 24)]),
		_sums(_total("total_amount", "Total"), _r("bank_charges", "Currency", "Bank Charges", visible_if="doc.bank_charges")),
		signs=(("Authorised Signatory", None), ("For the Bank", None)),
	)


def item_standard_cost():
	"""An item's standard cost from a date."""
	return _paper("Standard Cost", "Cost No",
		_pair([heading("Item"), field("item_code", "Link", "Item", show_label="hide", bold=1, font_size=13)],
			[_r("effective_date", "Date", "From"), _total("standard_rate", "Standard Cost"), _r("revaluation_entry", "Link", "Revaluation")]),
		signs=PREPARED,
	)


def landed_cost_voucher():
	"""What it cost to land goods, shared over them: the receipts, the
	charges, and each item with its share."""
	return _paper("Landed Cost", "Voucher No",
		_pair([], [_r("posting_date", "Date", "Date"), _r("distribute_charges_based_on", "Data", "Shared By")], top=18),
		_list("purchase_receipts", "Receipts", [
			_c("receipt_document", "Dynamic Link", "Receipt", 28, ("receipt_document_type", "Data", "Document")), _c("supplier", "Link", "Supplier", 32),
			_c("posting_date", "Date", "Date", 18), _c("grand_total", "Currency", "Total", 22)]),
		_list("taxes", "Charges", [_c("description", "Small Text", "Charge", 46), _c("expense_account", "Link", "Account", 30), _c("amount", "Currency", "Amount", 24)]),
		_list("items", "Shared Over", [
			_c("item_code", "Link", "Item", 36, ("description", "Text Editor", "Description")), _c("receipt_document", "Dynamic Link", "Receipt", 18),
			_c("qty", "Float", "Qty", 10), _c("amount", "Currency", "Amount", 16), _c("applicable_charges", "Currency", "Charges Added", 20)]),
		_sums(_total("total_taxes_and_charges", "Total Charges")),
		signs=PREPARED,
	)


def period_closing_voucher():
	"""A year closed: which, the dates, and where the profit went."""
	return _paper("Period Closing", "Voucher No",
		_pair([], [_r("transaction_date", "Date", "Date"), _r("fiscal_year", "Link", "Fiscal Year"), _r("period_start_date", "Date", "From"),
			_r("period_end_date", "Date", "To"), _r("closing_account_head", "Link", "Closed Into", bold=1), _r("gle_processing_status", "Data", "Status")], top=18),
		_note("remarks", "Remarks"),
		signs=PREPARED,
	)


def process_deferred_accounting():
	"""Income or expense earned over time, booked for a stretch of dates."""
	return _paper("Deferred Booking", "Booking No",
		_pair([], [_r("type", "Data", "Type"), _r("account", "Link", "Account"), _r("start_date", "Date", "From"), _r("end_date", "Date", "To"),
			_r("posting_date", "Date", "Booked On")], top=18),
	)


def process_payment_reconciliation():
	"""A party's payments matched to its invoices in the background: whose,
	which account, and the dates looked at."""
	return _paper("Payment Reconciliation", "Run No",
		_pair([heading("Party"), field("party", "Dynamic Link", "Party", show_label="hide", bold=1, font_size=13), _line("party_type", "Link", "Type")],
			[_r("receivable_payable_account", "Link", "Account"), _r("from_invoice_date", "Date", "Invoices From"), _r("to_invoice_date", "Date", "Invoices To"),
				_r("from_payment_date", "Date", "Payments From"), _r("to_payment_date", "Date", "Payments To"), _r("status", "Data", "Status")]),
	)


def product_bundle():
	"""Items sold as one: the bundle and what's in it."""
	return _paper("Product Bundle", "Bundle",
		_pair([heading("Sold As"), field("new_item_code", "Link", "Item", show_label="hide", bold=1, font_size=13), _muted("description", "Data")], [], top=22),
		_lines("items", "Contains", [_c("idx", "Int", "No", 6), _c("item_code", "Link", "Item", 50, ("description", "Text Editor", "Description")),
			_qty(width=20), _c("rate", "Float", "Rate", 24)], top=22),
	)


def production_plan():
	"""What the workshop plans to make for which orders, when, and the
	materials it needs."""
	return _paper("Production Plan", "Plan No",
		_pair([], [_r("posting_date", "Date", "Date"), _r("from_date", "Date", "Orders From"), _r("to_date", "Date", "Orders To"),
			_r("for_warehouse", "Link", "Materials Into"), _project(), _r("status", "Data", "Status")], top=18),
		_list("sales_orders", "For Orders", [_c("sales_order", "Link", "Order", 26), _c("customer", "Link", "Customer", 34),
			_c("sales_order_date", "Date", "Date", 18), _c("grand_total", "Currency", "Total", 22)]),
		_list("po_items", "To Make", [
			_c("item_code", "Link", "Item", 30, ("bom_no", "Link", "BOM")), _qty(fieldname="planned_qty", unit="stock_uom", label="Planned", width=14),
			_c("warehouse", "Link", "Into", 20), _c("planned_start_date", "Datetime", "Starts", 18), _c("produced_qty", "Float", "Made", 18)]),
		_list("mr_items", "Materials Needed", [
			_c("item_name", "Data", "Material", 36, ("item_code", "Link", "Item Code")), _qty(fieldname="quantity", width=14),
			_c("warehouse", "Link", "For", 22), _c("material_request_type", "Data", "By", 14), _c("schedule_date", "Date", "By When", 14)]),
		_sums(_r("total_planned_qty", "Float", "Planned"), _r("total_produced_qty", "Float", "Made")),
	)


def project_update():
	"""What each person said about a project on a day."""
	return _paper("Project Update", "Update No",
		_pair([heading("Project"), linked("project.project_name", "Project", show_label="hide", bold=1, font_size=13)],
			[_r("date", "Date", "Date"), _r("time", "Time", "Time")]),
		_lines("users", "Updates", [_c("full_name", "Data", "Who", 28), _c("project_status", "Text", "Update", 72)], top=24),
	)


def repost_accounting_ledger():
	"""Documents whose ledger entries were written again, and how it went."""
	return _paper("Ledger Repost", "Repost No",
		_pair([], [_r("status", "Data", "Status")], top=18),
		_lines("vouchers", "Documents", [_c("voucher_type", "Link", "Document", 40), _c("voucher_no", "Dynamic Link", "Number", 40), _c("status", "Data", "Status", 20)], top=22),
	)


def repost_payment_ledger():
	"""Documents whose payment ledger was written again, and how it went."""
	return _paper("Payment Ledger Repost", "Repost No",
		_pair([], [_r("posting_date", "Date", "From"), _r("voucher_type", "Link", "Documents"), _r("repost_status", "Data", "Status")], top=18),
		_lines("repost_vouchers", "Documents", [_c("voucher_type", "Link", "Document", 50), _c("voucher_no", "Dynamic Link", "Number", 50)], top=22),
	)


def sales_forecast():
	"""What we expect to sell, item by item and when, to plan making and
	buying by."""
	return _paper("Sales Forecast", "Forecast No",
		_pair([], [_r("posting_date", "Date", "Date"), _r("from_date", "Date", "From"), _r("frequency", "Data", "Every"),
			_r("demand_number", "Int", "Periods"), _r("parent_warehouse", "Link", "Warehouse"), _r("status", "Data", "Status")], top=18),
		_lines("items", "Expected", [_c("item_name", "Data", "Item", 40, ("item_code", "Link", "Item Code")), _c("delivery_date", "Date", "By", 18),
			_c("warehouse", "Link", "Warehouse", 22), _qty(fieldname="demand_qty", width=20)], top=22),
	)


def serial_and_batch_bundle():
	"""The serial and batch numbers that moved with one line of a document."""
	return _paper("Serial and Batch Numbers", "Bundle No",
		_pair(_head("Item", "item_name", field("item_code", "Link", "Item Code", show_label="hide", custom_style=f"color:{MUTED};")),
			[_r("type_of_transaction", "Data", "Direction"), _r("voucher_type", "Link", "Document"), _r("voucher_no", "Dynamic Link", "Number"),
				_r("warehouse", "Link", "Warehouse"), _r("posting_datetime", "Datetime", "Date"), _r("total_qty", "Float", "Quantity", bold=1)]),
		_lines("entries", "Numbers", [_c("serial_no", "Link", "Serial No", 32), _c("batch_no", "Link", "Batch", 28), _c("warehouse", "Link", "Warehouse", 25),
			_c("qty", "Float", "Qty", 15)]),
	)


def share_transfer():
	"""Shares issued, bought back or passed on: from whom to whom, which and
	how many, at what price, and each side to sign."""
	return _paper("Share Transfer", "Transfer No",
		_pair([heading("From", visible_if="doc.from_shareholder"), linked("from_shareholder.title", "From", show_label="hide", bold=1, font_size=13),
				_line("from_folio_no", "Data", "Folio"),
				heading("To", visible_if="doc.to_shareholder", custom_style="margin-top:14px;"),
				linked("to_shareholder.title", "To", show_label="hide", bold=1, font_size=13), _line("to_folio_no", "Data", "Folio")],
			[_r("date", "Date", "Date"), _r("transfer_type", "Data", "Type"), _r("share_type", "Link", "Shares"), _r("from_no", "Int", "From No"),
				_r("to_no", "Int", "To No"), _r("no_of_shares", "Int", "Number of Shares", bold=1), _r("rate", "Currency", "Price Each"), _total("amount", "Amount")]),
		_note("remarks", "Remarks", "Long Text"),
		signs=(("Transferor", None), ("Transferee", None)),
	)


def shipment():
	"""A booking with a carrier: from where to where, when it's collected,
	the parcels, what's inside and its value, and the deliveries it carries."""
	return _paper("Shipment", "Shipment No",
		_pair([heading("Collect From"), *[field(one, "Link", "From", show_label="hide", bold=1, font_size=13) for one in ("pickup_company", "pickup_customer", "pickup_supplier")],
				field("pickup", "Data", "From", show_label="hide", bold=1, font_size=13), _muted("pickup_address", "Text"),
				_line("pickup_contact", "Text", "Contact"),
				heading("Deliver To", custom_style="margin-top:14px;"),
				*[field(one, "Link", "To", show_label="hide", bold=1, font_size=13) for one in ("delivery_company", "delivery_customer", "delivery_supplier")],
				field("delivery_to", "Data", "To", show_label="hide", bold=1, font_size=13),
				_muted("delivery_address", "Text"), _line("delivery_contact", "Text", "Contact")],
			[_r("pickup_date", "Date", "Collect On"), _r("pickup_from", "Time", "From"), _r("pickup_to", "Time", "Until"), _r("shipment_type", "Data", "Type"),
				_r("carrier", "Data", "Carrier"), _r("carrier_service", "Data", "Service"), _r("awb_number", "Data", "Waybill No", bold=1),
				_r("value_of_goods", "Currency", "Value"), _r("incoterm", "Link", "Delivery Terms"), _r("total_weight", "Float", "Weight")]),
		_list("shipment_parcel", "Parcels", [_c("count", "Int", "Count", 16), _c("length", "Float", "Length", 21), _c("width", "Float", "Width", 21),
			_c("height", "Float", "Height", 21), _c("weight", "Float", "Weight", 21)]),
		_note("description_of_content", "Contents"),
		_list("shipment_delivery_note", "Deliveries", [_c("delivery_note", "Link", "Delivery No", 60), _c("grand_total", "Currency", "Value", 40)]),
		signs=(("Handed Over By", None), ("Collected By", "carrier")),
	)


def stock_closing_entry():
	"""Stock balances frozen for a stretch of dates."""
	return _paper("Stock Closing", "Closing No",
		_pair([], [_r("from_date", "Date", "From"), _r("to_date", "Date", "To"), _r("status", "Data", "Status")], top=18),
		signs=PREPARED,
	)


def stock_reconciliation():
	"""Stock counted: opening stock, a count or an adjustment by what it's
	for, each item with what the books said and what was found, the value
	it changes, and who counted and approved."""
	titles = (("Opening Stock", 'doc.purpose == "Opening Stock"'), ("Stock Count", 'doc.purpose == "Stock Reconciliation"'),
		("Stock Adjustment", 'doc.purpose == "Adjustment Entry"'))
	return _paper(titles, "Count No",
		_pair([], [_r("posting_date", "Date", "Date"), _r("set_warehouse", "Link", "Warehouse")], top=18),
		_lines("items", "Items", [
			_c("item_name", "Data", "Item", 30, ("item_code", "Link", "Item Code"), ("batch_no", "Link", "Batch")), _c("warehouse", "Link", "Warehouse", 16),
			_c("current_qty", "Float", "Books Said", 12), _qty(unit="stock_uom", label="Counted", width=12), _c("quantity_difference", "Data", "Difference", 12, align="right"),
			_c("amount_difference", "Currency", "Value Change", 18)], top=22),
		_sums(_total("difference_amount", "Value Change")),
		signs=(("Counted By", None), ("Approved By", None)),
	)


def stock_reservation_entry():
	"""Stock held for an order: which item, where, for what, how much is
	held and how much has gone."""
	return _paper("Stock Reservation", "Reservation No",
		_pair([heading("Item"), field("item_code", "Link", "Item", show_label="hide", bold=1, font_size=13), _line("warehouse", "Link", "In")],
			[_r("voucher_type", "Data", "For"), _r("voucher_no", "Dynamic Link", "Number"), _r("reserved_qty", "Float", "Held", bold=1),
				_r("stock_uom", "Link", "Unit"), _r("delivered_qty", "Float", "Gone"), _r("status", "Data", "Status"), _project()]),
	)


def supplier_scorecard_period():
	"""How a supplier scored over a stretch: each measure with its weight
	and score, and the total."""
	return _paper("Supplier Score", "Score No",
		_pair([heading("Supplier"), field("supplier", "Link", "Supplier", show_label="hide", bold=1, font_size=13)],
			[_r("start_date", "Date", "From"), _r("end_date", "Date", "To"), _r("total_score", "Percent", "Score", bold=1, font_size=15)]),
		_lines("criteria", "Measures", [_c("criteria_name", "Link", "Measure", 46), _c("weight", "Percent", "Weight", 18), _c("score", "Percent", "Score", 18),
			_c("max_score", "Float", "Out Of", 18)], top=22),
	)


def telephony_call_type():
	"""A kind of call, by name."""
	return _paper("Call Type", "Name", _pair([heading("Call Type"), field("call_type", "Data", "Call Type", show_label="hide", bold=1, font_size=13)], [], top=22))


def transaction_deletion_record():
	"""A company's transactions deleted: what kinds and how many."""
	return _paper("Transactions Deleted", "Record No",
		_pair([], [_r("status", "Data", "Status")], top=18),
		_lines("doctypes_to_delete", "Deleted", [_c("doctype_name", "Link", "Kind", 60), _c("document_count", "Int", "Count", 20), _c("deleted", "Check", "Done", 20, align="right")], top=22),
		signs=PREPARED,
	)


def credit_ledger_entry():
	"""Credits given, spent or refunded: to whom, how many, why, and until
	when."""
	return _paper("Credit Entry", "Entry No",
		_pair([heading("Workspace"), field("tenant", "Link", "Workspace", show_label="hide", bold=1, font_size=13), _muted("why")],
			[_r("kind", "Data", "Kind"), _r("credits", "Float", "Credits", bold=1), _r("source", "Data", "From"), _r("expires_on", "Date", "Until"),
				_r("against", "Link", "Against"), _r("reference", "Data", "Reference")]),
	)


def _emp(*more, words="Employee", name="employee_name"):
	"""Whose it is: the name, and the lines under it."""
	return [heading(words), field(name, "Data", words, show_label="hide", bold=1, font_size=13), *more]


DEPT = _muted("department", "Link", "Department")
SIGNED = (("Employee", "employee_name"), ("Approved By", None))
LETTER = (("For the Company", "company"), ("Accepted By", "employee_name"))


def _components(fieldname, words):
	return _list(fieldname, words, [_c("salary_component", "Link", "Component", 70), _c("amount", "Float", "Amount", 30)], top=18)


def _changes(fieldname):
	return _lines(fieldname, "Changes", [_c("property", "Data", "What", 34), _c("current", "Data", "Was", 33), _c("new", "Data", "Now", 33)], top=24)


def _activities():
	return _list("activities", "Steps", [_c("activity_name", "Data", "Step", 36, ("description", "Text Editor", "Description")),
		_c("user", "Link", "Who", 26), _c("role", "Link", "Or Role", 20), _c("begin_on", "Int", "Day", 9), _c("duration", "Int", "Days", 9)], top=24)


def additional_salary():
	"""An amount added to or taken from one payroll: whose, what for, how much
	and when."""
	return _paper("Additional Salary", "No",
		_pair(_emp(DEPT), [_r("salary_component", "Link", "Component"), _r("type", "Data", "Type"), _r("payroll_date", "Date", "Paid With Payroll Of"),
			_r("from_date", "Date", "From"), _r("to_date", "Date", "To"), _total("amount", "Amount")]),
		signs=SIGNED)


def appraisal():
	"""How someone did over a cycle: each goal with its weight and score,
	how they rated themselves, what others said, and the final score."""
	return _paper("Appraisal", "Appraisal No",
		_pair(_emp(_muted("designation", "Link", "Designation"), DEPT),
			[_r("appraisal_cycle", "Link", "Cycle"), _r("start_date", "Date", "From"), _r("end_date", "Date", "To"),
				_r("total_score", "Float", "Goals"), _r("self_score", "Float", "Self"), _r("avg_feedback_score", "Float", "Feedback"),
				_r("final_score", "Float", "Final Score", bold=1, font_size=15)]),
		_list("appraisal_kra", "Goals", [_c("kra", "Link", "Goal", 46), _c("per_weightage", "Percent", "Weight", 18),
			_c("goal_completion", "Percent", "Done", 18), _c("goal_score", "Float", "Score", 18)], top=24),
		_list("self_ratings", "Self Rating", [_c("criteria", "Link", "Criterion", 60), _c("per_weightage", "Percent", "Weight", 20), _c("rating", "Rating", "Rating", 20)]),
		_note("reflections", "Reflections", "Text Editor"),
		_note("remarks", "Remarks", "Text Editor"),
		signs=(("Employee", "employee_name"), ("Appraiser", None)),
	)


def arrear():
	"""Pay owed from before, paid now: whose, from when, and each component."""
	return _paper("Arrears", "No",
		_pair(_emp(), [_r("arrear_start_date", "Date", "Owed From"), _r("payroll_date", "Date", "Paid With Payroll Of"), _r("payroll_period", "Link", "Payroll Period"),
			_r("salary_structure", "Link", "Salary Structure")]),
		_components("earning_arrears", "Earnings"), _components("deduction_arrears", "Deductions"), _components("accrual_arrears", "Accruals"),
		signs=SIGNED)


def attendance():
	"""A day's attendance: whose, which day, present or not, the shift, in
	and out, and the hours."""
	return _paper("Attendance", "No",
		_pair(_emp(DEPT), [_r("attendance_date", "Date", "Date"), _r("status", "Data", "Status", bold=1), _r("leave_type", "Link", "Leave"),
			_r("shift", "Link", "Shift"), _r("in_time", "Datetime", "In"), _r("out_time", "Datetime", "Out"), _r("working_hours", "Float", "Hours"),
			_r("actual_overtime_duration", "Float", "Overtime")]),
	)


def attendance_request():
	"""Asking for days to count as worked: whose, which days, and why."""
	return _paper("Attendance Request", "Request No",
		_pair(_emp(DEPT), [_r("from_date", "Date", "From"), _r("to_date", "Date", "To"), _r("half_day_date", "Date", "Half Day On"),
			_r("reason", "Data", "Reason", bold=1), _r("shift", "Link", "Shift")]),
		_note("explanation", "Explanation"),
		signs=SIGNED)


def compensatory_leave_request():
	"""Leave asked for in return for days worked off-schedule."""
	return _paper("Compensatory Leave Request", "Request No",
		_pair(_emp(DEPT), [_r("work_from_date", "Date", "Worked From"), _r("work_end_date", "Date", "Worked To"), _r("half_day_date", "Date", "Half Day On"),
			_r("leave_type", "Link", "Leave Type")]),
		_note("reason", "Reason"),
		signs=SIGNED)


def employee_benefit_application():
	"""Benefits chosen for a payroll period, within what's allowed."""
	return _paper("Benefit Application", "Application No",
		_pair(_emp(DEPT), [_r("date", "Date", "Date"), _r("payroll_period", "Link", "Payroll Period"), _r("max_benefits", "Currency", "Allowed"),
			_r("remaining_benefit", "Currency", "Left")]),
		_lines("employee_benefits", "Benefits", [_c("salary_component", "Link", "Benefit", 50), _c("max_benefit_amount", "Currency", "Up To", 25),
			_c("amount", "Currency", "Chosen", 25)], top=24),
		_sums(_total("total_amount", "Total")),
		signs=SIGNED)


def employee_benefit_claim():
	"""A benefit claimed: what, how much, and how much is allowed."""
	return _paper("Benefit Claim", "Claim No",
		_pair(_emp(DEPT), [_r("payroll_date", "Date", "Date"), _r("earning_component", "Link", "Benefit"), _r("max_amount_eligible", "Currency", "Allowed"),
			_total("claimed_amount", "Claimed")]),
		signs=SIGNED)


def employee_grievance():
	"""A grievance: who raised it, against whom, what happened, why, and how
	it was resolved."""
	return _paper("Grievance", "Grievance No",
		_pair([heading("Raised By"), linked("raised_by.employee_name", "Raised By", show_label="hide", bold=1, font_size=13),
				_muted("designation", "Link", "Designation"), heading("Against", custom_style="margin-top:14px;"),
				field("grievance_against", "Dynamic Link", "Against", show_label="hide", bold=1), _muted("grievance_against_party", "Link", "Kind")],
			[_r("date", "Date", "Date"), _r("grievance_type", "Link", "Type"), _r("status", "Data", "Status", bold=1), _r("resolution_date", "Date", "Resolved On")]),
		section([heading("Subject"), field("subject", "Data", "Subject", show_label="hide", bold=1)], top=18),
		_note("description", "What Happened", "Text Editor"),
		_note("cause_of_grievance", "Cause", "Text Editor"),
		_note("resolution_detail", "Resolution"),
		signs=(("Raised By", None), ("Resolved By", None)),
	)


def employee_incentive():
	"""An incentive paid with a payroll."""
	return _paper("Incentive", "No",
		_pair(_emp(DEPT), [_r("payroll_date", "Date", "Paid With Payroll Of"), _r("salary_component", "Link", "Component"), _total("incentive_amount", "Amount")]),
		signs=SIGNED)


def employee_onboarding():
	"""Someone joining: who, when, as what, and each step to get them started."""
	return _paper("Onboarding", "No",
		_pair(_emp(_muted("designation", "Link", "Designation"), DEPT),
			[_r("date_of_joining", "Date", "Joins On"), _r("boarding_begins_on", "Date", "Starts On"), _r("job_offer", "Link", "Job Offer"),
				_r("boarding_status", "Data", "Status"), _project()]),
		_activities(),
	)


def employee_other_income():
	"""Income from elsewhere declared for tax."""
	return _paper("Other Income", "No",
		_pair(_emp(), [_r("payroll_period", "Link", "Payroll Period"), _r("source", "Data", "From"), _total("amount", "Amount")]),
		signs=SIGNED)


def employee_performance_feedback():
	"""What a reviewer said about someone: each criterion rated, the score,
	and the words."""
	return _paper("Performance Feedback", "No",
		_pair(_emp(_muted("designation", "Link", "Designation"), DEPT),
			[_r("added_on", "Date", "Date"), _r("appraisal_cycle", "Link", "Cycle"), _r("reviewer_name", "Data", "Reviewer"),
				_r("reviewer_designation", "Link", "Reviewer's Role"), _r("total_score", "Float", "Score", bold=1)]),
		_list("feedback_ratings", "Ratings", [_c("criteria", "Link", "Criterion", 60), _c("per_weightage", "Percent", "Weight", 20), _c("rating", "Rating", "Rating", 20)], top=24),
		_note("feedback", "Feedback", "Text Editor"),
		signs=(("Reviewer", "reviewer_name"), ("Employee", "employee_name")),
	)


def employee_promotion():
	"""A promotion: from when, what changes, and the pay before and after."""
	return _paper("Promotion Letter", "No",
		_pair(_emp(DEPT), [_r("promotion_date", "Date", "From"), _r("current_ctc", "Currency", "Pay Was"), _r("revised_ctc", "Currency", "Pay Now", bold=1)]),
		_changes("promotion_details"),
		signs=LETTER)


def employee_referral():
	"""Someone put forward for a job: who, for what, by whom, and why."""
	return _paper("Referral", "Referral No",
		_pair(_head("Candidate", "full_name", _line("email", "Data", "Email"), _line("contact_no", "Data", "Phone"),
				_line("current_employer", "Data", "Works At"), _line("current_job_title", "Data", "As")),
			[_r("date", "Date", "Date"), _r("for_designation", "Link", "For"), _r("department", "Link", "Department"), _r("referrer_name", "Data", "Referred By"),
				_r("status", "Data", "Status")]),
		_note("qualification_reason", "Why", "Text Editor"),
		_note("work_references", "References", "Text Editor"),
	)


def employee_separation():
	"""Someone leaving: who, when they resigned, and each step to see them
	out."""
	return _paper("Separation", "No",
		_pair(_emp(_muted("designation", "Link", "Designation"), DEPT),
			[_r("resignation_letter_date", "Date", "Resigned On"), _r("boarding_begins_on", "Date", "Starts On"), _r("boarding_status", "Data", "Status"), _project()]),
		_activities(),
		_note("exit_interview", "Exit Interview", "Text Editor"),
	)


def employee_tax_exemption_declaration():
	"""What someone expects to claim against tax this period."""
	return _paper("Tax Exemption Declaration", "No",
		_pair(_emp(DEPT), [_r("payroll_period", "Link", "Payroll Period")]),
		_lines("declarations", "Declared", [_c("exemption_sub_category", "Link", "For", 40, ("exemption_category", "Link", "Category")),
			_c("max_amount", "Currency", "Up To", 30), _c("amount", "Currency", "Declared", 30)], top=24),
		_sums(_r("total_declared_amount", "Currency", "Declared"), _total("total_exemption_amount", "Exempt")),
		signs=SIGNED)


def employee_tax_exemption_proof_submission():
	"""Proof of what someone spent against tax."""
	return _paper("Tax Exemption Proof", "No",
		_pair(_emp(DEPT), [_r("submission_date", "Date", "Date"), _r("payroll_period", "Link", "Payroll Period")]),
		_lines("tax_exemption_proofs", "Proofs", [_c("exemption_sub_category", "Link", "For", 36, ("exemption_category", "Data", "Category")),
			_c("type_of_proof", "Data", "Proof", 24), _c("max_amount", "Currency", "Up To", 20), _c("amount", "Currency", "Spent", 20)], top=24),
		_sums(_r("total_actual_amount", "Currency", "Spent"), _total("exemption_amount", "Exempt")),
		signs=SIGNED)


def employee_transfer():
	"""A transfer: from when, and what changes."""
	return _paper("Transfer Letter", "No",
		_pair(_emp(DEPT), [_r("transfer_date", "Date", "From"), _r("new_company", "Link", "To Company"), _r("new_employee_id", "Link", "New Employee No")]),
		_changes("transfer_details"),
		signs=LETTER)


def exit_interview():
	"""The conversation on the way out: who, when, with whom, and what was
	said."""
	return _paper("Exit Interview", "No",
		_pair(_emp(_muted("designation", "Link", "Designation"), DEPT),
			[_r("date", "Date", "Date"), _r("date_of_joining", "Date", "Joined"), _r("relieving_date", "Date", "Leaves"), _r("status", "Data", "Status"),
				_r("employee_status", "Data", "Outcome", bold=1)]),
		_list("interviewers", "Interviewers", [_c("user", "Link", "Interviewer", 100)]),
		_note("interview_summary", "Summary", "Text Editor"),
		signs=(("Employee", "employee_name"), ("Interviewer", None)),
	)


def full_and_final_statement():
	"""What's settled when someone leaves: what's owed to them, what they owe,
	the company's things they hold, and both to sign."""
	return _paper("Full and Final Settlement", "Statement No",
		_pair(_emp(_muted("designation", "Link", "Designation"), DEPT),
			[_r("transaction_date", "Date", "Date"), _r("date_of_joining", "Date", "Joined"), _r("relieving_date", "Date", "Left"), _r("status", "Data", "Status")]),
		_list("payables", "Owed to Them", [_c("component", "Data", "For", 40, ("remark", "Small Text", "Remark")), _c("reference_document", "Dynamic Link", "Document", 26),
			_c("status", "Data", "Status", 14), _c("amount", "Currency", "Amount", 20)], top=24),
		_list("receivables", "Owed by Them", [_c("component", "Data", "For", 40, ("remark", "Small Text", "Remark")), _c("reference_document", "Dynamic Link", "Document", 26),
			_c("status", "Data", "Status", 14), _c("amount", "Currency", "Amount", 20)]),
		_list("assets_allocated", "Company Property", [_c("asset_name", "Data", "Item", 36, ("reference", "Link", "Asset No")), _c("date", "Date", "Given On", 18),
			_c("status", "Data", "Status", 16), _c("action", "Data", "Action", 12), _c("cost", "Currency", "Cost", 18)]),
		_sums(_r("total_payable_amount", "Currency", "Owed to Them"), _r("total_receivable_amount", "Currency", "Owed by Them"),
			_r("total_asset_recovery_cost", "Currency", "Property Not Returned", visible_if="doc.total_asset_recovery_cost")),
		signs=(("For the Company", "company"), ("Received and Settled", "employee_name")),
	)


def gratuity():
	"""End-of-service pay: whose, by which rule, how long they served, how
	much, and what's been paid."""
	return _paper("Gratuity", "No",
		_pair(_emp(_muted("designation", "Data", "Designation"), DEPT),
			[_r("posting_date", "Date", "Date"), _r("gratuity_rule", "Link", "Rule"), _r("current_work_experience", "Float", "Years Served"),
				_total("amount", "Gratuity"), _r("paid_amount", "Currency", "Paid", visible_if="doc.paid_amount"), _r("status", "Data", "Status")]),
		signs=(("For the Company", "company"), ("Received By", "employee_name")),
	)


def holiday_list_assignment():
	"""Which holidays someone follows, from when."""
	return _paper("Holiday List Assignment", "No",
		_pair([heading("For"), field("employee_name", "Data", "Employee", show_label="hide", bold=1, font_size=13),
				field("assigned_to", "Dynamic Link", "For", show_label="hide", custom_style=f"color:{MUTED};")],
			[_r("holiday_list", "Link", "Holiday List", bold=1), _r("from_date", "Date", "From"), _r("holiday_list_start", "Date", "List Starts"),
				_r("holiday_list_end", "Date", "List Ends")]),
	)


def income_tax_slab():
	"""Income tax by bands: from when, each band and its rate, and other
	taxes."""
	return _paper("Income Tax Slab", "Slab",
		_pair([], [_r("effective_from", "Date", "From"), _r("currency", "Link", "Currency"), _r("standard_tax_exemption_amount", "Currency", "Standard Exemption"),
			_r("tax_relief_limit", "Currency", "Relief Up To")], top=18),
		_lines("slabs", "Bands", [_c("from_amount", "Currency", "From", 30), _c("to_amount", "Currency", "To", 30), _c("percent_deduction", "Percent", "Rate", 40)], top=22),
		_list("other_taxes_and_charges", "Other Taxes", [_c("description", "Data", "Tax", 40), _c("percent", "Percent", "Rate", 20),
			_c("min_taxable_income", "Currency", "From", 20), _c("max_taxable_income", "Currency", "To", 20)]),
	)


def interview():
	"""An interview: who for what, when, with whom, the rating, and the
	summary."""
	return _paper("Interview", "Interview No",
		_pair([heading("Candidate"), linked("job_applicant.applicant_name", "Candidate", show_label="hide", bold=1, font_size=13),
				_line("designation", "Link", "For"), _line("job_opening", "Link", "Opening")],
			[_r("scheduled_on", "Date", "Date"), _r("from_time", "Time", "From"), _r("to_time", "Time", "To"), _r("interview_type", "Link", "Round"),
				_r("average_rating", "Rating", "Rating"), _r("status", "Data", "Status", bold=1)]),
		_list("interview_details", "Interviewers", [_c("interviewer", "Link", "Interviewer", 100)]),
		_note("interview_summary", "Summary", "Text Editor"),
		signs=(("Interviewer", None), ("Interviewer", None)),
	)


def leave_adjustment():
	"""Leave added or taken off an allocation, and why."""
	return _paper("Leave Adjustment", "No",
		_pair(_emp(), [_r("posting_date", "Date", "Date"), _r("leave_type", "Link", "Leave Type"), _r("adjustment_type", "Data", "Adjustment"),
			_r("allocated_leaves", "Float", "Had"), _r("leaves_to_adjust", "Float", "Changed By"), _r("leaves_after_adjustment", "Float", "Has Now", bold=1)]),
		_note("reason_for_adjustment", "Reason"),
		signs=SIGNED)


def leave_allocation():
	"""Leave given for a period: how much new, carried forward, and in all."""
	return _paper("Leave Allocation", "No",
		_pair(_emp(DEPT), [_r("leave_type", "Link", "Leave Type"), _r("from_date", "Date", "From"), _r("to_date", "Date", "To"),
			_r("new_leaves_allocated", "Float", "New"), _r("unused_leaves", "Float", "Carried Forward", visible_if="doc.carry_forward"),
			_r("total_leaves_allocated", "Float", "In All", bold=1, font_size=15)]),
		_note("description", "Notes"),
	)


def leave_application():
	"""Leave asked for: whose, what kind, from when to when, how many days,
	what's left, why, and who approves."""
	return _paper("Leave Application", "Application No",
		_pair(_emp(DEPT), [_r("posting_date", "Date", "Date"), _r("leave_type", "Link", "Leave Type"), _r("from_date", "Date", "From"), _r("to_date", "Date", "To"),
			_r("half_day_date", "Date", "Half Day On"), _r("total_leave_days", "Float", "Days", bold=1, font_size=15), _r("leave_balance", "Float", "Balance Before"),
			_r("status", "Data", "Status", bold=1)]),
		_note("description", "Reason"),
		section([_block("One Leave Balance")], top=18),
		signs=(("Employee", "employee_name"), ("Approved By", "leave_approver_name")))


def leave_encashment():
	"""Unused leave paid out: how many days, at how much."""
	return _paper("Leave Encashment", "No",
		_pair(_emp(DEPT), [_r("encashment_date", "Date", "Date"), _r("leave_type", "Link", "Leave Type"), _r("leave_balance", "Float", "Balance"),
			_r("encashment_days", "Float", "Days Paid"), _total("encashment_amount", "Amount"), _r("status", "Data", "Status")]),
		signs=(("For the Company", "company"), ("Received By", "employee_name")))


def leave_policy():
	"""How much of each leave a year a policy gives."""
	return _paper("Leave Policy", "Policy No",
		_lines("leave_policy_details", "Leave a Year", [_c("leave_type", "Link", "Leave Type", 70), _c("annual_allocation", "Float", "Days", 30)], top=24))


def leave_policy_assignment():
	"""Which leave policy someone follows, from when to when."""
	return _paper("Leave Policy Assignment", "No",
		_pair(_emp(), [_r("leave_policy", "Link", "Policy", bold=1), _r("assignment_based_on", "Data", "Based On"), _r("effective_from", "Date", "From"),
			_r("effective_to", "Date", "To")]))


def overtime_slip():
	"""Overtime worked over a stretch: each day and how long."""
	return _paper("Overtime Slip", "Slip No",
		_pair(_emp(DEPT), [_r("posting_date", "Date", "Date"), _r("start_date", "Date", "From"), _r("end_date", "Date", "To"),
			_r("total_overtime_duration", "Float", "Overtime", bold=1)]),
		_lines("overtime_details", "Overtime", [_c("date", "Date", "Date", 22), _c("overtime_type", "Link", "Type", 30),
			_c("standard_working_hours", "Float", "Normal Hours", 24), _c("overtime_duration", "Float", "Overtime", 24)], top=24),
		signs=SIGNED)


def payroll_correction():
	"""A payroll put right: days given back, and each amount."""
	return _paper("Payroll Correction", "No",
		_pair(_emp(), [_r("payroll_date", "Date", "Paid With Payroll Of"), _r("month_for_lwp_reversal", "Data", "For Month"), _r("working_days", "Float", "Working Days"),
			_r("lwp_days", "Float", "Unpaid Days"), _r("days_to_reverse", "Float", "Days Given Back", bold=1), _r("salary_slip_reference", "Link", "Payslip")]),
		_components("earning_arrears", "Earnings"), _components("deduction_arrears", "Deductions"),
		signs=SIGNED)


def payroll_entry():
	"""A payroll run: the period, who's in it, and where it's paid from."""
	return _paper("Payroll Run", "Run No",
		_pair([], [_r("posting_date", "Date", "Date"), _r("start_date", "Date", "From"), _r("end_date", "Date", "To"), _r("payroll_frequency", "Data", "Every"),
			_r("number_of_employees", "Int", "People", bold=1), _r("bank_account", "Link", "Paid From"), _r("status", "Data", "Status")], top=18),
		_lines("employees", "People", [_c("idx", "Int", "No", 6), _c("employee_name", "Data", "Employee", 44), _c("department", "Link", "Department", 25),
			_c("designation", "Data", "Designation", 25)], top=22),
		signs=PREPARED)


def retention_bonus():
	"""A bonus to stay: whose, how much, and when it's paid."""
	return _paper("Retention Bonus", "No",
		_pair(_emp(DEPT), [_r("bonus_payment_date", "Date", "Paid On"), _r("salary_component", "Link", "Component"), _total("bonus_amount", "Amount")]),
		signs=LETTER)


def salary_structure():
	"""How pay is made up: each earning and deduction, and how it's worked
	out."""
	return _paper("Salary Structure", "Structure",
		_pair([], [_r("payroll_frequency", "Data", "Paid Every"), _r("currency", "Link", "Currency")], top=18),
		_list("earnings", "Earnings", [_c("salary_component", "Link", "Component", 34), _c("formula", "Code", "Worked Out As", 40), _c("amount", "Currency", "Amount", 26)]),
		_list("deductions", "Deductions", [_c("salary_component", "Link", "Component", 34), _c("formula", "Code", "Worked Out As", 40), _c("amount", "Currency", "Amount", 26)]),
	)


def salary_structure_assignment():
	"""Someone's pay from a date: the structure, the base, and the tax slab."""
	return _paper("Salary Assignment", "No",
		_pair(_emp(_muted("designation", "Link", "Designation"), DEPT),
			[_r("from_date", "Date", "From"), _r("salary_structure", "Link", "Structure"), _total("base", "Base Pay"), _r("variable", "Currency", "Variable"),
				_r("income_tax_slab", "Link", "Tax Slab")]),
		_list("employee_benefits", "Benefits", [_c("salary_component", "Link", "Benefit", 70), _c("amount", "Currency", "Amount", 30)]),
		signs=LETTER)


def salary_withholding():
	"""Pay held back: whose, why, and for which periods."""
	return _paper("Salary Withholding", "No",
		_pair(_emp(), [_r("posting_date", "Date", "Date"), _r("from_date", "Date", "From"), _r("to_date", "Date", "To"),
			_r("number_of_withholding_cycles", "Int", "Pay Periods"), _r("relieving_date", "Date", "Leaves On"), _r("status", "Data", "Status", bold=1)]),
		_note("reason_for_withholding_salary", "Reason"),
		_list("cycles", "Periods", [_c("from_date", "Date", "From", 33), _c("to_date", "Date", "To", 33), _c("journal_entry", "Link", "Journal Entry", 34)]),
		signs=PREPARED)


def shift_assignment():
	"""A shift someone works, from when, and where."""
	return _paper("Shift Assignment", "No",
		_pair(_emp(DEPT), [_r("shift_type", "Link", "Shift", bold=1), _r("start_date", "Date", "From"), _r("end_date", "Date", "To"),
			_r("shift_location", "Link", "Where"), _r("status", "Data", "Status")]))


def shift_request():
	"""A shift asked for, and who approves it."""
	return _paper("Shift Request", "Request No",
		_pair(_emp(DEPT), [_r("shift_type", "Link", "Shift", bold=1), _r("from_date", "Date", "From"), _r("to_date", "Date", "To"), _r("status", "Data", "Status")]),
		signs=(("Employee", "employee_name"), ("Approved By", "approver")))


def shift_schedule():
	"""A shift that repeats: which, how often, and on which days."""
	return _paper("Shift Schedule", "Schedule",
		_pair([], [_r("shift_type", "Link", "Shift", bold=1), _r("frequency", "Data", "Repeats")], top=18),
		_lines("repeat_on_days", "Days", [_c("day", "Data", "Day", 100)], top=22))


def staffing_plan():
	"""How many people a department plans for: each role, how many now, how
	many to hire, and what it costs."""
	return _paper("Staffing Plan", "Plan",
		_pair([heading("Department", visible_if="doc.department"), field("department", "Link", "Department", show_label="hide", bold=1, font_size=13)],
			[_r("from_date", "Date", "From"), _r("to_date", "Date", "To")]),
		_lines("staffing_details", "Roles", [_c("designation", "Link", "Role", 30), _c("number_of_positions", "Int", "Planned", 12), _c("current_count", "Int", "Now", 10),
			_c("vacancies", "Int", "To Hire", 12), _c("estimated_cost_per_position", "Currency", "Cost Each", 18), _c("total_estimated_cost", "Currency", "Cost", 18)], top=24),
		_sums(_total("total_estimated_budget", "Budget")),
		signs=PREPARED)


def training_event():
	"""A training: what, when and where, who runs it, and who attends."""
	return _paper("Training", "Training",
		_pair(_head("Training", "event_name", _line("training_program", "Link", "Programme"), _line("course", "Data", "Course"), size=15),
			[_r("start_time", "Datetime", "Starts"), _r("end_time", "Datetime", "Ends"), _r("location", "Data", "Where"), _r("type", "Data", "Kind"),
				_r("level", "Data", "Level"), _r("trainer_name", "Data", "Trainer"), _r("event_status", "Data", "Status")]),
		_note("introduction", "About", "Text Editor"),
		_list("employees", "Attending", [_c("employee_name", "Data", "Employee", 40), _c("department", "Link", "Department", 26), _c("status", "Data", "Invited", 17),
			_c("attendance", "Data", "Attended", 17)]),
	)


def training_feedback():
	"""What someone thought of a training."""
	return _paper("Training Feedback", "No",
		_pair(_emp(DEPT), [_r("training_event", "Link", "Training"), _r("course", "Data", "Course"), _r("trainer_name", "Data", "Trainer")]),
		_note("feedback", "Feedback", "Text Editor"))


def training_result():
	"""How each person did in a training: hours, grade and comments."""
	return _paper("Training Result", "No",
		_pair([heading("Training"), field("training_event", "Link", "Training", show_label="hide", bold=1, font_size=13)], [], top=22),
		_lines("employees", "Results", [_c("employee_name", "Data", "Employee", 30), _c("hours", "Float", "Hours", 12), _c("grade", "Data", "Grade", 14),
			_c("comments", "Text", "Comments", 44)], top=22),
		signs=(("Trainer", None), ("Approved By", None)))


def travel_request():
	"""A trip asked for: who, why, the route and dates, who pays, and what it
	costs."""
	return _paper("Travel Request", "Request No",
		_pair(_emp(_line("cell_number", "Data", "Phone"), _line("prefered_email", "Data", "Email"), _line("passport_number", "Data", "Passport")),
			[_r("travel_type", "Data", "Travel"), _r("purpose_of_travel", "Link", "Purpose", bold=1), _r("travel_funding", "Data", "Funding"),
				_r("details_of_sponsor", "Data", "Sponsor"), _r("name_of_organizer", "Data", "Organiser")]),
		_note("description", "Details"),
		_list("itinerary", "Route", [_c("travel_from", "Data", "From", 18), _c("travel_to", "Data", "To", 18), _c("mode_of_travel", "Data", "By", 12),
			_c("departure_date", "Datetime", "Leaves", 18), _c("arrival_date", "Datetime", "Arrives", 18), _c("advance_amount", "Data", "Advance", 16, align="right")], top=22),
		_list("costings", "Costs", [_c("expense_type", "Link", "Cost", 34, ("comments", "Small Text", "Comments")), _c("sponsored_amount", "Currency", "Sponsored", 22),
			_c("funded_amount", "Currency", "Company Pays", 22), _c("total_amount", "Currency", "Total", 22)]),
		signs=SIGNED)


def vehicle_log():
	"""A company car's trip or fill-up: which car, who, the odometer, fuel,
	and service done."""
	return _paper("Vehicle Log", "Log No",
		_pair([heading("Vehicle"), field("license_plate", "Link", "Vehicle", show_label="hide", bold=1, font_size=13), _line("make", "Data", "Make"), _line("model", "Data", "Model"),
				heading("Driver", custom_style="margin-top:14px;"), linked("employee.employee_name", "Driver", show_label="hide", bold=1)],
			[_r("date", "Date", "Date"), _r("last_odometer", "Int", "Odometer Was"), _r("odometer", "Int", "Odometer Now", bold=1), _r("fuel_qty", "Float", "Fuel"),
				_r("price", "Currency", "Fuel Price"), _r("supplier", "Link", "Filled At"), _r("invoice", "Data", "Their Invoice No")]),
		_list("service_detail", "Service", [_c("service_item", "Link", "Service", 40), _c("type", "Data", "Kind", 20), _c("frequency", "Data", "How Often", 20),
			_c("expense_amount", "Currency", "Cost", 20)]),
		signs=(("Driver", None), ("Checked By", None)))


# -- Papers gathered from other records ---------------------------------------

def _block(name):
	"""One of One's blocks (one/print_blocks.py): what a paper gathers from
	records it doesn't hold. Everything around it is the builder's own."""
	return {"label": name, "fieldname": name.lower().replace(" ", "_") + "_template", "fieldtype": "Field Template",
		"field_template": name, "show_label": "hide"}


def _statement(words, name):
	"""Its account is the party itself, so the title stands alone and the
	party is said once, under it."""
	return lambda: layout(
		section([text(words, font_size=24, bold=1, custom_style="letter-spacing:-0.01em;line-height:1.1;")],
			[], widths=[60, 40], top=6, field_orientation="left-right"),
		_pair([heading("Statement For"), field(name, "Data", "Name", show_label="hide", bold=1, font_size=14),
				_muted("primary_address", "Text", "Address"), _line("tax_id", "Data", "TRN"), _line("email_id", "Data", "Email"),
				_line("mobile_no", "Data", "Phone")], [], top=22),
		section([_block("One Statement")], top=22))


def _letter(words, block):
	return lambda: _paper(words, "Ref No",
		_pair([heading("Employee"), field("employee_name", "Data", "Employee", show_label="hide", bold=1, font_size=13),
				_muted("designation", "Link", "Designation")], [], top=18),
		section([_block(block)], top=18),
		signs=(("Authorised Signatory", None), ("Company Stamp", None)))


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
	"One Purchase Voucher": ("Purchase Invoice", "one_book", purchase_voucher),
	"One Purchase Receipt with Serial Numbers": ("Purchase Receipt", "one_inventory", receipt_with_serials),
	"One Payment Receipt": ("Payment Entry", "one_book", payment_receipt),
	"One Payment Voucher": ("Payment Entry", "one_book", payment_voucher),
	"One Journal Voucher": ("Journal Entry", "one_book", journal_voucher),
	"One Journal Credit Note": ("Journal Entry", "one_book", journal_credit_note),
	"One Payment Reminder": ("Dunning", "one_book", payment_reminder),
	"One Pick List": ("Pick List", "one_inventory", pick_list),
	"One Payslip": ("Salary Slip", "one_hr", payslip),
	"One Payslip Compact": ("Salary Slip", "one_hr", payslip_compact),
	"One Salary Statement": ("Salary Slip", "one_hr", salary_statement),
	"One Job Offer": ("Job Offer", "one_hr", job_offer),
	"One Appointment Letter": ("Appointment Letter", "one_hr", appointment_letter),
	"One Packing Slip": ("Packing Slip", "one_inventory", packing_slip),
	"One Stock Entry": ("Stock Entry", "one_inventory", stock_entry),
	"One Blanket Order": ("Blanket Order", "one_inventory", blanket_order),
	"One Work Order": ("Work Order", "one_inventory", work_order),
	"One Equipment Handover": ("Asset Movement", "one_inventory", equipment_handover),
	"One Timesheet": ("Timesheet", "one_project", timesheet),
	"One Contract": ("Contract", "one_crm", contract),
	"One Maintenance Plan": ("Maintenance Schedule", "one_crm", maintenance_plan),
	"One Service Report": ("Maintenance Visit", "one_crm", service_report),
	"One Installation Note": ("Installation Note", "one_crm", installation_note),
	"One Subcontracting Order": ("Subcontracting Order", "one_inventory", subcontracting_order),
	"One Subcontracting Receipt": ("Subcontracting Receipt", "one_inventory", subcontracting_receipt),
	"One Subcontracting Inward Order": ("Subcontracting Inward Order", "one_inventory", subcontracting_inward_order),
	"One Payment Order": ("Payment Order", "one_book", payment_order),
	"One Bank Guarantee": ("Bank Guarantee", "one_book", bank_guarantee),
	"One Material Request": ("Material Request", "one_inventory", material_request),
	"One Delivery Trip": ("Delivery Trip", "one_inventory", delivery_trip),
	"One Quality Inspection": ("Quality Inspection", "one_inventory", quality_inspection),
	"One Payment Request": ("Payment Request", "one_book", payment_request),
	"One Expense Claim": ("Expense Claim", "one_hr", expense_claim),
	"One Employee Advance": ("Employee Advance", "one_hr", employee_advance),
	"One Job Card": ("Job Card", "one_inventory", job_card),
	"One Bill of Materials": ("BOM", "one_inventory", bill_of_materials),
	"One Asset Card": ("Asset", "one_inventory", asset),
	"One Asset Capitalization": ("Asset Capitalization", "one_inventory", asset_capitalization),
	"One Maintenance Record": ("Asset Maintenance Log", "one_inventory", asset_maintenance_log),
	"One Repair Record": ("Asset Repair", "one_inventory", asset_repair),
	"One Asset Shift Allocation": ("Asset Shift Allocation", "one_inventory", asset_shift_allocation),
	"One Asset Value Adjustment": ("Asset Value Adjustment", "one_inventory", asset_value_adjustment),
	"One BOM Creator": ("BOM Creator", "one_inventory", bom_creator),
	"One Bank Transaction": ("Bank Transaction", "one_book", bank_transaction),
	"One Budget": ("Budget", "one_book", budget),
	"One Cost Center Allocation": ("Cost Center Allocation", "one_book", cost_center_allocation),
	"One Exchange Rate Revaluation": ("Exchange Rate Revaluation", "one_book", exchange_rate_revaluation),
	"One Invoice Discounting": ("Invoice Discounting", "one_book", invoice_discounting),
	"One Item Standard Cost": ("Item Standard Cost", "one_inventory", item_standard_cost),
	"One Landed Cost Voucher": ("Landed Cost Voucher", "one_inventory", landed_cost_voucher),
	"One Period Closing Voucher": ("Period Closing Voucher", "one_book", period_closing_voucher),
	"One Process Deferred Accounting": ("Process Deferred Accounting", "one_book", process_deferred_accounting),
	"One Process Payment Reconciliation": ("Process Payment Reconciliation", "one_book", process_payment_reconciliation),
	"One Product Bundle": ("Product Bundle", "one_inventory", product_bundle),
	"One Production Plan": ("Production Plan", "one_inventory", production_plan),
	"One Project Update": ("Project Update", "one_project", project_update),
	"One Repost Accounting Ledger": ("Repost Accounting Ledger", "one_book", repost_accounting_ledger),
	"One Repost Payment Ledger": ("Repost Payment Ledger", "one_book", repost_payment_ledger),
	"One Sales Forecast": ("Sales Forecast", "one_inventory", sales_forecast),
	"One Serial and Batch Bundle": ("Serial and Batch Bundle", "one_inventory", serial_and_batch_bundle),
	"One Share Transfer": ("Share Transfer", "one_book", share_transfer),
	"One Shipment": ("Shipment", "one_inventory", shipment),
	"One Stock Closing Entry": ("Stock Closing Entry", "one_inventory", stock_closing_entry),
	"One Stock Reconciliation": ("Stock Reconciliation", "one_inventory", stock_reconciliation),
	"One Stock Reservation Entry": ("Stock Reservation Entry", "one_inventory", stock_reservation_entry),
	"One Supplier Scorecard Period": ("Supplier Scorecard Period", "one_inventory", supplier_scorecard_period),
	"One Telephony Call Type": ("Telephony Call Type", "one_crm", telephony_call_type),
	"One Transaction Deletion Record": ("Transaction Deletion Record", "one_book", transaction_deletion_record),
	"One Credit Ledger Entry": ("Credit Ledger Entry", "one_admin", credit_ledger_entry),
	"One Statement of Account": ("Customer", "one_book", _statement("Statement of Account", "customer_name")),
	"One Supplier Statement": ("Supplier", "one_book", _statement("Supplier Statement", "supplier_name")),
	"One Salary Certificate": ("Employee", "one_hr", _letter("Salary Certificate", "One Salary Certificate")),
	"One Experience Letter": ("Employee", "one_hr", _letter("Experience Letter", "One Experience Letter")),
	"One Additional Salary": ("Additional Salary", "one_hr", additional_salary),
	"One Appraisal": ("Appraisal", "one_hr", appraisal),
	"One Arrear": ("Arrear", "one_hr", arrear),
	"One Attendance": ("Attendance", "one_hr", attendance),
	"One Attendance Request": ("Attendance Request", "one_hr", attendance_request),
	"One Compensatory Leave Request": ("Compensatory Leave Request", "one_hr", compensatory_leave_request),
	"One Employee Benefit Application": ("Employee Benefit Application", "one_hr", employee_benefit_application),
	"One Employee Benefit Claim": ("Employee Benefit Claim", "one_hr", employee_benefit_claim),
	"One Employee Grievance": ("Employee Grievance", "one_hr", employee_grievance),
	"One Employee Incentive": ("Employee Incentive", "one_hr", employee_incentive),
	"One Employee Onboarding": ("Employee Onboarding", "one_hr", employee_onboarding),
	"One Employee Other Income": ("Employee Other Income", "one_hr", employee_other_income),
	"One Employee Performance Feedback": ("Employee Performance Feedback", "one_hr", employee_performance_feedback),
	"One Promotion Letter": ("Employee Promotion", "one_hr", employee_promotion),
	"One Employee Referral": ("Employee Referral", "one_hr", employee_referral),
	"One Employee Separation": ("Employee Separation", "one_hr", employee_separation),
	"One Employee Tax Exemption Declaration": ("Employee Tax Exemption Declaration", "one_hr", employee_tax_exemption_declaration),
	"One Employee Tax Exemption Proof Submission": ("Employee Tax Exemption Proof Submission", "one_hr", employee_tax_exemption_proof_submission),
	"One Transfer Letter": ("Employee Transfer", "one_hr", employee_transfer),
	"One Exit Interview": ("Exit Interview", "one_hr", exit_interview),
	"One Full and Final Settlement": ("Full and Final Statement", "one_hr", full_and_final_statement),
	"One Gratuity": ("Gratuity", "one_hr", gratuity),
	"One Holiday List Assignment": ("Holiday List Assignment", "one_hr", holiday_list_assignment),
	"One Income Tax Slab": ("Income Tax Slab", "one_hr", income_tax_slab),
	"One Interview": ("Interview", "one_hr", interview),
	"One Leave Adjustment": ("Leave Adjustment", "one_hr", leave_adjustment),
	"One Leave Allocation": ("Leave Allocation", "one_hr", leave_allocation),
	"One Leave Application": ("Leave Application", "one_hr", leave_application),
	"One Leave Encashment": ("Leave Encashment", "one_hr", leave_encashment),
	"One Leave Policy": ("Leave Policy", "one_hr", leave_policy),
	"One Leave Policy Assignment": ("Leave Policy Assignment", "one_hr", leave_policy_assignment),
	"One Overtime Slip": ("Overtime Slip", "one_hr", overtime_slip),
	"One Payroll Correction": ("Payroll Correction", "one_hr", payroll_correction),
	"One Payroll Run": ("Payroll Entry", "one_hr", payroll_entry),
	"One Retention Bonus": ("Retention Bonus", "one_hr", retention_bonus),
	"One Salary Structure": ("Salary Structure", "one_hr", salary_structure),
	"One Salary Structure Assignment": ("Salary Structure Assignment", "one_hr", salary_structure_assignment),
	"One Salary Withholding": ("Salary Withholding", "one_hr", salary_withholding),
	"One Shift Assignment": ("Shift Assignment", "one_hr", shift_assignment),
	"One Shift Request": ("Shift Request", "one_hr", shift_request),
	"One Shift Schedule": ("Shift Schedule", "one_hr", shift_schedule),
	"One Staffing Plan": ("Staffing Plan", "one_hr", staffing_plan),
	"One Training Event": ("Training Event", "one_hr", training_event),
	"One Training Feedback": ("Training Feedback", "one_hr", training_feedback),
	"One Training Result": ("Training Result", "one_hr", training_result),
	"One Travel Request": ("Travel Request", "one_hr", travel_request),
	"One Vehicle Log": ("Vehicle Log", "one_hr", vehicle_log),
}
TRADE["Supplier Quotation"] = {
	# A buyer's own address is the one it's billed at.
	"our_address": "billing_address_display",
	"module": "one_inventory",
	"titles": (("Supplier Quotation", ""),),
	"number": "Quotation No",
	"party": ("From", "supplier_name"),
	"tax": None,
	"details": (
		("transaction_date", "Date", "Date"),
		("quotation_number", "Data", "Their Quotation No"),
		("valid_till", "Date", "Valid Until"),
		("project", "Project", "Project"),
		("incoterm", "Link", "Delivery Terms"),
	),
}
#: ERPNext ships one look for these, or none, so One's is its master alone.
ONE_LOOK = ("Purchase Receipt", "Supplier Quotation")
for _doctype, _spec in TRADE.items():
	VERSIONS[f"One {_doctype}"] = (_doctype, _spec["module"], _trade(_doctype, trade_master))
	if _doctype in ONE_LOOK:
		continue
	VERSIONS[f"One {_doctype} Classic"] = (_doctype, _spec["module"], _trade(_doctype, trade_classic))
	VERSIONS[f"One {_doctype} Bordered"] = (_doctype, _spec["module"], _trade(_doctype, trade_bordered))
	VERSIONS[f"One {_doctype} with Images"] = (_doctype, _spec["module"], _trade(_doctype, trade_images))

MODULES = {"one_admin": "One Admin", "one_book": "One Book", "one_crm": "One CRM", "one_inventory": "One Inventory", "one_hr": "One HR", "one_project": "One Project"}


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
