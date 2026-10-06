"""What One's print blocks show (point 11, docs/PASSOVER.md).

A record that leaves the company prints from a format laid out in frappe's
print format builder (each module's `print_format/`). Most of the page is the
builder's own: fields, the items table, the terms. The parts the builder cannot
say are One's blocks, frappe's own Print Format Field Templates, standard in
module One (`one/print_format_field_template/`), so a workspace finds them in
the builder's Library and can place them on a format of its own:

- **One Title**: what the paper is (an invoice, a credit note, a receipt) and
  its number, in the company's Brand Colour.
- **One Party**: who it is for, with their address, contact and tax ID, and
  where the goods go when that is somewhere else.
- **One Details**: its dates and references, the ones that are set.
- **One Totals**: the subtotal, discount, each tax, the total, what is paid
  and owed, the total in the company's currency when the record is in
  another, and the total in words.
- **One Payment Schedule**, **One Bank Details**: when it is due, and where
  to pay it.
- **One Payslip** and **One Payment**: a payslip's earnings and deductions,
  and what a payment settles.
- **One Signatures**: where each side signs, on a paper that is signed and
  handed back.

Each template (templates/one_print/) is drawn from `one_print_block`, which
says what to show. Every value is frappe's formatted value, in the record's
own currency, so nothing here formats a number by hand.

Each record in FORMATS prints with One's format unless the workspace has
chosen another (`settle`).
"""

from pathlib import Path

import frappe
from frappe import _, _lt
from frappe.utils import cint, flt

#: What each kind of record is called on paper, and its number's label.
TITLES = {
	"Quotation": (_lt("Quotation"), _lt("Quotation No")),
	"Sales Order": (_lt("Sales Order"), _lt("Order No")),
	"Sales Invoice": (_lt("Invoice"), _lt("Invoice No")),
	"Delivery Note": (_lt("Delivery Note"), _lt("Delivery No")),
	"Purchase Order": (_lt("Purchase Order"), _lt("Order No")),
	"Request for Quotation": (_lt("Request for Quotation"), _lt("Request No")),
	"Payment Entry": (_lt("Receipt"), _lt("Receipt No")),
	"Salary Slip": (_lt("Payslip"), _lt("Payslip No")),
	"Job Offer": (_lt("Job Offer"), _lt("Offer No")),
	"Appointment Letter": (_lt("Appointment Letter"), _lt("Letter No")),
}

#: Each record's dates and references, in the order they are printed.
DETAILS = {
	"Quotation": ((_lt("Date"), "transaction_date"), (_lt("Valid Until"), "valid_till")),
	"Sales Order": (
		(_lt("Date"), "transaction_date"),
		(_lt("Delivery Date"), "delivery_date"),
		(_lt("Your Reference"), "po_no"),
	),
	"Sales Invoice": (
		(_lt("Date"), "posting_date"),
		(_lt("Due Date"), "due_date"),
		(_lt("Against Invoice"), "return_against"),
		(_lt("Your Reference"), "po_no"),
	),
	"Delivery Note": ((_lt("Date"), "posting_date"), (_lt("Your Reference"), "po_no"), (_lt("Vehicle"), "vehicle_no")),
	"Purchase Order": ((_lt("Date"), "transaction_date"), (_lt("Required By"), "schedule_date")),
	"Request for Quotation": ((_lt("Date"), "transaction_date"),),
	"Payment Entry": (
		(_lt("Date"), "posting_date"),
		(_lt("Paid By"), "mode_of_payment"),
		(_lt("Reference"), "reference_no"),
		(_lt("Reference Date"), "reference_date"),
	),
	"Salary Slip": ((_lt("Working Days"), "total_working_days"), (_lt("Paid Days"), "payment_days")),
	"Job Offer": ((_lt("Date"), "offer_date"), (_lt("Position"), "designation")),
	"Appointment Letter": ((_lt("Starts On"), "appointment_date"),),
}

#: Who a record is for: its heading, and the field with their name.
PARTIES = {
	"Quotation": (_lt("Prepared For"), "customer_name"),
	"Sales Order": (_lt("Bill To"), "customer_name"),
	"Sales Invoice": (_lt("Bill To"), "customer_name"),
	"Delivery Note": (_lt("Deliver To"), "customer_name"),
	"Purchase Order": (_lt("Supplier"), "supplier_name"),
	"Payment Entry": (_lt("Received From"), "party_name"),
	"Salary Slip": (_lt("Employee"), "employee_name"),
	"Job Offer": (_lt("Offered To"), "applicant_name"),
	"Appointment Letter": (_lt("Addressed To"), "applicant_name"),
}

#: The format each record that leaves the company prints with, and the module
#: it is shipped in.
FORMATS = {
	"Quotation": ("One Quotation", "one_crm"),
	"Sales Order": ("One Sales Order", "one_crm"),
	"Sales Invoice": ("One Sales Invoice", "one_book"),
	"Payment Entry": ("One Payment Receipt", "one_book"),
	"Delivery Note": ("One Delivery Note", "one_inventory"),
	"Purchase Order": ("One Purchase Order", "one_inventory"),
	"Request for Quotation": ("One Request for Quotation", "one_inventory"),
	"Salary Slip": ("One Payslip", "one_hr"),
	"Job Offer": ("One Job Offer", "one_hr"),
	"Appointment Letter": ("One Appointment Letter", "one_hr"),
}

#: Who signs a paper that is signed and handed back: the company's side, then
#: the party's, each with the field that names them.
SIGNED = {
	"Quotation": ((_lt("For {0}"), "company"), (_lt("Accepted By"), "customer_name")),
	"Delivery Note": ((_lt("Delivered By"), None), (_lt("Received By"), "customer_name")),
	"Job Offer": ((_lt("For {0}"), "company"), (_lt("Accepted By"), "applicant_name")),
	"Appointment Letter": ((_lt("For {0}"), "company"), (_lt("Accepted By"), "applicant_name")),
}

#: The colour a page has when the company has no Brand Colour.
INK = "#111827"


def settle() -> None:
	"""The blocks, and One's format as each record's default where nobody has
	chosen one or the default is the one ERPNext set when it was installed. A
	format the workspace chose (Printing, or frappe's own Set as Default) is
	kept."""
	_sync_blocks()
	for doctype, (name, _module) in FORMATS.items():
		if not frappe.db.exists("Print Format", name):
			continue
		chosen = frappe.db.get_value(
			"Property Setter",
			{"doc_type": doctype, "property": "default_print_format", "doctype_or_field": "DocType"},
			["value", "is_system_generated"],
			as_dict=True,
		)
		if chosen and (chosen.value == name or not chosen.is_system_generated):
			continue
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocType",
				"property": "default_print_format",
				"value": name,
				"property_type": "Link",
			},
			validate_fields_for_doctype=False,
		)
		frappe.clear_cache(doctype=doctype)


def _sync_blocks() -> None:
	"""frappe syncs a module's print formats on install and migrate, but not
	its field templates, so a new site would print One's formats with every
	block empty. Each is imported here, and only when its file has changed."""
	from frappe.modules.import_file import import_file_by_path

	folder = Path(frappe.get_app_path("onedesk", "one", "print_format_field_template"))
	for path in sorted(folder.glob("*/*.json")):
		import_file_by_path(str(path))


def one_print_block(doc, block: str) -> dict:
	"""What one of One's blocks shows for this record, for its template."""
	shown = {
		"title": title,
		"party": party,
		"details": details,
		"totals": totals,
		"schedule": schedule,
		"bank": bank,
		"payslip": payslip,
		"payment": payment,
		"signatures": signatures,
	}[block](doc)
	return {**shown, "colour": colour(doc)} if shown else {}


def colour(doc) -> str:
	company = doc.get("company")
	return (company and frappe.get_cached_value("Company", company, "one_brand_colour")) or INK


def title(doc) -> dict:
	said, number = TITLES.get(doc.doctype, (_(doc.doctype), _("No")))
	if doc.doctype == "Sales Invoice" and doc.get("is_return"):
		said = _("Credit Note")
	elif doc.doctype == "Sales Invoice" and doc.get("is_debit_note"):
		said = _("Debit Note")
	elif doc.doctype == "Delivery Note" and doc.get("is_return"):
		said = _("Return")
	elif doc.doctype == "Payment Entry" and doc.get("payment_type") == "Pay":
		said, number = _("Payment"), _("Payment No")
	elif doc.doctype == "Payment Entry" and doc.get("payment_type") == "Internal Transfer":
		said, number = _("Transfer"), _("Transfer No")
	# A Print Heading frappe lets the record choose, such as Tax Invoice. A
	# draft or cancelled record is marked by frappe itself, above the page.
	heading = doc.get("select_print_heading")
	return {"title": _(heading) if heading else str(said), "label": str(number), "name": doc.name}


def party(doc) -> dict:
	heading, field = PARTIES.get(doc.doctype, (None, None))
	if not heading:
		return {}
	if doc.doctype == "Payment Entry" and doc.get("payment_type") == "Pay":
		heading = _("Paid To")
	name = doc.get(field) or doc.get("party_name") or doc.get("customer") or doc.get("supplier")
	lines = []
	if doc.doctype == "Salary Slip":
		lines = [doc.get("employee"), doc.get("designation"), doc.get("department")]
	address = doc.get("address_display")
	if doc.doctype == "Delivery Note":
		address = doc.get("shipping_address") or address
	tax = doc.get("tax_id")
	ship = None
	if (
		doc.doctype in ("Sales Order", "Sales Invoice")
		and doc.get("shipping_address_name")
		and doc.get("shipping_address_name") != doc.get("customer_address")
	):
		ship = doc.get("shipping_address")
	return {
		"heading": str(heading),
		"name": name,
		"lines": [one for one in lines if one],
		"address": address,
		"contact": doc.get("contact_display"),
		"email": doc.get("contact_email"),
		"tax": _("Tax ID {0}").format(tax) if tax else None,
		"ship_heading": _("Ship To") if ship else None,
		"ship": ship,
	}


def details(doc) -> dict:
	rows = []
	if doc.doctype == "Salary Slip" and doc.get("start_date"):
		period = "{} – {}".format(doc.get_formatted("start_date"), doc.get_formatted("end_date"))
		rows.append((_("Period"), period))
	for label, field in DETAILS.get(doc.doctype, ()):
		if doc.get(field) and doc.meta.has_field(field):
			rows.append((str(label), doc.get_formatted(field)))
	project = doc.get("project")
	if project:
		rows.append((_("Project"), frappe.get_cached_value("Project", project, "project_name") or project))
	return {"rows": rows} if rows else {}


def money(doc, value, currency: str | None = None) -> str:
	"""A sum as frappe formats it, in the record's currency unless told."""
	return frappe.format_value(
		flt(value), {"fieldtype": "Currency"}, currency=currency or doc.get("currency")
	)


def totals(doc) -> dict:
	if not doc.meta.has_field("grand_total"):
		return {}
	rows = [(_("Subtotal"), money(doc, doc.get("total")))]
	if flt(doc.get("discount_amount")):
		rows.append((_("Discount"), "− " + money(doc, doc.get("discount_amount"))))
	for tax in doc.get("taxes") or []:
		if flt(tax.tax_amount):
			rows.append((tax.description or tax.account_head, money(doc, tax.tax_amount)))
	rounded = flt(doc.get("rounded_total")) and not cint(doc.get("disable_rounded_total"))
	total = doc.get("rounded_total") if rounded else doc.get("grand_total")
	owed = []
	if doc.doctype == "Sales Invoice" and doc.docstatus == 1 and not doc.get("is_return"):
		outstanding = flt(doc.get("outstanding_amount"))
		if outstanding < flt(total):
			owed = [
				(_("Paid"), money(doc, flt(total) - outstanding)),
				(_("Balance Due"), money(doc, outstanding)),
			]
	company_currency = doc.get("company") and frappe.get_cached_value(
		"Company", doc.company, "default_currency"
	)
	base = None
	if company_currency and doc.get("currency") and doc.currency != company_currency:
		base_total = doc.get("base_rounded_total") if rounded else doc.get("base_grand_total")
		base = {
			"label": _("Total in {0}").format(company_currency),
			"value": money(doc, base_total, company_currency),
			"rate": _("1 {0} = {1} {2}").format(
				doc.currency, frappe.format_value(doc.get("conversion_rate"), {"fieldtype": "Float"}), company_currency
			),
		}
	return {
		"rows": rows,
		"total": (_("Total"), money(doc, total)),
		"owed": owed,
		"base": base,
		"words": doc.get("in_words"),
	}


def schedule(doc) -> dict:
	rows = doc.get("payment_schedule") or []
	if len(rows) < 2:
		return {}
	return {
		"heading": _("Payment Schedule"),
		"rows": [
			(
				row.get_formatted("due_date"),
				row.get("description") or row.get("payment_term") or "",
				money(doc, row.payment_amount),
			)
			for row in rows
		],
	}


def bank(doc) -> dict:
	"""The company's own bank account to pay into, its default one first."""
	if not doc.get("company"):
		return {}
	found = frappe.get_all(
		"Bank Account",
		filters={"company": doc.company, "is_company_account": 1, "disabled": 0},
		fields=["bank", "account_name", "bank_account_no", "iban", "branch_code", "is_default"],
		order_by="is_default desc, creation asc",
		limit=1,
	)
	if not found:
		return {}
	one = found[0]
	swift = frappe.get_cached_value("Bank", one.bank, "swift_number") if one.bank else None
	rows = [
		(_("Bank"), one.bank),
		(_("Account Name"), one.account_name),
		(_("Account No"), one.bank_account_no),
		(_("IBAN"), one.iban),
		(_("SWIFT"), swift),
		(_("Branch Code"), one.branch_code),
	]
	return {"heading": _("Pay To"), "rows": [row for row in rows if row[1]]}


def payslip(doc) -> dict:
	if doc.doctype != "Salary Slip":
		return {}

	def lines(table):
		return [(row.salary_component, money(doc, row.amount)) for row in doc.get(table) or [] if flt(row.amount)]

	net = doc.get("rounded_total") or doc.get("net_pay")
	return {
		"earnings": lines("earnings"),
		"deductions": lines("deductions"),
		"gross": (_("Gross Pay"), money(doc, doc.get("gross_pay"))),
		"deducted": (_("Total Deductions"), money(doc, doc.get("total_deduction"))),
		"net": (_("Net Pay"), money(doc, net)),
		"words": doc.get("total_in_words"),
	}


def payment(doc) -> dict:
	if doc.doctype != "Payment Entry":
		return {}
	received = doc.get("payment_type") == "Receive"
	amount, currency = (
		(doc.get("paid_amount"), doc.get("paid_from_account_currency"))
		if received
		else (doc.get("received_amount"), doc.get("paid_to_account_currency"))
	)
	return {
		"label": _("Amount Received") if received else _("Amount Paid"),
		"amount": money(doc, amount, currency),
		"heading": _("Settles"),
		"rows": [
			(_(row.reference_doctype), row.reference_name, money(doc, row.allocated_amount, currency))
			for row in doc.get("references") or []
			if flt(row.allocated_amount)
		],
	}


def signatures(doc) -> dict:
	if doc.doctype not in SIGNED:
		return {}
	sides = []
	for heading, field in SIGNED[doc.doctype]:
		if field == "company":
			sides.append({"heading": str(heading).format(doc.get("company")), "name": None})
		else:
			sides.append({"heading": str(heading), "name": doc.get(field) if field else None})
	return {"sides": sides, "signature": _("Signature"), "date": _("Date")}
