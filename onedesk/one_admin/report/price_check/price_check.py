"""Whether the price list makes sense: every offering, what it costs us,
its margin, how much each plan saves over the one below it bought as
add-ons, and what does not hold. The rules are plans.check's."""

from itertools import pairwise

import frappe
from frappe import _
from frappe.utils import fmt_money

from onedesk.one_admin import offerings, plans, site


def execute(filters=None):
	site.require_admin()
	ladder, sold, costs = offerings.listed()
	currency = offerings.currency()
	ladder = sorted(ladder, key=lambda one: one.price)
	found = plans.check(ladder, sold, costs)
	said = {}
	for one in found:
		said.setdefault(one.offer, []).append(one)
	below = {upper.key: lower for lower, upper in pairwise(ladder)}

	rows = []
	order = {"Add-on": 0, "Credit Pack": 1}
	for offer in [
		*ladder,
		*sorted(sold, key=lambda one: (order.get(one.kind, 2), one.resource or "", one.price)),
	]:
		ours = plans.cost(offer, costs)
		lower = below.get(offer.key)
		saving = plans.upgrade_saving(lower, offer, sold) if lower else None
		worst = (
			"red"
			if any(one.level == "red" for one in said.get(offer.key, []))
			else "orange"
			if said.get(offer.key)
			else None
		)
		rows.append(
			{
				"currency": currency,
				"offering": offer.key,
				"kind": offer.kind,
				"holds": _holds(offer),
				"price": offer.price,
				"costs_us": ours,
				"margin": round(offer.price / ours, 2) if ours else None,
				"saving": round(100 * saving) if saving is not None else None,
				"says": " ".join(one.said for one in said.get(offer.key, [])) or _("Makes sense."),
				"indicator": worst or "green",
			}
		)
	summary = [
		{"label": _("Offerings"), "value": len(rows), "datatype": "Int"},
		{
			"label": _("Wrong"),
			"value": len([one for one in found if one.level == "red"]),
			"datatype": "Int",
			"indicator": "Red" if any(one.level == "red" for one in found) else "Green",
		},
		{
			"label": _("Close Calls"),
			"value": len([one for one in found if one.level == "orange"]),
			"datatype": "Int",
			"indicator": "Orange" if any(one.level == "orange" for one in found) else "Green",
		},
	]
	return _columns(), rows, None, None, summary


def _holds(offer) -> str:
	if offer.kind == "Credit Pack":
		return _("{0} credits, once").format(fmt_money(offer.credits, precision=0))
	parts = []
	for resource, label in (
		("seats", _("{0} seats")),
		("storage_gb", _("{0} GB storage")),
		("database_gb", _("{0} GB database")),
		("credits_a_month", _("{0} credits a month")),
	):
		held = offer.quota(resource)
		if held == plans.INF:
			parts.append(label.format(_("unlimited")))
		elif held:
			parts.append(label.format(fmt_money(held, precision=0)))
	return ", ".join(parts)


def _columns() -> list[dict]:
	return [
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
		{
			"fieldname": "offering",
			"label": _("Offering"),
			"fieldtype": "Link",
			"options": "Offering",
			"width": 140,
		},
		{"fieldname": "kind", "label": _("Kind"), "fieldtype": "Data", "width": 100},
		{"fieldname": "holds", "label": _("Holds"), "fieldtype": "Data", "width": 300},
		{
			"fieldname": "price",
			"label": _("Price"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 90,
		},
		{
			"fieldname": "costs_us",
			"label": _("Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 100,
		},
		{"fieldname": "margin", "label": _("Times Cost"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "saving", "label": _("Saves Over Add-ons (%)"), "fieldtype": "Int", "width": 170},
		{"fieldname": "says", "label": _("Says"), "fieldtype": "Data", "width": 420},
	]
