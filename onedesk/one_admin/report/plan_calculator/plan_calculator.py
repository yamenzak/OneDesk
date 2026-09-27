"""What a workspace needing this much would pay, every way it could: each
plan with the add-ons that bring it up to the need, cheapest first, and
what each way costs us. The same answer a workspace gets when it adds to its
plan (plans.quote)."""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money

from onedesk.one_admin import offerings, plans, site


def execute(filters=None):
	site.require_admin()
	filters = frappe._dict(filters or {})
	needs = {one: flt(filters.get(one)) for one in plans.RESOURCES}
	ladder, sold, costs = offerings.listed()
	currency = offerings.currency()
	rows = []
	for at, option in enumerate(plans.quote(needs, ladder, sold)):
		ours = plans.cost(option.plan, costs) + sum(
			plans.cost(one, costs) * count for one, count in option.extras
		)
		rows.append(
			{
				"currency": currency,
				"plan": option.plan.key,
				"extras": ", ".join(f"{count} × {one.label}" for one, count in option.extras) or _("Nothing"),
				"monthly": option.monthly,
				"costs_us": round(ours, 2),
				"margin": round(option.monthly / ours, 2) if ours else None,
				"verdict": _("Cannot reach it")
				if option.unmet
				else _("Cheapest")
				if at == 0
				else _("{0} more").format(fmt_money(option.monthly - rows[0]["monthly"], currency=currency)),
			}
		)
	return _columns(), rows


def _columns() -> list[dict]:
	return [
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
		{"fieldname": "plan", "label": _("Plan"), "fieldtype": "Link", "options": "Offering", "width": 120},
		{"fieldname": "extras", "label": _("Add-ons"), "fieldtype": "Data", "width": 320},
		{
			"fieldname": "monthly",
			"label": _("A Month"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{
			"fieldname": "costs_us",
			"label": _("Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 110,
		},
		{"fieldname": "margin", "label": _("Times Cost"), "fieldtype": "Float", "precision": 1, "width": 100},
		{"fieldname": "verdict", "label": _("Against the Cheapest"), "fieldtype": "Data", "width": 170},
	]
