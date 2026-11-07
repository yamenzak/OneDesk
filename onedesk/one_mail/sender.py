"""Who wrote, beside their mail: the customer, supplier, lead, employee or
applicant their address belongs to, and what of theirs is still open, as
the reader may see it. HubSpot's panel in Gmail does the same job."""

import frappe
from frappe import _
from frappe.utils import flt

FEW = 4

OPEN = {
	"Customer": (
		("Opportunity", {"opportunity_from": "Customer", "party_name": "{0}", "status": ["in", ["Open", "Replied", "Quotation"]]}, None),
		("Quotation", {"quotation_to": "Customer", "party_name": "{0}", "docstatus": 1, "status": ["in", ["Open", "Replied"]]}, "grand_total"),
		("Sales Order", {"customer": "{0}", "docstatus": 1, "status": ["in", ["To Deliver and Bill", "To Bill", "To Deliver"]]}, "grand_total"),
		("Sales Invoice", {"customer": "{0}", "docstatus": 1, "outstanding_amount": [">", 0]}, "outstanding_amount"),
		("Issue", {"customer": "{0}", "status": ["in", ["Open", "Replied", "On Hold"]]}, None),
		("Project", {"customer": "{0}", "status": "Open"}, None),
	),
	"Supplier": (
		("Supplier Quotation", {"supplier": "{0}", "docstatus": 1, "status": "Submitted"}, "grand_total"),
		("Purchase Order", {"supplier": "{0}", "docstatus": 1, "status": ["in", ["To Receive and Bill", "To Bill", "To Receive"]]}, "grand_total"),
		("Purchase Invoice", {"supplier": "{0}", "docstatus": 1, "outstanding_amount": [">", 0]}, "outstanding_amount"),
		("Subcontracting Order", {"supplier": "{0}", "docstatus": 1, "status": ["not in", ["Completed", "Closed", "Cancelled"]]}, None),
	),
	"Lead": (
		("Opportunity", {"opportunity_from": "Lead", "party_name": "{0}", "status": ["in", ["Open", "Replied", "Quotation"]]}, None),
		("Quotation", {"quotation_to": "Lead", "party_name": "{0}", "docstatus": 1, "status": ["in", ["Open", "Replied"]]}, "grand_total"),
	),
	"Employee": (
		("Leave Application", {"employee": "{0}", "status": "Open"}, None),
		("Expense Claim", {"employee": "{0}", "docstatus": ["<", 2], "status": ["in", ["Draft", "Unpaid"]]}, "grand_total"),
		("Employee Advance", {"employee": "{0}", "docstatus": 1, "status": ["in", ["Unpaid", "Paid"]]}, "advance_amount"),
	),
	"Job Applicant": (
		("Interview", {"job_applicant": "{0}", "status": ["in", ["Pending", "Under Review"]]}, None),
		("Job Offer", {"job_applicant": "{0}", "status": ["in", ["Awaiting Response", "Accepted"]]}, None),
	),
}

DATES = {"Quotation": "valid_till", "Sales Order": "delivery_date", "Sales Invoice": "due_date", "Purchase Order": "schedule_date", "Purchase Invoice": "due_date", "Opportunity": "expected_closing", "Interview": "scheduled_on", "Leave Application": "from_date", "Issue": "opening_date", "Project": "expected_end_date"}


def party(address: str) -> tuple[str, str] | None:
	"""The record an address belongs to: a contact's customer, supplier or
	lead, or a customer, supplier, lead, employee or applicant by its own
	address."""
	address = (address or "").strip().lower()
	if not address:
		return None
	from frappe.contacts.doctype.contact.contact import get_contact_name

	contact = get_contact_name(address)
	if contact:
		for link in frappe.get_cached_doc("Contact", contact).links:
			if link.link_doctype in OPEN and frappe.db.exists(link.link_doctype, link.link_name):
				return link.link_doctype, link.link_name
	for doctype, fields in (
		("Customer", ("email_id",)),
		("Supplier", ("email_id",)),
		("Lead", ("email_id",)),
		("Employee", ("company_email", "personal_email", "prefered_email", "user_id")),
		("Job Applicant", ("email_id",)),
	):
		for field in fields:
			if not frappe.get_meta(doctype).has_field(field):
				continue
			found = frappe.db.get_value(doctype, {field: address})
			if found:
				return doctype, found
	return None


@frappe.whitelist()
def about(address: str) -> dict | None:
	"""The panel: who it is and what of theirs is open, for the reader."""
	found = party(address)
	if not found:
		return None
	doctype, name = found
	if not frappe.has_permission(doctype, "read", doc=name):
		return None
	meta = frappe.get_meta(doctype)
	title_field = meta.title_field or "name"
	title, image = frappe.db.get_value(doctype, name, [title_field, meta.image_field or "name"]) if meta.image_field else (frappe.db.get_value(doctype, name, title_field), None)
	groups = []
	for kind, filters, amount in OPEN[doctype]:
		if not frappe.has_permission(kind, "read"):
			continue
		filled = {key: (value.format(name) if isinstance(value, str) else value) for key, value in filters.items()}
		fields = ["name", "status" if frappe.get_meta(kind).has_field("status") else "name as status"]
		if amount:
			fields += [f"{amount} as amount", "currency" if frappe.get_meta(kind).has_field("currency") else "'' as currency"]
		if DATES.get(kind) and frappe.get_meta(kind).has_field(DATES[kind]):
			fields.append(f"{DATES[kind]} as date")
		rows = frappe.get_list(kind, filters=filled, fields=fields, order_by="modified desc", limit_page_length=FEW + 1)
		if rows:
			groups.append(
				{
					"doctype": kind,
					"label": _(kind),
					"more": len(rows) > FEW,
					"rows": [{**one, "amount": flt(one.get("amount")) if amount else None} for one in rows[:FEW]],
				}
			)
	return {"doctype": doctype, "label": _(doctype), "name": name, "title": title or name, "image": image, "groups": groups}
