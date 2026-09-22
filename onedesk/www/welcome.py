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
	"New": lambda: frappe._("The payment has not arrived yet."),
	"Paying": lambda: frappe._("Waiting for the payment to settle."),
	"Paid": lambda: frappe._("Payment received. The workspace is being built."),
	"Provisioning": lambda: frappe._("Payment received. The workspace is being built."),
	"Done": lambda: frappe._("The workspace is ready."),
	"Failed": lambda: frappe._("The workspace could not be built. Somebody has been told and will be in touch."),
}

#: What the same two statuses say when the plan carried a trial. Nothing was
#: charged, so "Payment received" is simply false — the card was taken and the
#: first invoice is days away. Done is not here: "The workspace is ready" is
#: already the whole answer on the screen somebody opens to click Open it.
ON_TRIAL = {
	"Paid": lambda: frappe._("Your trial has started. The workspace is being built."),
	"Provisioning": lambda: frappe._("Your trial has started. The workspace is being built."),
}


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError

	context.no_cache = 1
	context.cancelled = frappe.form_dict.get("outcome") == "cancelled"
	asked = frappe.db.get_value(
		"Account Request",
		frappe.form_dict.get("request"),
		["workspace_name", "status", "tenant", "email", "offering"],
		as_dict=True,
	)
	context.asked = asked
	trial = (
		frappe.db.get_value("Offering", asked.offering, "trial_days")
		if asked and asked.offering
		else 0
	)
	says = None
	if asked:
		says = (ON_TRIAL.get(asked.status) if trial else None) or SAYS.get(asked.status)
	context.said = says() if says else None
	context.domain = (
		frappe.db.get_value("Tenant", asked.tenant, "domain") if asked and asked.tenant else None
	)
	return context
