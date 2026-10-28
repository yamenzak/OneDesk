"""What One shows on the portal, read by OnePortal's engine
(one_portal/portal.py) through the one_portal hook: a customer's addresses,
which they add and change there (frappe's own addresses web form), beside
the ones the workspace keeps for them. KINDS is
in the keys one_portal/AGENTS.md lists."""

import frappe
from frappe import _, _lt

FIELDS = ("name", "owner", "address_title", "address_type", "address_line1", "address_line2", "city", "state", "country")


def _addresses(txt: str | None, limit: int) -> list:
	"""The reader's addresses: those they added, and those the workspace keeps
	for their customer or supplier, which frappe's own portal list leaves out."""
	user = frappe.session.user
	parties = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "parent": ("in", frappe.get_all("Contact", filters={"user": user}, pluck="name") or [""]), "link_doctype": ("in", ("Customer", "Supplier"))},
		fields=["link_doctype", "link_name"],
	)
	linked = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Address", "link_doctype": ("in", ("Customer", "Supplier")), "link_name": ("in", [one.link_name for one in parties] or [""])},
		pluck="parent",
	)
	filters = {"disabled": 0}
	if txt:
		filters["address_line1"] = ("like", f"%{txt}%")
	return frappe.get_all(
		"Address",
		filters=filters,
		or_filters={"owner": user, "name": ("in", linked or [""])},
		fields=list(FIELDS),
		order_by="modified desc",
		limit=limit or None,
	)


def _address_row(doc) -> dict:
	"""An address in the Addresses tab: its lines, its type and its city."""
	where = ", ".join(one for one in (doc.address_line1, doc.address_line2, doc.state, doc.country) if one)
	return {
		"name": doc.name,
		"title": doc.get("address_title") or doc.name,
		"line": where,
		"tone": "gray",
		"status": _(doc.address_type) if doc.get("address_type") else "",
		"figure": doc.get("city") or "",
		# Only an address they added is theirs to change; the workspace keeps the rest.
		"to": f"addresses/{doc.name}" if doc.get("owner") == frappe.session.user else None,
	}


KINDS = {
	"Address": {
		"icon": "map-pin",
		"columns": (_lt("Address"), _lt("Type"), _lt("City")),
		"add": ("addresses/new", _lt("Add Address")),
		"row": _address_row,
		"found": _addresses,
	},
}
