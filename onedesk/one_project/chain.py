"""Every document about a job names its project, once.

ERPNext lets most money documents name a project, on the document and on
each line, and carries it when one is made from another: an order's
delivery and invoice, a purchase order's receipt and bill, an invoice's
payment. Three couldn't name one at all (Quotation, Request for Quotation and
Material Request, which now can: custom/), and nothing kept a document's
lines and the document itself in agreement, so a project's figures missed
whatever somebody forgot to type.

`agree` does that as each is validated: a line with no project takes the
document's, and a document with no project takes its lines' when they all
name the same one. Since the field is called `project` on every one of them,
ERPNext's own mapping then carries it from document to document: a quotation
to its order, a material request to its purchase order, a request for
quotation to the supplier's quotation and on.

A payment made from an invoice or an order takes its project from it, as
ERPNext does. One made on its own and matched to invoices later, or paying
several at once, takes the project they all name (`paid_for`). A new
order, delivery or invoice for a customer with one open project names it
(`customer_project`, public/js/customer_project.js).
"""

import frappe

#: The documents kept in agreement, and what their lines call the project.
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


#: What a payment can be matched to that names a project.
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
