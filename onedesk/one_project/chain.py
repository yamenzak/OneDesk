"""Every document about a job names its project, once."""

import frappe

LINES = {
	"Request for Quotation": "project_name",
	"Material Request": "project",
	"Supplier Quotation": "project",
	"Purchase Order": "project",
	"Purchase Receipt": "project",
	"Purchase Invoice": "project",
	"Sales Order": "project",
	"Delivery Note": "project",
	"Sales Invoice": "project",
}


def agree(doc, method=None) -> None:
	"""validate: the document and its lines name the same project."""
	field = LINES.get(doc.doctype)
	if not field:
		return
	rows = doc.get("items") or []
	if not doc.get("project"):
		named = {row.get(field) for row in rows if row.get(field)}
		if len(named) == 1:
			doc.project = named.pop()
	if doc.get("project"):
		for row in rows:
			if not row.get(field):
				row.set(field, doc.project)


NAMED = ("Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order")


def paid_for(doc, method=None) -> None:
	"""Payment Entry validate: a payment with no project takes the one its
	invoices and orders all name."""
	if doc.get("project"):
		return
	named = set()
	for row in doc.get("references") or []:
		if row.reference_doctype not in NAMED:
			return
		named.add(frappe.db.get_value(row.reference_doctype, row.reference_name, "project"))
	if len(named) == 1 and None not in named and "" not in named:
		doc.project = named.pop()


def customers_one(doc, method=None) -> None:
	"""before_insert: a new quotation, order, delivery or invoice with no
	project takes the customer's one open project, however it is made (the
	form, a mapper, a bulk edit, Data Import). A return keeps what it returns."""
	if doc.get("project") or doc.get("is_return"):
		return
	customer = doc.get("customer") or (doc.get("party_name") if doc.get("quotation_to") == "Customer" else None)
	project = customer_project(customer) if customer else None
	if project:
		doc.project = project


@frappe.whitelist()
@frappe.read_only()
def customer_project(customer: str) -> str | None:
	"""A new order's, delivery's or invoice's project: the customer's one open
	project, when there's exactly one. With more, the person picks."""
	if not customer or not frappe.has_permission("Customer", "read", doc=customer):
		return None
	found = frappe.get_list(
		"Project", filters={"customer": customer, "status": "Open"}, pluck="name", limit_page_length=2
	)
	return found[0] if len(found) == 1 else None
