"""What One shows on the portal, read by OnePortal's engine
(one_portal/portal.py) through the one_portal hook: a customer's addresses,
which they add and change there (frappe's own addresses web form). KINDS is
in the keys one_portal/AGENTS.md lists."""

from frappe import _, _lt


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
		"to": f"addresses/{doc.name}",
	}


KINDS = {
	"Address": {
		"icon": "map-pin",
		"columns": (_lt("Address"), _lt("Type"), _lt("City")),
		"add": ("addresses/new", _lt("Add Address")),
		"row": _address_row,
	},
}
