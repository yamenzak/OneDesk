"""Clients become Customers and suppliers Suppliers, the supplier's kind its
group. A consultant is not a party Rua trades with: it is a Project Contact
on the projects it appears on (projects.py). A party no record ever named
is left behind."""

import frappe

from rua.importer.base import clean, parsed

PARTY = "RUA Party"
GROUPS = {
	"Supplier: Aluminum": "Aluminium",
	"Supplier: Glass": "Glass",
	"Supplier: Cladding": "Cladding",
}
TRADED = ("RUA Invoice", "RUA Payment", "RUA LPO", "RUA RFQ", "RUA Quotation", "RUA Purchase Receipt")


def run(run_):
	named = referenced(run_)
	customer_group = frappe.db.get_single_value("Selling Settings", "customer_group") or _leaf(
		"Customer Group"
	)
	territory = (
		"United Arab Emirates"
		if frappe.db.exists("Territory", "United Arab Emirates")
		else frappe.db.get_single_value("Selling Settings", "territory") or _leaf("Territory")
	)
	for party in run_.docs(PARTY):
		kind = party.get("type") or ""
		if kind == "Consultant":
			continue
		if party["name"] not in named:
			run_.note("Left Out", None, None, f"{party['name']}: a {kind or 'party'} no record names")
			continue
		if kind == "Client":
			made = run_.made(PARTY, party["name"], "Customer")
			if not made:
				doc = frappe.get_doc(
					{
						"doctype": "Customer",
						"customer_name": clean(party.get("party") or party["name"]),
						"customer_type": "Company",
						"customer_group": customer_group,
						"territory": territory,
						"tax_id": trn(party.get("trn")),
					}
				)
				doc.insert(ignore_permissions=True)
				run_.remember(PARTY, party["name"], "Customer", doc.name)
				contact(run_, party, "Customer", doc.name)
		elif kind.startswith("Supplier"):
			made = run_.made(PARTY, party["name"], "Supplier")
			if not made:
				doc = frappe.get_doc(
					{
						"doctype": "Supplier",
						"supplier_name": clean(party.get("party") or party["name"]),
						"supplier_type": "Company",
						"supplier_group": GROUPS.get(kind) or _leaf("Supplier Group"),
						"tax_id": trn(party.get("trn")),
					}
				)
				doc.insert(ignore_permissions=True)
				run_.remember(PARTY, party["name"], "Supplier", doc.name)
				contact(run_, party, "Supplier", doc.name)


def referenced(run_) -> set:
	"""The parties some record names: on a sale, a purchase or a payment, or
	among a project's parties."""
	named = set()
	for doctype in TRADED:
		named |= {row.get("party") for row in run_.docs(doctype) if row.get("party")}
	for project in run_.docs("RUA Project"):
		named |= {one.get("name") for one in parsed(project.get("parties"), []) if one.get("name")}
	return named


def trn(value):
	"""A UAE TRN is fifteen digits; the old app kept 0 and blanks too."""
	digits = "".join(ch for ch in str(value or "") if ch.isdigit())
	return digits if len(digits) == 15 else None


def contact(run_, party, doctype, name):
	phone, email = clean(party.get("phone")), clean(party.get("email")).lower()
	if not phone and not email:
		return
	doc = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": clean(party.get("party") or party["name"])[:140],
			"is_primary_contact": 1,
			"links": [{"link_doctype": doctype, "link_name": name}],
		}
	)
	if email and frappe.utils.validate_email_address(email):
		doc.append("email_ids", {"email_id": email, "is_primary": 1})
	if phone:
		doc.append("phone_nos", {"phone": phone, "is_primary_phone": 1})
	doc.insert(ignore_permissions=True)


def _leaf(doctype):
	return frappe.get_all(doctype, filters={"is_group": 0}, pluck="name", limit=1)[0]


def customer_of(run_, party_name):
	return run_.made(PARTY, party_name, "Customer") if party_name else None


def supplier_of(run_, party_name):
	return run_.made(PARTY, party_name, "Supplier") if party_name else None
