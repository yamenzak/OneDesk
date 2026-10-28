"""What OneBook shows on the portal, read by OnePortal's engine
(one_portal/portal.py) through the one_portal hook: a customer's invoices,
with what is left to pay and erpnext's own Pay, and a supplier's purchase
invoices. Each entry of KINDS is one kind of record, in the keys
one_portal/AGENTS.md lists."""

from frappe import _, _lt


def _paid(doc) -> bool:
	return (doc.get("outstanding_amount") or 0) <= 0


KINDS = {
	"Sales Invoice": {
		"transaction": True,
		"party": "customer",
		"icon": "receipt",
		"owed": True,
		"chain": ((("Sales Order", "sales_order"), ("Delivery Note", "delivery_note")), ()),
		"waiting": (("Unpaid", "Overdue", "Partly Paid"), lambda n: _("{0} to pay").format(n)),
		"asks": (lambda doc: (doc.get("outstanding_amount") or 0) > 0, _lt("View and Pay")),
		"steps": lambda doc: [(_("Issued"), True), (_("Paid"), _paid(doc))],
	},
	"Purchase Invoice": {
		"transaction": True,
		"party": "supplier",
		"icon": "receipt",
		"owed": True,
		"chain": ((("Purchase Order", "purchase_order"),), ()),
		"steps": lambda doc: [(_("Received"), True), (_("Paid"), _paid(doc))],
	},
}
