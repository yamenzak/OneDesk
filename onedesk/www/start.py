"""The signup page, on the admin site and nowhere else.

A tenant workspace carries this file like every other, and answers 404 for it:
`one_admin.site.is_admin` decides, and a workspace offering its own customers a
signup form would be a confusing thing to stumble onto.

Nothing here decides a price. The offerings are read as they are, and the page
draws what it is given — so a plan withdrawn in One Admin is a plan that stops
being offered without anybody editing a template.
"""

import frappe

from onedesk.one_admin import site

no_cache = 1


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError

	context.no_cache = 1
	context.offerings = frappe.get_all(
		"Offering",
		filters={"kind": "Plan", "enabled": 1},
		fields=["name", "label", "description", "currency", "amount", "storage_gb", "seats", "credits_a_month"],
		order_by="amount asc",
	)
	context.jurisdictions = ("Global", "EU")
	return context
