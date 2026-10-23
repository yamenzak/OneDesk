"""What One's print blocks show (point 11, docs/PASSOVER.md).

The parts frappe's print format builder cannot say, as frappe's own Print Format
Field Templates, each drawn from `one_print_block` with frappe's formatted values.
"""

import re
from pathlib import Path

import frappe
from frappe import _, _lt
from frappe.utils import cint, flt

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

MOVED = ("Material Transfer", "Material Transfer for Manufacture", "Send to Subcontractor")

PARTIES = {
	"Quotation": (_lt("Prepared For"), "customer_name"),
	"Sales Order": (_lt("Bill To"), "customer_name"),
	"Sales Invoice": (_lt("Bill To"), "customer_name"),
	"Delivery Note": (_lt("Deliver To"), "customer_name"),
	"Purchase Order": (_lt("Supplier"), "supplier_name"),
	"Blanket Order": (_lt("Agreed With"), None),
	"Work Order": (_lt("Made For"), None),
	"Asset Movement": (_lt("Handed To"), None),
	"Purchase Receipt": (_lt("Received From"), "supplier_name"),
	"Pick List": (_lt("For"), "customer_name"),
	"Packing Slip": (_lt("Deliver To"), None),
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

SOLD = ("Sales Invoice", "POS Invoice")
for _said in (TITLES, DETAILS, PARTIES):
	_said["POS Invoice"] = _said["Sales Invoice"]

FORMATS = {
	"Quotation": ("One Quotation", "one_crm"),
	"Sales Order": ("One Sales Order", "one_crm"),
	"Sales Invoice": ("One Sales Invoice", "one_book"),
	"POS Invoice": ("One POS Invoice", "one_book"),
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
	"Installation Note": ("One Installation Note", "one_crm"),
	"Subcontracting Order": ("One Subcontracting Order", "one_inventory"),
	"Subcontracting Receipt": ("One Subcontracting Receipt", "one_inventory"),
	"Subcontracting Inward Order": ("One Subcontracting Inward Order", "one_inventory"),
	"Payment Order": ("One Payment Order", "one_book"),
	"Bank Guarantee": ("One Bank Guarantee", "one_book"),
	"Material Request": ("One Material Request", "one_inventory"),
	"Supplier Quotation": ("One Supplier Quotation", "one_inventory"),
	"Delivery Trip": ("One Delivery Trip", "one_inventory"),
	"Quality Inspection": ("One Quality Inspection", "one_inventory"),
	"Payment Request": ("One Payment Request", "one_book"),
	"Expense Claim": ("One Expense Claim", "one_hr"),
	"Employee Advance": ("One Employee Advance", "one_hr"),
	"Job Card": ("One Job Card", "one_inventory"),
	"BOM": ("One Bill of Materials", "one_inventory"),
	"Asset": ("One Asset Card", "one_inventory"),
	"Asset Capitalization": ("One Asset Capitalization", "one_inventory"),
	"Asset Maintenance Log": ("One Maintenance Record", "one_inventory"),
	"Asset Repair": ("One Repair Record", "one_inventory"),
	"Asset Shift Allocation": ("One Asset Shift Allocation", "one_inventory"),
	"Asset Value Adjustment": ("One Asset Value Adjustment", "one_inventory"),
	"BOM Creator": ("One BOM Creator", "one_inventory"),
	"Bank Transaction": ("One Bank Transaction", "one_book"),
	"Budget": ("One Budget", "one_book"),
	"Cost Center Allocation": ("One Cost Center Allocation", "one_book"),
	"Exchange Rate Revaluation": ("One Exchange Rate Revaluation", "one_book"),
	"Invoice Discounting": ("One Invoice Discounting", "one_book"),
	"Item Standard Cost": ("One Item Standard Cost", "one_inventory"),
	"Landed Cost Voucher": ("One Landed Cost Voucher", "one_inventory"),
	"Period Closing Voucher": ("One Period Closing Voucher", "one_book"),
	"Process Deferred Accounting": ("One Process Deferred Accounting", "one_book"),
	"Process Payment Reconciliation": ("One Process Payment Reconciliation", "one_book"),
	"Product Bundle": ("One Product Bundle", "one_inventory"),
	"Production Plan": ("One Production Plan", "one_inventory"),
	"Project Update": ("One Project Update", "one_project"),
	"Repost Accounting Ledger": ("One Repost Accounting Ledger", "one_book"),
	"Repost Payment Ledger": ("One Repost Payment Ledger", "one_book"),
	"Sales Forecast": ("One Sales Forecast", "one_inventory"),
	"Serial and Batch Bundle": ("One Serial and Batch Bundle", "one_inventory"),
	"Share Transfer": ("One Share Transfer", "one_book"),
	"Shipment": ("One Shipment", "one_inventory"),
	"Stock Closing Entry": ("One Stock Closing Entry", "one_inventory"),
	"Stock Reconciliation": ("One Stock Reconciliation", "one_inventory"),
	"Stock Reservation Entry": ("One Stock Reservation Entry", "one_inventory"),
	"Supplier Scorecard Period": ("One Supplier Scorecard Period", "one_inventory"),
	"Telephony Call Type": ("One Telephony Call Type", "one_crm"),
	"Transaction Deletion Record": ("One Transaction Deletion Record", "one_book"),
	"Credit Ledger Entry": ("One Credit Ledger Entry", "one_admin"),
	"Additional Salary": ("One Additional Salary", "one_hr"),
	"Appraisal": ("One Appraisal", "one_hr"),
	"Arrear": ("One Arrear", "one_hr"),
	"Attendance": ("One Attendance", "one_hr"),
	"Attendance Request": ("One Attendance Request", "one_hr"),
	"Compensatory Leave Request": ("One Compensatory Leave Request", "one_hr"),
	"Employee Benefit Application": ("One Employee Benefit Application", "one_hr"),
	"Employee Benefit Claim": ("One Employee Benefit Claim", "one_hr"),
	"Employee Grievance": ("One Employee Grievance", "one_hr"),
	"Employee Incentive": ("One Employee Incentive", "one_hr"),
	"Employee Onboarding": ("One Employee Onboarding", "one_hr"),
	"Employee Other Income": ("One Employee Other Income", "one_hr"),
	"Employee Performance Feedback": ("One Employee Performance Feedback", "one_hr"),
	"Employee Promotion": ("One Promotion Letter", "one_hr"),
	"Employee Referral": ("One Employee Referral", "one_hr"),
	"Employee Separation": ("One Employee Separation", "one_hr"),
	"Employee Tax Exemption Declaration": ("One Employee Tax Exemption Declaration", "one_hr"),
	"Employee Tax Exemption Proof Submission": ("One Employee Tax Exemption Proof Submission", "one_hr"),
	"Employee Transfer": ("One Transfer Letter", "one_hr"),
	"Exit Interview": ("One Exit Interview", "one_hr"),
	"Full and Final Statement": ("One Full and Final Settlement", "one_hr"),
	"Gratuity": ("One Gratuity", "one_hr"),
	"Holiday List Assignment": ("One Holiday List Assignment", "one_hr"),
	"Income Tax Slab": ("One Income Tax Slab", "one_hr"),
	"Interview": ("One Interview", "one_hr"),
	"Leave Adjustment": ("One Leave Adjustment", "one_hr"),
	"Leave Allocation": ("One Leave Allocation", "one_hr"),
	"Leave Application": ("One Leave Application", "one_hr"),
	"Leave Encashment": ("One Leave Encashment", "one_hr"),
	"Leave Policy": ("One Leave Policy", "one_hr"),
	"Leave Policy Assignment": ("One Leave Policy Assignment", "one_hr"),
	"Overtime Slip": ("One Overtime Slip", "one_hr"),
	"Payroll Correction": ("One Payroll Correction", "one_hr"),
	"Payroll Entry": ("One Payroll Run", "one_hr"),
	"Retention Bonus": ("One Retention Bonus", "one_hr"),
	"Salary Structure": ("One Salary Structure", "one_hr"),
	"Salary Structure Assignment": ("One Salary Structure Assignment", "one_hr"),
	"Salary Withholding": ("One Salary Withholding", "one_hr"),
	"Shift Assignment": ("One Shift Assignment", "one_hr"),
	"Shift Request": ("One Shift Request", "one_hr"),
	"Shift Schedule": ("One Shift Schedule", "one_hr"),
	"Staffing Plan": ("One Staffing Plan", "one_hr"),
	"Training Event": ("One Training Event", "one_hr"),
	"Training Feedback": ("One Training Feedback", "one_hr"),
	"Training Result": ("One Training Result", "one_hr"),
	"Travel Request": ("One Travel Request", "one_hr"),
	"Vehicle Log": ("One Vehicle Log", "one_hr"),
	"Customer": ("One Statement of Account", "one_book"),
	"Supplier": ("One Supplier Statement", "one_book"),
	"Employee": ("One Salary Certificate", "one_hr"),
}

INK = "#111827"


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
	"""The blocks, a country's formats offered only there, ERPNext's formats
	One's replace turned off, and One's format as each record's default where
	nobody has chosen one or the default is the one ERPNext set when it was
	installed. A format the workspace chose (Printing, or frappe's own Set as
	Default) is kept."""
	from onedesk.one import countries

	_sync_blocks()
	here = offered()
	for ours, theirs in REPLACES.items():
		ready = frappe.db.exists("Print Format", {"name": ours, "disabled": 0})
		for one in theirs:
			if frappe.db.exists("Print Format", one):
				off = ready or not countries.shown(ours, here)
				frappe.db.set_value("Print Format", one, "disabled", 1 if off else 0, update_modified=False)
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
	_proforma()


def offered(*_args) -> set[str]:
	"""after_migrate, and when a company is saved: a format that is one
	country's (one/countries.py) is offered only where a company is in it."""
	from onedesk.one import countries

	here = countries.ours()
	for name in countries.ONLY_IN:
		if frappe.db.exists("Print Format", name):
			off = 0 if countries.shown(name, here) else 1
			frappe.db.set_value("Print Format", name, "disabled", off, update_modified=False)
	return here


def _proforma() -> None:
	"""ERPNext's Proforma Invoice prints its Sales Order through the format
	Selling Settings names, else its own, which One's replaces."""
	ours = "One Proforma Invoice"
	chosen = frappe.db.get_single_value("Selling Settings", "default_proforma_print_format")
	if not frappe.db.exists("Print Format", {"name": ours, "disabled": 0}):
		return
	if not chosen or chosen in REPLACES[ours]:
		frappe.db.set_single_value("Selling Settings", "default_proforma_print_format", ours)


def _sync_blocks() -> None:
	"""frappe syncs a module's print formats on install and migrate, but not
	its field templates, so a new site would print One's formats with every
	block empty. Each is imported here, and only when its file has changed."""
	from frappe.modules.import_file import import_file_by_path

	folder = Path(frappe.get_app_path("onedesk", "one", "print_format_field_template"))
	for path in sorted(folder.glob("*/*.json")):
		import_file_by_path(str(path))
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
		"claim": claim,
		"statement": statement,
		"salary_certificate": salary_certificate,
		"experience_letter": experience_letter,
		"leave_balance": leave_balance,
		"total": total,
	}[block](doc)
	if not shown:
		return {}
	from onedesk.one.letter_heads import readable

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
	if doc.doctype in SOLD and doc.get("is_return"):
		said = _("Credit Note")
	elif doc.doctype in SOLD and doc.get("is_debit_note"):
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
	tax = _taxed(doc)
	heading = doc.get("select_print_heading")
	if tax:
		said = _("Tax Credit Note") if doc.get("is_return") else _("Tax Invoice")
		if doc.get("is_return"):
			number = _("Credit Note No")
		if heading in AUTOMATIC:
			heading = None
	name = doc.get("project_name") if doc.doctype == "Project" else None
	return {
		"title": _(heading) if heading else str(said),
		"label": str(number),
		"name": name or doc.name,
		"tax": (_("TRN {0}") if _trn(doc) else _("Tax ID {0}")).format(tax) if tax else None,
		"status": _status(doc),
	}


STANDING = {
	"Paid": ("#15803d", "#dcfce7"),
	"Partly Paid": ("#b45309", "#fef3c7"),
	"Unpaid": ("#374151", "#f3f4f6"),
	"Overdue": ("#b91c1c", "#fee2e2"),
}


def _status(doc) -> dict | None:
	"""A submitted invoice's standing, when it is one a reader acts on."""
	if doc.doctype not in (*SOLD, "Purchase Invoice") or doc.docstatus != 1 or doc.get("is_return"):
		return None
	standing = doc.get("status")
	if standing in ("Partly Paid and Discounted", "Unpaid and Discounted"):
		standing = standing.split(" and ")[0]
	if standing not in STANDING:
		return None
	ink, ground = STANDING[standing]
	return {"text": _(standing), "ink": ink, "ground": ground}


AUTOMATIC = ("Credit Note", "Debit Note")


def _taxed(doc) -> str | None:
	"""The company's tax number, where a sales invoice carrying it is a tax
	invoice: in a country one/countries.py lists, when the company has one."""
	if doc.doctype not in SOLD:
		return None
	from onedesk.one import countries

	company = _company(doc)
	if not countries.tax_invoice(company):
		return None
	return frappe.get_cached_value("Company", company, "tax_id") or None


def _trn(doc) -> str | None:
	"""The company's TRN: its tax number on a tax invoice, in the UAE."""
	from onedesk.one_book import vat

	found = _taxed(doc)
	return found if found and vat.in_uae(_company(doc)) else None


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
		doc.doctype in ("Sales Order", *SOLD)
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


def claim(doc) -> dict:
	"""Where a project's contract stands as of this invoice: the contract,
	billed before, this claim, billed to date, received and left to bill."""
	if doc.doctype != "Sales Invoice" or doc.get("is_return"):
		return {}
	from onedesk.one_project import claims

	said = claims.standing(doc)
	if not said:
		return {}
	heading = _("Claim {0} on the Contract").format(said["claim"]) if said["claim"] else _("Contract Statement")
	return {
		"heading": heading,
		"rows": [
			(_("Contract"), money(doc, said["contract"]), False),
			(_("Billed Before"), money(doc, said["before"]), False),
			(_("This Claim"), money(doc, said["this"]), False),
			(_("Billed to Date"), money(doc, said["to_date"]), True),
			(_("Received to Date"), money(doc, said["received"]), False),
			(_("Left to Bill"), money(doc, said["left"]), True),
		],
	}


def _day(value) -> str:
	"""A date as One's papers print it: 18 Oct 2026."""
	from frappe.utils import formatdate

	return formatdate(value, "dd MMM yyyy") if value else ""


PAID = {"Pay": _lt("Payment"), "Receive": _lt("Payment")}


def _currency(company: str | None) -> str:
	return (company and frappe.get_cached_value("Company", company, "default_currency")) or ""


AGES = ((0, _lt("Not Due")), (30, _lt("1-30 Days")), (60, _lt("31-60 Days")), (90, _lt("61-90 Days")), (None, _lt("Over 90 Days")))


def statement(doc) -> dict:
	"""A customer's or a supplier's account this fiscal year: what it stood at
	before, every document since with the balance after it, how old what's
	still open is, and the invoices it's made of. A customer's balance is
	what they owe us, a supplier's what we owe them."""
	if doc.doctype not in ("Customer", "Supplier"):
		return {}
	from erpnext.accounts.utils import get_fiscal_year
	from frappe.utils import date_diff, getdate, today

	company = _company(doc)
	currency = _currency(company)
	start = get_fiscal_year(today(), company=company)[1]
	sign = 1 if doc.doctype == "Customer" else -1
	gle = frappe.qb.DocType("GL Entry")
	mine = (gle.party_type == doc.doctype) & (gle.party == doc.name) & (gle.company == company) & (gle.is_cancelled == 0)
	from frappe.query_builder.functions import Sum

	before = frappe.qb.from_(gle).select(Sum(gle.debit - gle.credit)).where(mine & (gle.posting_date < start)).run()
	opening = sign * flt(before[0][0] if before else 0)
	moved = (
		frappe.qb.from_(gle)
		.select(gle.posting_date, gle.voucher_type, gle.voucher_subtype, gle.voucher_no, Sum(gle.debit).as_("debit"), Sum(gle.credit).as_("credit"))
		.where(mine & (gle.posting_date >= start))
		.groupby(gle.posting_date, gle.voucher_type, gle.voucher_subtype, gle.voucher_no)
		.orderby(gle.posting_date)
		.orderby(gle.voucher_no)
		.run(as_dict=True)
	)
	balance, rows, charged, settled = opening, [], 0.0, 0.0
	for one in moved:
		up, down = (one.debit, one.credit) if sign == 1 else (one.credit, one.debit)
		balance += flt(up) - flt(down)
		charged += flt(up)
		settled += flt(down)
		rows.append((
			_day(one.posting_date), str(PAID.get(one.voucher_subtype) or _(one.voucher_subtype or one.voucher_type)), one.voucher_no,
			number(doc, up, currency) if up else "", number(doc, down, currency) if down else "", number(doc, balance, currency),
		))
	invoice = "Sales Invoice" if doc.doctype == "Customer" else "Purchase Invoice"
	party = "customer" if doc.doctype == "Customer" else "supplier"
	open_ = frappe.get_all(
		invoice,
		filters={party: doc.name, "company": company, "docstatus": 1, "outstanding_amount": ["!=", 0]},
		fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount"],
		order_by="due_date asc",
	)
	aged = [0.0] * len(AGES)
	invoices = []
	for one in open_:
		late = max(date_diff(getdate(), one.due_date or one.posting_date), 0)
		for i, (upto, _label) in enumerate(AGES):
			if upto is None or late <= upto:
				aged[i] += flt(one.outstanding_amount)
				break
		invoices.append((one.name, _day(one.posting_date), _day(one.due_date), number(doc, one.grand_total, currency),
			number(doc, one.outstanding_amount, currency), str(late) if late else ""))
	return {
		"period": _("{0} to {1}").format(_day(start), _day(today())),
		"period_label": _("Period"),
		"summary": (
			(_("Opening Balance"), money(doc, opening, currency)),
			(_("Invoiced") if sign == 1 else _("Billed"), money(doc, charged, currency)),
			(_("Paid") if sign == 1 else _("Paid to Them"), money(doc, settled, currency)),
			(_("Balance Due") if sign == 1 else _("We Owe"), money(doc, balance, currency)),
		),
		"columns": (_("Date"), _("Document"), _("Number"), _("Debit") if sign == 1 else _("Credit"), _("Credit") if sign == 1 else _("Debit"), _("Balance")),
		"rows": rows,
		"opening_label": _("Opening Balance"),
		"opening": number(doc, opening, currency),
		"ages_heading": _("How Old"),
		"ages": [(str(label), money(doc, amount, currency)) for (_upto, label), amount in zip(AGES, aged, strict=True)],
		"invoices_heading": _("Open Invoices"),
		"invoice_columns": (_("Invoice"), _("Date"), _("Due"), _("Total"), _("Outstanding"), _("Days Late")),
		"invoices": invoices,
		"currency": currency,
		"bank_heading": _("Pay To"),
		"bank": _bank(company) if sign == 1 and balance > 0 else [],
	}


def _bank(company: str | None) -> list:
	found = frappe.db.get_value(
		"Bank Account", {"company": company, "is_company_account": 1, "disabled": 0},
		["bank", "account_name", "iban", "bank_account_no"], order_by="is_default desc, creation asc", as_dict=True,
	)
	if not found:
		return []
	return [(label, value) for label, value in (
		(_("Bank"), found.bank), (_("Account"), found.account_name), (_("IBAN"), found.iban), (_("Account No"), found.bank_account_no),
	) if value]


def _letter_date(doc) -> str:
	from frappe.utils import today

	return _("Date: {0}").format(_day(today()))


def _employed(doc) -> str:
	return _day(doc.date_of_joining)


def salary_certificate(doc) -> dict:
	"""A salary certificate, as a bank or an embassy asks for one: who, since
	when and as what, and the monthly pay as the latest payslip made it up."""
	if doc.doctype != "Employee":
		return {}
	company = _company(doc)
	slip = frappe.get_all(
		"Salary Slip", filters={"employee": doc.name, "docstatus": 1}, fields=["name", "gross_pay", "currency"],
		order_by="end_date desc", limit=1,
	)
	lines, gross, currency = [], 0.0, _currency(company)
	if slip:
		currency = slip[0].currency or currency
		gross = flt(slip[0].gross_pay)
		for one in frappe.get_all(
			"Salary Detail",
			filters={"parent": slip[0].name, "parentfield": "earnings", "statistical_component": 0, "do_not_include_in_total": 0},
			fields=["salary_component", "amount"],
			order_by="idx",
		):
			if flt(one.amount):
				lines.append((_(one.salary_component), money(doc, one.amount, currency)))
	else:
		base = frappe.db.get_value("Salary Structure Assignment", {"employee": doc.name, "docstatus": 1}, ["base", "currency"],
			order_by="from_date desc", as_dict=True)
		if base and flt(base.base):
			currency = base.currency or currency
			gross = flt(base.base)
			lines.append((_("Basic Salary"), money(doc, gross, currency)))
	passport = _(", holding passport number {0},").format(doc.passport_number) if doc.get("passport_number") else ""
	return {
		"date": _letter_date(doc),
		"greeting": _("To Whom It May Concern"),
		"opening": _("This is to certify that {0}{1} has been employed with {2} as {3} since {4}.").format(
			doc.employee_name, passport, company, _(doc.designation or "") or _("an employee"), _employed(doc)),
		"pay_heading": _("Monthly Salary"),
		"lines": lines,
		"total_label": _("Total"),
		"total": money(doc, gross, currency) if gross else "",
		"closing": _("This certificate is issued at the employee's request, without any liability on the part of the company."),
	}


def experience_letter(doc) -> dict:
	"""An experience letter: who worked here, from when to when, as what and
	where, or that they still do."""
	if doc.doctype != "Employee":
		return {}
	company = _company(doc)
	role = _(doc.designation or "") or _("an employee")
	where = _(" in the {0} department").format(doc.department.rsplit(" - ", 1)[0]) if doc.get("department") else ""
	if doc.get("relieving_date"):
		said = _("This is to certify that {0} worked with {1} from {2} to {3} as {4}{5}.").format(
			doc.employee_name, company, _employed(doc), _day(doc.relieving_date), role, where)
		wish = _("We thank {0} for their work and wish them every success.").format(doc.employee_name)
	else:
		said = _("This is to certify that {0} has worked with {1} since {2} and is currently employed as {3}{4}.").format(
			doc.employee_name, company, _employed(doc), role, where)
		wish = ""
	return {
		"date": _letter_date(doc),
		"greeting": _("To Whom It May Concern"),
		"opening": said,
		"wish": wish,
		"closing": _("This letter is issued at the employee's request."),
	}


def leave_balance(doc) -> dict:
	"""What the employee has of each leave on the first day asked for, as
	HRMS counts it."""
	if doc.doctype != "Leave Application" or not doc.get("employee") or not doc.get("from_date"):
		return {}
	from hrms.hr.doctype.leave_application.leave_application import get_leave_details

	found = (get_leave_details(doc.employee, doc.from_date) or {}).get("leave_allocation") or {}
	rows = [
		(_(kind), f"{flt(one.get('total_leaves')):g}", f"{flt(one.get('leaves_taken')):g}",
			f"{flt(one.get('leaves_pending_approval')):g}", f"{flt(one.get('remaining_leaves')):g}")
		for kind, one in found.items()
	]
	if not rows:
		return {}
	return {
		"heading": _("Leave Balance"),
		"columns": (_("Leave Type"), _("Allocated"), _("Taken"), _("Waiting"), _("Left")),
		"rows": rows,
	}


SUMS = {"Payment Order": ("references", "amount")}


def total(doc) -> dict:
	"""A table's total, for a record that keeps none."""
	if doc.doctype not in SUMS:
		return {}
	table, fieldname = SUMS[doc.doctype]
	currency = _currency(_company(doc))
	return {"label": _("Total"), "value": money(doc, sum(flt(one.get(fieldname)) for one in doc.get(table) or []), currency)}
