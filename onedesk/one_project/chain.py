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
"""

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
