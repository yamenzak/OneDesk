"""What One's print blocks show (point 11, docs/PASSOVER.md).

The parts frappe's print format builder cannot say, as frappe's own Print Format
Field Templates, each drawn from `one_print_block` with frappe's formatted values.
"""

import re
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
	"Dunning": (_lt("Payment Reminder"), _lt("Reminder No")),
	"Salary Slip": (_lt("Payslip"), _lt("Payslip No")),
	"Job Offer": (_lt("Job Offer"), _lt("Offer No")),
	"Appointment Letter": (_lt("Appointment Letter"), _lt("Letter No")),
	"Timesheet": (_lt("Timesheet"), _lt("Timesheet No")),
	"Contract": (_lt("Contract"), _lt("Contract No")),
	"Project": (_lt("Project Status"), _lt("Project")),
	"Maintenance Schedule": (_lt("Maintenance Plan"), _lt("Plan No")),
	"Maintenance Visit": (_lt("Service Report"), _lt("Report No")),
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
	"Dunning": ((_lt("Date"), "posting_date"),),
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
	"Maintenance Schedule": ((_lt("Date"), "transaction_date"),),
	"Maintenance Visit": (
		(_lt("Date"), "mntc_date"),
		(_lt("Type"), "maintenance_type"),
		(_lt("Status"), "completion_status"),
	),
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
	"Dunning": (_lt("Bill To"), "customer_name"),
	"Salary Slip": (_lt("Employee"), "employee_name"),
	"Job Offer": (_lt("Offered To"), "applicant_name"),
	"Appointment Letter": (_lt("Addressed To"), "applicant_name"),
	"Timesheet": (_lt("Employee"), "employee_name"),
	"Contract": (_lt("Agreed With"), "party_full_name"),
	"Project": (_lt("Prepared For"), "customer"),
	"Maintenance Schedule": (_lt("Prepared For"), "customer_name"),
	"Maintenance Visit": (_lt("Customer"), "customer_name"),
}

#: The format each record that leaves the company prints with, and the module
#: it is shipped in.
FORMATS = {
	"Quotation": ("One Quotation", "one_crm"),
	"Sales Order": ("One Sales Order", "one_crm"),
	"Sales Invoice": ("One Sales Invoice", "one_book"),
	"Purchase Invoice": ("One Purchase Invoice", "one_book"),
	"Journal Entry": ("One Journal Voucher", "one_book"),
	"Payment Entry": ("One Payment Receipt", "one_book"),
	"Dunning": ("One Payment Reminder", "one_book"),
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
	"Maintenance Schedule": ("One Maintenance Plan", "one_crm"),
	"Maintenance Visit": ("One Service Report", "one_crm"),
}

#: The colour a page has when the company has no Brand Colour.
INK = "#111827"


#: ERPNext's own formats each of One's stands in for, turned off so the print
#: menu offers each version once. ERPNext's come back on if One's is removed.
REPLACES = {
	"One Sales Invoice": ("Sales Invoice Modern", "Tax Invoice", "Sales Invoice Return"),
	"One Sales Invoice Classic": ("Sales Invoice Classic",),
	"One Sales Invoice Bordered": ("Sales Invoice Bordered",),
	"One Sales Invoice with Images": ("Sales Invoice Modern with Images",),
	"One Simplified Tax Invoice": ("Simplified Tax Invoice",),
	"One Detailed Tax Invoice": ("Detailed Tax Invoice",),
	"One Sales Voucher": ("Sales Auditing Voucher",),
	"One Proforma Invoice": ("Proforma Invoice",),
	"One Quotation": ("Quotation Modern",),
	"One Quotation Classic": ("Quotation Classic",),
	"One Quotation Bordered": ("Quotation Bordered",),
	"One Quotation with Images": ("Quotation Modern with Images",),
	"One Sales Order": ("Sales Order Modern",),
	"One Sales Order Classic": ("Sales Order Classic",),
	"One Sales Order Bordered": ("Sales Order Bordered",),
	"One Sales Order with Images": ("Sales Order Modern with Images",),
	"One Delivery Note": ("Delivery Note Modern",),
	"One Delivery Note Classic": ("Delivery Note Classic",),
	"One Delivery Note Bordered": ("Delivery Note Bordered",),
	"One Delivery Note with Images": ("Delivery Note Modern with Images",),
	"One Purchase Order": ("Purchase Order Modern",),
	"One Purchase Order Classic": ("Purchase Order Classic",),
	"One Purchase Order Bordered": ("Purchase Order Bordered",),
	"One Purchase Order with Images": ("Purchase Order Modern with Images",),
	"One Purchase Invoice": ("Purchase Invoice Modern",),
	"One Purchase Invoice Classic": ("Purchase Invoice Classic",),
	"One Purchase Invoice Bordered": ("Purchase Invoice Bordered",),
	"One Purchase Invoice with Images": ("Purchase Invoice Modern with Images",),
	"One Request for Quotation": ("Request for Quotation Modern",),
	"One Request for Quotation Classic": ("Request for Quotation Classic",),
	"One Request for Quotation Bordered": ("Request for Quotation Bordered",),
	"One Request for Quotation with Images": ("Request for Quotation Modern with Images",),
	"One Purchase Voucher": ("Purchase Auditing Voucher",),
	"One Purchase Receipt with Serial Numbers": ("Purchase Receipt Serial and Batch Bundle Print",),
	"One Payment Voucher": ("Bank and Cash Payment Voucher",),
	"One Journal Voucher": ("Journal Auditing Voucher",),
	"One Journal Credit Note": ("Credit Note",),
	"One Payment Reminder": ("Dunning Letter",),
	"One Pick List": ("Pick List",),
	"One Payslip": ("Salary Slip Classic",),
	"One Payslip Compact": ("Salary Slip Compact",),
	"One Salary Statement": ("Salary Slip Detailed",),
	"One Job Offer": ("Job Offer",),
	"One Appointment Letter": ("Standard Appointment Letter",),
}


def settle() -> None:
	"""The blocks, ERPNext's formats One's replace turned off, and One's
	format as each record's default where nobody has chosen one or the default
	is the one ERPNext set when it was installed. A format the workspace
	chose (Printing, or frappe's own Set as Default) is kept."""
	_sync_blocks()
	for ours, theirs in REPLACES.items():
		ready = frappe.db.exists("Print Format", {"name": ours, "disabled": 0})
		for one in theirs:
			if frappe.db.exists("Print Format", one):
				frappe.db.set_value("Print Format", one, "disabled", 0 if not ready else 1, update_modified=False)
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
	# A block a format no longer uses leaves with its file.
	shipped = {path.parent.name for path in folder.glob("*/*.json")}
	for name in frappe.get_all("Print Format Field Template", filters={"module": "One", "standard": 1}, pluck="name"):
		if frappe.scrub(name) not in shipped:
			frappe.delete_doc("Print Format Field Template", name, ignore_permissions=True, force=True)


def one_print_block(doc, block: str) -> dict:
	"""What one of One's blocks shows for this record, for its template."""
	shown = {
		"title": title,
		"party": party,
		"details": details,
		"progress": progress,
	}[block](doc)
	if not shown:
		return {}
	from onedesk.one.letter_heads import readable

	# The Brand Colour, and the same darkened where it is text, as a letter head does.
	return {**shown, "colour": colour(doc), "ink": readable(colour(doc))}


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
	# In the UAE a VAT-registered company's invoice is a Tax Invoice, and a
	# return a Tax Credit Note, each with the company's TRN (FTA, Article 59).
	trn = _trn(doc)
	heading = doc.get("select_print_heading")
	if trn and doc.doctype == "Sales Invoice":
		said = _("Tax Credit Note") if doc.get("is_return") else _("Tax Invoice")
		if doc.get("is_return"):
			number = _("Credit Note No")
		# ERPNext heads every return "Credit Note" on its own; that gives way.
		if heading in AUTOMATIC:
			heading = None
	# A Print Heading frappe lets the record choose, such as Tax Invoice. A
	# draft or cancelled record is marked by frappe itself, above the page.
	# A customer knows a project by what it is called, not its number.
	name = doc.get("project_name") if doc.doctype == "Project" else None
	return {
		"title": _(heading) if heading else str(said),
		"label": str(number),
		"name": name or doc.name,
		"tax": _("TRN {0}").format(trn) if trn else None,
		"status": _status(doc),
	}


#: Where an invoice stands, as its reader is told beside its title: the
#: words and the colours of the mark (text, ground).
STANDING = {
	"Paid": ("#15803d", "#dcfce7"),
	"Partly Paid": ("#b45309", "#fef3c7"),
	"Unpaid": ("#374151", "#f3f4f6"),
	"Overdue": ("#b91c1c", "#fee2e2"),
}


def _status(doc) -> dict | None:
	"""A submitted invoice's standing, when it is one a reader acts on."""
	if doc.doctype not in ("Sales Invoice", "Purchase Invoice") or doc.docstatus != 1 or doc.get("is_return"):
		return None
	standing = doc.get("status")
	if standing in ("Partly Paid and Discounted", "Unpaid and Discounted"):
		standing = standing.split(" and ")[0]
	if standing not in STANDING:
		return None
	ink, ground = STANDING[standing]
	return {"text": _(standing), "ink": ink, "ground": ground}


#: The Print Headings ERPNext sets on a return by itself, not by choice.
AUTOMATIC = ("Credit Note", "Debit Note")


def _trn(doc) -> str | None:
	"""The company's TRN, where an invoice must carry it: a sales invoice of a
	company in the UAE that has one."""
	if doc.doctype != "Sales Invoice":
		return None
	from onedesk.one_book import vat

	company = _company(doc)
	if not company or not vat.in_uae(company):
		return None
	return frappe.get_cached_value("Company", company, "tax_id") or None


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
	address = _trimmed(address)
	tax = doc.get("tax_id")
	ship = None
	if (
		doc.doctype in ("Sales Order", "Sales Invoice")
		and doc.get("shipping_address_name")
		and doc.get("shipping_address_name") != doc.get("customer_address")
	):
		ship = _trimmed(doc.get("shipping_address"))
	return {
		"heading": str(heading),
		"name": name,
		"lines": [one for one in lines if one],
		"address": address,
		"contact": doc.get("contact_display"),
		"email": doc.get("contact_email"),
		"tax": (_("TRN {0}") if _trn(doc) else _("Tax ID {0}")).format(tax) if tax else None,
		"ship_heading": _("Ship To") if ship else None,
		"ship": ship,
	}


def _trimmed(html: str | None) -> str | None:
	"""An address as ERPNext keeps it, less the line breaks at its end. Pure."""
	return re.sub(r"(\s*<br\s*/?>\s*)+$", "", html or "").strip() or None


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
	"""A sum in the record's currency unless told, said by its code before the
	number as frappe formats it: AED 1,234.00. A currency's own symbol, such as
	the dirham's, reads differently on every printer and to every reader."""
	code = currency or doc.get("currency") or ""
	return f"{code} {number(doc, value, code)}".strip()


def number(doc, value, currency: str | None = None) -> str:
	"""A sum as frappe formats it, without its currency: 1,234.00."""
	from frappe.utils import fmt_money

	code = currency or doc.get("currency")
	precision = cint(frappe.db.get_default("currency_precision")) or 2
	return fmt_money(flt(value), precision=precision, currency=None, format=_number_format(code))


def _number_format(currency: str | None) -> str | None:
	return (currency and frappe.get_cached_value("Currency", currency, "number_format")) or None


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
