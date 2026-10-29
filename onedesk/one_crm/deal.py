"""A deal's value, filled on the server as well as on the form, its owner, and
who to talk to there.

Runs after ERPNext's own validate, which sets the exchange rate and the items'
total.
"""

import frappe
from frappe.utils import flt


def validate(doc, method=None) -> None:
	if not flt(doc.opportunity_amount) and flt(doc.total):
		doc.opportunity_amount = doc.total
	doc.base_opportunity_amount = flt(doc.opportunity_amount) * (flt(doc.conversion_rate) or 1)
	if not doc.opportunity_owner:
		lead = doc.party_name if doc.opportunity_from == "Lead" else None
		doc.opportunity_owner = (lead and frappe.db.get_value("Lead", lead, "lead_owner")) or frappe.session.user
	_contact(doc)


def _contact(doc) -> None:
	"""The party's primary contact and address, as the form fills them when a
	party is picked: an opportunity made by OneAI, the demo or an import came
	with its Contacts tab empty."""
	if not doc.party_name or doc.contact_person or doc.contact_email:
		return
	if doc.opportunity_from == "Lead":
		lead = frappe.db.get_value("Lead", doc.party_name, ["lead_name", "email_id", "mobile_no"], as_dict=True)
		if lead:
			doc.contact_display = doc.contact_display or lead.lead_name
			doc.contact_email, doc.contact_mobile = lead.email_id, lead.mobile_no
		return
	from frappe.contacts.doctype.address.address import get_default_address
	from frappe.contacts.doctype.contact.contact import get_default_contact

	person = get_default_contact(doc.opportunity_from, doc.party_name)
	if person:
		said = frappe.db.get_value("Contact", person, ["full_name", "email_id", "mobile_no"], as_dict=True)
		doc.contact_person, doc.contact_display = person, said.full_name
		doc.contact_email, doc.contact_mobile = said.email_id, said.mobile_no
	doc.customer_address = doc.customer_address or get_default_address(doc.opportunity_from, doc.party_name)
