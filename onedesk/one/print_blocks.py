"""What One's print blocks show (point 11, docs/PASSOVER.md).

The parts frappe's print format builder cannot say, as frappe's own Print Format
Field Templates, each drawn from `one_print_block` with frappe's formatted values.
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
	"Purchase Receipt": (_lt("Goods Received Note"), _lt("Receipt No")),
	"Pick List": (_lt("Pick List"), _lt("Pick List No")),
	"Packing Slip": (_lt("Packing Slip"), _lt("Slip No")),
	"Stock Entry": (_lt("Stock Movement"), _lt("Movement No")),
	"Purchase Order": (_lt("Purchase Order"), _lt("Order No")),
	"Request for Quotation": (_lt("Request for Quotation"), _lt("Request No")),
	"Blanket Order": (_lt("Blanket Order"), _lt("Agreement No")),
	"Work Order": (_lt("Work Order"), _lt("Order No")),
	"Asset Movement": (_lt("Equipment Handover"), _lt("Handover No")),
	"Payment Entry": (_lt("Receipt"), _lt("Receipt No")),
	"Salary Slip": (_lt("Payslip"), _lt("Payslip No")),
	"Job Offer": (_lt("Job Offer"), _lt("Offer No")),
	"Appointment Letter": (_lt("Appointment Letter"), _lt("Letter No")),
	"Timesheet": (_lt("Timesheet"), _lt("Timesheet No")),
	"Contract": (_lt("Contract"), _lt("Contract No")),
	"Project": (_lt("Project Status"), _lt("Project")),
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
	"Delivery Note": (
		(_lt("Date"), "posting_date"),
		(_lt("Your Reference"), "po_no"),
		(_lt("Vehicle"), "vehicle_no"),
	),
	"Pick List": ((_lt("Purpose"), "purpose"), (_lt("From"), "parent_warehouse")),
	"Stock Entry": (
		(_lt("Date"), "posting_date"),
		(_lt("Type"), "stock_entry_type"),
		(_lt("From"), "from_warehouse"),
		(_lt("To"), "to_warehouse"),
	),
	"Packing Slip": (
		(_lt("Delivery No"), "delivery_note"),
		(_lt("Net Weight"), "net_weight_pkg"),
		(_lt("Gross Weight"), "gross_weight_pkg"),
	),
	"Purchase Receipt": (
		(_lt("Date"), "posting_date"),
		(_lt("Their Delivery Note"), "supplier_delivery_note"),
		(_lt("Vehicle"), "lr_no"),
	),
	"Purchase Order": ((_lt("Date"), "transaction_date"), (_lt("Required By"), "schedule_date")),
	"Request for Quotation": ((_lt("Date"), "transaction_date"),),
	"Blanket Order": ((_lt("Date"), "order_date"), (_lt("From"), "from_date"), (_lt("To"), "to_date")),
	"Work Order": ((_lt("Starts On"), "planned_start_date"), (_lt("Wanted By"), "expected_delivery_date")),
	"Asset Movement": ((_lt("Date"), "transaction_date"),),
	"Payment Entry": (
		(_lt("Date"), "posting_date"),
		(_lt("Paid By"), "mode_of_payment"),
		(_lt("Reference"), "reference_no"),
		(_lt("Reference Date"), "reference_date"),
	),
	"Salary Slip": ((_lt("Working Days"), "total_working_days"), (_lt("Paid Days"), "payment_days")),
	"Job Offer": ((_lt("Date"), "offer_date"), (_lt("Position"), "designation")),
	"Appointment Letter": ((_lt("Starts On"), "appointment_date"),),
	"Timesheet": ((_lt("Hours"), "total_hours"), (_lt("Billable Hours"), "total_billable_hours")),
	"Contract": (
		(_lt("Starts On"), "start_date"),
		(_lt("Ends On"), "end_date"),
		(_lt("Signed On"), "signed_on"),
	),
	"Project": ((_lt("Starts On"), "expected_start_date"), (_lt("Ends On"), "expected_end_date")),
}

#: The purposes that move goods from one warehouse to another, printed as a
#: transfer note that travels with them.
MOVED = ("Material Transfer", "Material Transfer for Manufacture", "Send to Subcontractor")

#: Who a record is for: its heading, and the field with their name.
PARTIES = {
	"Quotation": (_lt("Prepared For"), "customer_name"),
	"Sales Order": (_lt("Bill To"), "customer_name"),
	"Sales Invoice": (_lt("Bill To"), "customer_name"),
	"Delivery Note": (_lt("Deliver To"), "customer_name"),
	"Purchase Order": (_lt("Supplier"), "supplier_name"),
	# A blanket order is agreed with a supplier or a customer.
	"Blanket Order": (_lt("Agreed With"), None),
	# A work order is made for a project or a customer's order, when it is.
	"Work Order": (_lt("Made For"), None),
	# Equipment is handed to a person, or put back at a location.
	"Asset Movement": (_lt("Handed To"), None),
	"Purchase Receipt": (_lt("Received From"), "supplier_name"),
	"Pick List": (_lt("For"), "customer_name"),
	# A packing slip names its customer through its delivery note.
	"Packing Slip": (_lt("Deliver To"), None),
	# Goods moved to a warehouse go to its address, a site's among them.
	"Stock Entry": (_lt("Deliver To"), None),
	"Payment Entry": (_lt("Received From"), "party_name"),
	"Salary Slip": (_lt("Employee"), "employee_name"),
	"Job Offer": (_lt("Offered To"), "applicant_name"),
	"Appointment Letter": (_lt("Addressed To"), "applicant_name"),
	"Timesheet": (_lt("Employee"), "employee_name"),
	"Contract": (_lt("Agreed With"), "party_full_name"),
	"Project": (_lt("Prepared For"), "customer"),
}

#: The format each record that leaves the company prints with, and the module
#: it is shipped in.
FORMATS = {
	"Quotation": ("One Quotation", "one_crm"),
	"Sales Order": ("One Sales Order", "one_crm"),
	"Sales Invoice": ("One Sales Invoice", "one_book"),
	"Payment Entry": ("One Payment Receipt", "one_book"),
	"Delivery Note": ("One Delivery Note", "one_inventory"),
	"Purchase Receipt": ("One Purchase Receipt", "one_inventory"),
	"Pick List": ("One Pick List", "one_inventory"),
	"Packing Slip": ("One Packing Slip", "one_inventory"),
	"Stock Entry": ("One Stock Entry", "one_inventory"),
	"Purchase Order": ("One Purchase Order", "one_inventory"),
	"Request for Quotation": ("One Request for Quotation", "one_inventory"),
	"Blanket Order": ("One Blanket Order", "one_inventory"),
	"Work Order": ("One Work Order", "one_inventory"),
	"Asset Movement": ("One Equipment Handover", "one_inventory"),
	"Salary Slip": ("One Payslip", "one_hr"),
	"Job Offer": ("One Job Offer", "one_hr"),
	"Appointment Letter": ("One Appointment Letter", "one_hr"),
	"Timesheet": ("One Timesheet", "one_project"),
	"Contract": ("One Contract", "one_crm"),
	"Project": ("One Project Status", "one_project"),
}

#: Who signs a paper that is signed and handed back: the company's side, then
#: the party's, each with the field that names them.
SIGNED = {
	"Quotation": ((_lt("For {0}"), "company"), (_lt("Accepted By"), "customer_name")),
	"Delivery Note": ((_lt("Delivered By"), None), (_lt("Received By"), "customer_name")),
	# The supplier's driver hands the goods over, and the stores sign for them.
	"Purchase Receipt": ((_lt("Delivered By"), "supplier_name"), (_lt("Received By"), None)),
	"Pick List": ((_lt("Picked By"), None), (_lt("Checked By"), None)),
	"Packing Slip": ((_lt("Packed By"), None), (_lt("Received By"), None)),
	"Stock Entry": ((_lt("Sent By"), None), (_lt("Received By"), None)),
	# Whoever hands the equipment over, and whoever takes it, by name.
	"Asset Movement": ((_lt("Handed Over By"), None), (_lt("Received By"), None)),
	"Job Offer": ((_lt("For {0}"), "company"), (_lt("Accepted By"), "applicant_name")),
	"Appointment Letter": ((_lt("For {0}"), "company"), (_lt("Accepted By"), "applicant_name")),
	# The customer billed for the time signs that the hours are theirs.
	"Timesheet": ((_lt("For {0}"), "company"), (_lt("Approved By"), None)),
	"Contract": ((_lt("For {0}"), "company"), (_lt("For {0}"), "party_full_name")),
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
		"progress": progress,
		"time": time_billed,
	}[block](doc)
	return {**shown, "colour": colour(doc)} if shown else {}


def _company(doc) -> str | None:
	"""The company a record is for. A contract names none, and is the
	company's own."""
	return doc.get("company") or frappe.defaults.get_global_default("company")


def colour(doc) -> str:
	company = _company(doc)
	return (company and frappe.get_cached_value("Company", company, "one_brand_colour")) or INK


def title(doc) -> dict:
	said, number = TITLES.get(doc.doctype, (_(doc.doctype), _("No")))
	if doc.doctype == "Sales Invoice" and doc.get("is_return"):
		said = _("Credit Note")
	elif doc.doctype == "Sales Invoice" and doc.get("is_debit_note"):
		said = _("Debit Note")
	elif doc.doctype == "Delivery Note" and doc.get("is_return"):
		said = _("Return")
	elif doc.doctype == "Purchase Receipt" and doc.get("is_return"):
		said = _("Goods Returned")
	elif doc.doctype == "Payment Entry" and doc.get("payment_type") == "Pay":
		said, number = _("Payment"), _("Payment No")
	elif doc.doctype == "Stock Entry" and doc.get("purpose") in MOVED:
		said = _("Transfer Note")
	elif doc.doctype == "Stock Entry" and doc.get("purpose") == "Material Issue":
		said = _("Issue Note")
	elif doc.doctype == "Payment Entry" and doc.get("payment_type") == "Internal Transfer":
		said, number = _("Transfer"), _("Transfer No")
	# A Print Heading frappe lets the record choose, such as Tax Invoice. A
	# draft or cancelled record is marked by frappe itself, above the page.
	heading = doc.get("select_print_heading")
	# A customer knows a project by what it is called, not its number.
	name = doc.get("project_name") if doc.doctype == "Project" else None
	return {"title": _(heading) if heading else str(said), "label": str(number), "name": name or doc.name}


def _made_for(doc, heading) -> dict:
	"""Whom a work order is made for: the project's customer or the customer
	whose order it is. The project itself is among the details, and goods made
	for stock are made for nobody."""
	customer = None
	lines = []
	if doc.get("project"):
		customer = frappe.db.get_value("Project", doc.project, "customer")
	elif doc.get("sales_order"):
		customer = frappe.db.get_value("Sales Order", doc.sales_order, "customer")
		lines = [doc.sales_order]
	if not customer:
		return {}
	name = frappe.db.get_value("Customer", customer, "customer_name") or customer
	return {"heading": str(heading), "name": name, "lines": lines, "address": None}


def party(doc) -> dict:
	heading, field = PARTIES.get(doc.doctype, (None, None))
	if not heading:
		return {}
	if doc.doctype == "Packing Slip":
		delivery = frappe.db.get_value(
			"Delivery Note", doc.delivery_note, ["customer_name", "shipping_address", "address_display"], as_dict=True
		)
		if not delivery:
			return {}
		return {
			"heading": str(heading),
			"name": delivery.customer_name,
			"lines": [],
			"address": delivery.shipping_address or delivery.address_display,
		}
	if doc.doctype == "Stock Entry":
		return _moved_to(doc, heading)
	if doc.doctype == "Payment Entry" and doc.get("payment_type") == "Pay":
		heading = _("Paid To")
	if doc.doctype == "Blanket Order":
		field = "supplier_name" if doc.get("blanket_order_type") == "Purchasing" else "customer_name"
	if doc.doctype == "Work Order":
		return _made_for(doc, heading)
	if doc.doctype == "Asset Movement":
		return _handed_to(doc, heading)
	name = (doc.get(field) if field else None) or doc.get("party_name") or doc.get("customer") or doc.get("supplier")
	lines = []
	if doc.doctype in ("Salary Slip", "Timesheet"):
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


def _moved_to(doc, heading) -> dict:
	"""Where moved goods are going: the one warehouse its lines go to, with
	its address when it has one. Goods used up or going several ways have no
	one place to go."""
	to = {row.t_warehouse for row in doc.items if row.t_warehouse} or {doc.get("to_warehouse")} - {None}
	if len(to) != 1:
		return {}
	place = frappe.db.get_value(
		"Warehouse", to.pop(), ["warehouse_name", "address_line_1", "address_line_2", "city", "phone_no"], as_dict=True
	)
	if not place:
		return {}
	return {
		"heading": str(heading),
		"name": place.warehouse_name,
		"lines": [one for one in (place.address_line_1, place.address_line_2, place.city, place.phone_no) if one],
	}


def _holders(doc, field: str) -> list[str]:
	"""The employees on a handover's lines, by name."""
	names = dict.fromkeys(row.get(field) for row in doc.assets if row.get(field))
	return [frappe.db.get_value("Employee", one, "employee_name") or one for one in names]


def _handed_to(doc, heading) -> dict:
	"""Whoever the equipment goes to, with their job and department, or the
	location it is put back at."""
	people = {row.to_employee for row in doc.assets if row.to_employee}
	if len(people) == 1:
		person = frappe.db.get_value(
			"Employee", people.pop(), ["employee_name", "designation", "department"], as_dict=True
		)
		lines = [person.designation, person.department]
		return {"heading": str(heading), "name": person.employee_name, "lines": [one for one in lines if one]}
	places = {row.target_location for row in doc.assets if row.target_location}
	if not people and len(places) == 1:
		return {"heading": _("Kept At"), "name": places.pop(), "lines": []}
	return {}


def details(doc) -> dict:
	rows = []
	if doc.doctype in ("Salary Slip", "Timesheet") and doc.get("start_date"):
		period = "{} – {}".format(doc.get_formatted("start_date"), doc.get_formatted("end_date"))
		rows.append((_("Period"), period))
	for label, field in DETAILS.get(doc.doctype, ()):
		if doc.get(field) and doc.meta.has_field(field):
			value = doc.get_formatted(field)
			# A packing slip's weights are in its own unit, kept beside them.
			unit = doc.get(field.replace("_pkg", "_uom")) if field.endswith("_pkg") else None
			rows.append((str(label), f"{value} {unit}" if unit else value))
	if doc.doctype == "Packing Slip" and doc.get("from_case_no"):
		cases = doc.from_case_no if doc.from_case_no == doc.to_case_no else f"{doc.from_case_no}–{doc.to_case_no}"
		rows.append((_("Cases"), str(cases)))
	project = doc.get("project") or doc.get("parent_project")
	if doc.doctype == "Contract" and doc.get("document_type") == "Project":
		project = doc.get("document_name")
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
				doc.currency,
				frappe.format_value(doc.get("conversion_rate"), {"fieldtype": "Float"}),
				company_currency,
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
		return [
			(row.salary_component, money(doc, row.amount)) for row in doc.get(table) or [] if flt(row.amount)
		]

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
	if doc.doctype == "Asset Movement":
		return _handover_signatures(doc)
	sides = []
	for heading, field in SIGNED[doc.doctype]:
		if field == "company":
			sides.append({"heading": str(heading).format(_company(doc)), "name": None})
		elif "{0}" in str(heading):
			sides.append(
				{"heading": str(heading).format(doc.get(field) or doc.get("party_name")), "name": None}
			)
		else:
			sides.append({"heading": str(heading), "name": doc.get(field) if field else None})
	return {"sides": sides, "signature": _("Signature"), "date": _("Date")}


def _handover_signatures(doc) -> dict:
	"""Who gave the equipment and who took it, each by name when one person
	did, and what the person taking it agrees to."""
	(given, _given), (taken, _taken) = SIGNED["Asset Movement"]
	gave, took = _holders(doc, "from_employee"), _holders(doc, "to_employee")
	return {
		"sides": [
			# From the stores rather than a person, the company hands it over.
			{"heading": str(given), "name": gave[0] if len(gave) == 1 else None if gave else _company(doc)},
			{"heading": str(taken), "name": took[0] if len(took) == 1 else None},
		],
		"pledge": _("I have received the equipment above in good order. I will look after it, and give it back when I am asked.")
		if took
		else None,
		"signature": _("Signature"),
		"date": _("Date"),
	}


#: How many of a project's open tasks a status lists, soonest first.
NEXT = 8


def progress(doc) -> dict:
	"""A project's status on paper, as its customer's page says it: how far it
	has got, when it ends, its milestones, what comes next and its invoices."""
	if doc.doctype != "Project":
		return {}
	from onedesk.one_project import portal

	said = portal.view(doc.name)

	def row(task) -> tuple:
		due = frappe.format_value(task.due, {"fieldtype": "Date"}) if task.due else ""
		return (task.subject, task.shown, due)

	waiting = sorted(
		(one for one in said["tasks"] if one.status != "Completed"), key=lambda one: str(one.due or "9999")
	)
	return {
		"heading": _("Progress"),
		"share": int(said["share"] or 0),
		"done": _("{0} of {1} tasks done").format(said["done"], said["total"]) if said["total"] else "",
		"when": portal.when(said["days_left"]) or "",
		"milestones_heading": _("Milestones"),
		"milestones": [row(one) for one in said["milestones"]],
		"next_heading": _("Next"),
		"next": [row(one) for one in waiting[:NEXT]],
		# Its sub-projects for the same customer, as its portal page lists them.
		"projects_heading": _("Sub-projects"),
		"projects": [
			(
				one.project_name,
				_("{0}% done").format(round(flt(one.percent_complete))),
				frappe.format_value(one.expected_end_date, {"fieldtype": "Date"}) if one.expected_end_date else "",
			)
			for one in said["projects"]
		],
		"contract": money(doc, said["order"].grand_total, said["order"].currency) if said.get("order") else "",
		"contract_label": _("Contract"),
		"invoices_heading": _("Invoices"),
		"invoices": [
			(
				one.name,
				frappe.format_value(one.posting_date, {"fieldtype": "Date"}),
				money(doc, one.grand_total, one.currency),
				money(doc, one.outstanding_amount, one.currency),
			)
			for one in said["invoices"]
		],
		"columns": (_("Invoice"), _("Date"), _("Total"), _("Outstanding")),
	}


def time_billed(doc) -> dict:
	"""The hours an invoice bills, from ERPNext's own Time Sheets table on
	it: the day, the activity, who did it, the hours and what they come to.
	A retainer's month is billed as its fee, so its hours show without what
	they would come to. Nothing for an invoice that bills no time."""
	if doc.doctype != "Sales Invoice" or not doc.get("timesheets"):
		return {}
	sheets = {one.time_sheet for one in doc.timesheets if one.time_sheet}
	who = dict(
		frappe.get_all("Timesheet", filters={"name": ["in", list(sheets)]}, fields=["name", "employee_name"], as_list=True)
	)
	details = [one.timesheet_detail for one in doc.timesheets if one.timesheet_detail]
	projects = set(frappe.get_all("Timesheet Detail", filters={"name": ["in", details]}, pluck="project")) | {doc.get("project")}
	kinds = set(frappe.get_all("Project", filters={"name": ["in", list(projects - {None})]}, pluck="one_kind"))
	priced = "Retainer" not in kinds
	rows = [
		(
			frappe.format_value(one.from_time, {"fieldtype": "Date"}) if one.from_time else "",
			one.activity_type or "",
			who.get(one.time_sheet) or "",
			f"{flt(one.billing_hours):g}",
			money(doc, one.billing_amount) if priced else "",
		)
		for one in sorted(doc.timesheets, key=lambda one: str(one.from_time or ""))
	]
	return {
		"heading": _("Time Billed") if priced else _("Time Spent"),
		"columns": (_("Date"), _("Activity"), _("Employee"), _("Hours"), *((_("Amount"),) if priced else ())),
		"rows": rows,
		"priced": priced,
		"total_label": _("Total"),
		"hours": f"{sum(flt(one.billing_hours) for one in doc.timesheets):g}",
		"amount": money(doc, sum(flt(one.billing_amount) for one in doc.timesheets)) if priced else "",
	}
