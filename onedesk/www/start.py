"""The signup page, on the admin site and nowhere else.
"""

import frappe

from onedesk.one_admin import site

no_cache = 1

WHERE = {
	"Global": "Global",
	"EU": "European Union",
}


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError

	context.no_cache = 1
	context.offerings = [_drawn(one) for one in _plans()]
	context.jurisdictions = _jurisdictions()
	context.pay_note = _pay_note(context.offerings)
	context.prefill_name = (frappe.form_dict.get("name") or "")[:140]
	offered = [one["name"] for one in context.offerings]
	context.chosen = frappe.form_dict.get("plan") if frappe.form_dict.get("plan") in offered else (offered[0] if offered else None)
	context.me = (
		frappe.db.get_value("User", frappe.session.user, "email") if frappe.session.user != "Guest" else None
	)
	context.tenant_domain = (
		frappe.db.get_single_value("One Admin Settings", "tenant_domain") or "t.4dl.app"
	)
	return context


def _jurisdictions() -> list[tuple[str, str]]:
	"""Where a workspace may be put, and only where there is somewhere to put it.

	The EU choice moves the workspace's files to the EU bucket (storage._bucket)
	and nothing else yet: there is one cluster. So it is offered only once that
	bucket is set, since without it the first upload fails, and its note says
	files rather than the workspace.
	"""
	eu = frappe.db.get_single_value("One Admin Settings", "bucket_eu")
	return [
		(key, frappe._(label)) for key, label in WHERE.items() if key != "EU" or eu
	]


def _pay_note(offerings: list[dict]) -> str:
	"""The line under the button, which has to be true of whatever is picked.

	Two sentences rather than one when any plan has a trial, because "nothing is
	charged until it is confirmed" is the wrong reassurance there: the card is
	taken at checkout and the charge comes days later.
	"""
	if any(one.get("trial_days") for one in offerings):
		return frappe._(
			"Payment is taken by Stripe. A plan with a trial takes your card now "
			"and charges it when the trial ends."
		)
	return frappe._("Payment is taken by Stripe. Nothing is charged until it is confirmed there.")


def _plans() -> list[dict]:
	return frappe.get_all(
		"Offering",
		filters={"kind": "Plan", "enabled": 1},
		fields=[
			"name",
			"label",
			"description",
			"currency",
			"amount",
			"trial_days",
			"storage_gb",
			"database_gb",
			"seats",
			"credits_a_month",
		],
		order_by="amount asc",
	)


def _drawn(one: dict) -> dict:
	"""A plan with the lines the page shows written out.

	The trial is its own line rather than part of the price, because the price
	is right-aligned against the plan's name and "Free for 14 days, then $49.00
	a month" does not belong in that column.
	"""
	one["price"] = frappe._("{0} a month").format(
		frappe.utils.fmt_money(one["amount"], currency=one["currency"])
	)
	one["trial"] = (
		frappe._("Free for {0} days").format(one["trial_days"]) if one.get("trial_days") else None
	)
	one["quota"] = " · ".join(_quota(one))
	return one


def _quota(one: dict) -> list[str]:
	"""What the plan buys, in the order somebody compares plans in.

	A zero is unlimited, and saying "unlimited storage" on a signup page is a
	promise, so it is left out instead.
	"""
	said = []
	if one.get("storage_gb"):
		said.append(frappe._("{0} GB storage").format(one["storage_gb"]))
	if one.get("database_gb"):
		said.append(frappe._("{0} GB database").format(one["database_gb"]))
	if one.get("seats"):
		said.append(frappe._("{0} people").format(one["seats"]))
	if one.get("credits_a_month"):
		said.append(frappe._("{0} credits a month").format(f"{one['credits_a_month']:,}"))
	return said
