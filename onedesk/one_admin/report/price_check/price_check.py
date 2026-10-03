"""Whether the price list makes sense: every offering, what it costs us,
its margin, how much each plan saves over the one below it bought as
add-ons, and what does not hold. The rules are plans.check's; their words
are offerings.RULES, so the report reads in the operator's language.

What it gives is the offering's own `gives`, the line the Price List shows,
so the two cannot describe one thing two ways. The costs are One Admin
Settings', and the summary says the margin they ask for."""

from itertools import pairwise

import frappe
from frappe import _
from frappe.utils import cint

from onedesk.one_admin import offerings, plans, site


def execute(filters=None):
	site.require_admin()
	filters = frappe._dict(filters or {})
	ladder, sold, costs = offerings.listed(including_off=bool(cint(filters.get("include_disabled"))))
	currency = offerings.currency()
	ladder = sorted(ladder, key=lambda one: one.price)
	found = plans.check(ladder, sold, costs)
	said = {}
	for one in found:
		said.setdefault(one.offer, []).append(one)
	below = {upper.key: lower for lower, upper in pairwise(ladder)}
	keys = [one.key for one in [*ladder, *sold]]
	gives = dict(
		frappe.get_all(
			"Offering", filters={"name": ["in", keys or [""]]}, fields=["name", "gives"], as_list=True
		)
	)

	rows = []
	order = {"Add-on": 0, "Credit Pack": 1}
	for offer in [
		*ladder,
		*sorted(sold, key=lambda one: (order.get(one.kind, 2), one.resource or "", one.price)),
	]:
		ours = plans.cost(offer, costs)
		lower = below.get(offer.key)
		saving = plans.upgrade_saving(lower, offer, sold) if lower else None
		mine = said.get(offer.key, [])
		worst = "red" if any(one.level == "red" for one in mine) else "orange" if mine else "green"
		rows.append(
			{
				"currency": currency,
				"offering": offer.key,
				"says": " ".join(offerings.said(one) for one in mine) or _("OK"),
				"kind": _(offer.kind),
				"gives": gives.get(offer.key) or "",
				"price": offer.price,
				"costs_us": ours,
				"margin": f"{offer.price / ours:.1f}×" if ours else "",
				"saving": f"{round(100 * saving)}%" if saving is not None else "",
				"indicator": worst,
			}
		)
	# What is wrong first, then close calls, each in the list's own order.
	rank = {"red": 0, "orange": 1, "green": 2}
	rows.sort(key=lambda row: rank[row["indicator"]])

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
		{"label": _("Target Margin"), "value": f"{costs.margin:g}×", "datatype": "Data"},
	]
	return _columns(), rows, None, None, summary


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
		{"fieldname": "says", "label": _("Result"), "fieldtype": "Data", "width": 280},
		{"fieldname": "kind", "label": _("Type"), "fieldtype": "Data", "width": 105},
		{"fieldname": "gives", "label": _("Includes"), "fieldtype": "Data", "width": 185},
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
			"width": 90,
		},
		{"fieldname": "margin", "label": _("Margin"), "fieldtype": "Data", "width": 80},
		{"fieldname": "saving", "label": _("Saves"), "fieldtype": "Data", "width": 80},
	]
