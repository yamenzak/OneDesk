"""A deal's value, filled on the server as well as on the form.

ERPNext works out `base_opportunity_amount` only in the form's script, so a
deal made by import, the API or OneAI is worth nothing in the company's
currency, and every total that reads it. And a deal priced by its items keeps
Opportunity Amount empty beside a filled Total. Runs after ERPNext's own
validate, which sets the exchange rate and the items' total.
"""

from frappe.utils import flt


def validate(doc, method=None) -> None:
	if not flt(doc.opportunity_amount) and flt(doc.total):
		doc.opportunity_amount = doc.total
	doc.base_opportunity_amount = flt(doc.opportunity_amount) * (flt(doc.conversion_rate) or 1)
