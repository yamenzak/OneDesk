"""A deal's value, filled on the server as well as on the form, and its owner.

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
