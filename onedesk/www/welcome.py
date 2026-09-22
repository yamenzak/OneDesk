"""Where Stripe sends somebody back to, whichever way it went.

The page tells the truth about what is known *now*, which for a fresh payment is
usually "we have your money and the workspace is being built". The webhook is
what actually provisions, and it may not have arrived yet — so this reads the
request rather than assuming, and says so either way.
"""

import frappe

from onedesk.one_admin import site

no_cache = 1

SAYS = {
	"New": lambda: frappe._("We have not had the payment yet."),
	"Paying": lambda: frappe._("We are waiting for the payment to settle."),
	"Paid": lambda: frappe._("Thank you. Your workspace is being built."),
	"Provisioning": lambda: frappe._("Thank you. Your workspace is being built."),
	"Done": lambda: frappe._("Your workspace is ready."),
	"Failed": lambda: frappe._("Something went wrong and somebody has been told."),
}


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError

	context.no_cache = 1
	context.cancelled = frappe.form_dict.get("outcome") == "cancelled"
	asked = frappe.db.get_value(
		"Account Request",
		frappe.form_dict.get("request"),
		["workspace_name", "status", "tenant", "email"],
		as_dict=True,
	)
	context.asked = asked
	says = SAYS.get(asked.status) if asked else None
	context.said = says() if says else None
	context.domain = (
		frappe.db.get_value("Tenant", asked.tenant, "domain") if asked and asked.tenant else None
	)
	return context
