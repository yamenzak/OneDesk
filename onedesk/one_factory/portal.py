"""What a supplier sees of the work sent to them on the portal: their
subcontracting orders, what each makes, and whether it is back, which
OnePortal's engine (one_portal/portal.py) reads through the one_portal hook
(KINDS, in the keys one_portal/AGENTS.md lists). ERPNext gives the
subcontracting order no portal of its own, so its reading and its
permission are here."""

import frappe
from frappe import _lt

KIND = "Subcontracting Order"


def has_website_permission(doc, ptype: str = "read", user: str | None = None, verbose: bool = False) -> bool:
	"""A supplier's portal users read the orders sent to that supplier, as
	ERPNext lets them read its purchase orders, and none hidden from them."""
	from erpnext.controllers.website_list_for_contact import has_website_permission as theirs

	from onedesk.one_portal import portal

	user = user or frappe.session.user
	return bool(theirs(doc, ptype, user, verbose)) and portal.mine(KIND, doc, user)


def found(txt: str | None = None, limit: int = 0) -> list:
	"""The reader's suppliers' submitted orders, newest first."""
	from erpnext.controllers.website_list_for_contact import get_customers_suppliers

	from onedesk.one_portal import portal

	_customers, suppliers = get_customers_suppliers(KIND, frappe.session.user)
	if not suppliers:
		return []
	filters = {"supplier": ["in", suppliers], "docstatus": 1}
	if txt:
		filters["name"] = ["like", f"%{txt}%"]
	names = frappe.get_all(KIND, filters=filters, pluck="name", order_by="transaction_date desc, creation desc", limit=limit or 0)
	return [doc for doc in (frappe.get_doc(KIND, one) for one in names) if portal.mine(KIND, doc)]


KINDS = {
	KIND: {
		"transaction": True,
		"party": "supplier",
		"icon": "send",
		"called": _lt("Work Sent to You"),
		"found": found,
		"said": {
			"Open": ("amber", _lt("Materials to come")),
			"Partial Material Transferred": ("amber", _lt("Some materials sent")),
			"Material Transferred": ("amber", _lt("To make")),
			"Partially Received": ("amber", _lt("Part returned")),
			"Completed": ("green", _lt("Returned")),
			"Closed": ("gray", _lt("Closed")),
		},
		"chain": ((("Purchase Order", "purchase_order"),), ()),
	},
}
