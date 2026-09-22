"""The signup page, on the admin site and nowhere else.

A tenant workspace carries this file like every other, and answers 404 for it:
`one_admin.site.is_admin` decides, and a workspace offering its own customers a
signup form would be a confusing thing to stumble onto.

Nothing here decides a price. The offerings are read as they are, and the page
draws what it is given — so a plan withdrawn in One Admin is a plan that stops
being offered without anybody editing a template.

The quota line is built here rather than in the template because it is three
translated fragments joined by a separator, and a template that does that reads
worse than the Python does.
"""

import frappe

from onedesk.one_admin import site

no_cache = 1

#: What a jurisdiction is called on the page. The stored value is the short id,
#: because it goes in a field and into press's cluster choice; the label is what
#: somebody reads.
WHERE = {
	"Global": "Global",
	"EU": "European Union",
}


def get_context(context):
	if not site.is_admin():
		raise frappe.DoesNotExistError

	context.no_cache = 1
	context.offerings = [_drawn(one) for one in _plans()]
	context.jurisdictions = [(key, frappe._(label)) for key, label in WHERE.items()]
	context.pay_note = _pay_note(context.offerings)
	return context


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
	if one.get("seats"):
		said.append(frappe._("{0} people").format(one["seats"]))
	if one.get("credits_a_month"):
		said.append(frappe._("{0} AI credits a month").format(f"{one['credits_a_month']:,}"))
	return said
