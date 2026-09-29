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
	"New": lambda: frappe._("This workspace has not been paid for yet."),
	"Paying": lambda: frappe._("This workspace has not been paid for yet."),
	"Paid": lambda: frappe._("Payment received. The workspace is being built."),
	"Provisioning": lambda: frappe._("Payment received. The workspace is being built."),
	"Done": lambda: frappe._("The workspace is ready. We have emailed you a link to choose your password."),
	"Abandoned": lambda: frappe._("This signup was closed without paying, and the name is free again."),
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

	from onedesk.one_admin import signup

	context.no_cache = 1
	# Only with the key the request was given: its name counts up, and would
	# otherwise open anybody's signup (signup.owned).
	asked = signup.owned(frappe.form_dict.get("request"), frappe.form_dict.get("key"))
	context.cancelled = bool(asked) and frappe.form_dict.get("outcome") == "cancelled"
	if context.cancelled:
		signup.let_go(asked)
		# A page is a GET, and frappe rolls a GET back: said here or not at all.
		frappe.db.commit()
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
	# Asked again every few seconds while it is being built, so "Open it"
	# appears without anybody reloading.
	context.watching = bool(asked) and asked.status in ("Paid", "Provisioning")
	context.can_pay = bool(asked) and asked.status in ("New", "Paying") and not asked.tenant
	return context
