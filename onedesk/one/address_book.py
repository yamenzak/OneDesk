"""The Address Book: the workspace's contacts and addresses as one screen,
a person's places and a place's people found through the records both
belong to. The page is the island `onedesk.address_book` on the page
`address-book`; how it works is in One's AGENTS.md, under address_book.py."""

import frappe
from frappe import _

PAGE = 50

KINDS = {"contacts": "Contact", "addresses": "Address"}


def _links(doctype: str, names: list[str]) -> dict[str, list[dict]]:
	"""Who each contact or address belongs to: the records its Links table
	names, with their titles."""
	found = {}
	for one in frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": doctype, "parent": ["in", names]},
		fields=["parent", "link_doctype", "link_name", "link_title"],
		order_by="idx asc",
	):
		found.setdefault(one.parent, []).append(
			{"doctype": one.link_doctype, "name": one.link_name, "title": one.link_title or one.link_name}
		)
	return found


@frappe.whitelist(methods=["GET"])
@frappe.read_only()
def read(view: str = "contacts", search: str | None = None, start: int = 0) -> dict:
	"""A page of contacts or of addresses the reader may read, by name."""
	doctype = KINDS.get(view) or frappe.throw(_("That cannot be shown."))
	words = f"%{search.strip()}%" if search and search.strip() else None
	if doctype == "Contact":
		fields = ["name", "full_name", "email_id", "mobile_no", "phone", "company_name", "image"]
		searched = ("full_name", "email_id", "mobile_no", "phone", "company_name")
		order = "full_name asc"
	else:
		fields = ["name", "address_title", "address_type", "address_line1", "city", "country"]
		searched = ("address_title", "address_line1", "city", "country")
		order = "address_title asc"
	rows = frappe.get_list(
		doctype,
		fields=fields,
		or_filters={field: ["like", words] for field in searched} if words else None,
		order_by=order,
		start=int(start or 0),
		limit=PAGE + 1,
	)
	links = _links(doctype, [one.name for one in rows[:PAGE]])
	said = []
	for one in rows[:PAGE]:
		if doctype == "Contact":
			row = {
				"name": one.name,
				"title": one.full_name or one.email_id or one.name,
				"sub": one.email_id or one.mobile_no or one.phone or "",
				"image": one.image,
			}
		else:
			row = {
				"name": one.name,
				"title": one.address_title or one.address_line1 or one.name,
				"sub": ", ".join(filter(None, (one.address_line1, one.city, one.country))),
				"kind": _(one.address_type) if one.address_type else "",
			}
		row["links"] = links.get(one.name, [])
		said.append(row)
	return {
		"rows": said,
		"more": len(rows) > PAGE,
		"makes": frappe.has_permission(doctype, "create"),
	}


def _alongside(doctype: str, links: list[dict]) -> list[str]:
	"""The other kind (addresses for a contact, contacts for an address) linked
	to any of the same records, that the reader may read."""
	if not links:
		return []
	other = "Address" if doctype == "Contact" else "Contact"
	pairs = {(link["doctype"], link["name"]) for link in links}
	names = {
		one.parent
		for one in frappe.get_all(
			"Dynamic Link",
			filters={
				"parenttype": other,
				"link_doctype": ["in", list({pair[0] for pair in pairs})],
				"link_name": ["in", list({pair[1] for pair in pairs})],
			},
			fields=["parent", "link_doctype", "link_name"],
		)
		if (one.link_doctype, one.link_name) in pairs
	}
	return frappe.get_list(other, filters={"name": ["in", list(names)]}, pluck="name") if names else []


@frappe.whitelist(methods=["GET"])
@frappe.read_only()
def one(view: str, name: str) -> dict:
	"""One contact or address in full, and the other kind beside it."""
	from frappe.contacts.doctype.address.address import get_address_display

	doctype = KINDS.get(view) or frappe.throw(_("That cannot be shown."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("read")
	links = [
		{"doctype": link.link_doctype, "name": link.link_name, "title": link.link_title or link.link_name}
		for link in doc.links
	]
	alongside = _alongside(doctype, links)
	said = {"name": doc.name, "links": links, "writes": doc.has_permission("write")}
	if doctype == "Contact":
		said |= {
			"title": doc.full_name or doc.email_id or doc.name,
			"role": " · ".join(filter(None, (doc.designation, doc.department, doc.company_name))),
			"image": doc.image,
			"emails": [{"email": one.email_id, "primary": one.is_primary} for one in doc.email_ids],
			"phones": [
				{"phone": one.phone, "mobile": one.is_primary_mobile_no, "primary": one.is_primary_phone}
				for one in doc.phone_nos
			],
			"places": [
				{"name": one, "text": get_address_display(frappe.get_doc("Address", one).as_dict())}
				for one in alongside
			],
		}
	else:
		said |= {
			"title": doc.address_title or doc.address_line1 or doc.name,
			"kind": _(doc.address_type) if doc.address_type else "",
			"text": get_address_display(doc.as_dict()),
			"email": doc.email_id,
			"phone": doc.phone,
			"people": [
				{
					"name": one.name,
					"title": one.full_name or one.email_id or one.name,
					"sub": one.email_id or one.mobile_no or one.phone or "",
				}
				for one in frappe.get_all(
					"Contact",
					filters={"name": ["in", alongside or [""]]},
					fields=["name", "full_name", "email_id", "mobile_no", "phone"],
				)
			],
		}
	return said
