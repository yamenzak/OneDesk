"""What a workspace needing this much would pay, every way it could: each
plan with the add-ons that bring it up to the need, cheapest first, and
what each way costs us. The same answer a workspace gets when it adds to its
plan (billing.quote), so it counts add-ons and not credit packs, which are
bought once rather than monthly.

With a workspace, the needs start from what it has now (`needs_of`) and the
row of the plan it is on says so."""

from math import ceil

import frappe
from frappe import _, _lt
from frappe.utils import cint, flt, fmt_money

from onedesk.one_admin import billing, offerings, plans, site

GB = 1024**3

#: What a plan no add-on can top up is short of. Credits have no monthly
#: add-on, only packs bought once, so a plan short of them stays short.
SHORT = {
	"seats": _lt("seats"),
	"storage_gb": _lt("storage"),
	"database_gb": _lt("database"),
	"credits_a_month": _lt("credits"),
}


def execute(filters=None):
	site.require_admin()
	filters = frappe._dict(filters or {})
	needs = {one: flt(filters.get(one)) for one in plans.RESOURCES}
	options, currency = quote(needs)
	held = frappe.get_doc("Tenant", filters.workspace) if filters.get("workspace") else None
	gives = dict(frappe.get_all("Offering", filters={"kind": "Plan"}, fields=["name", "gives"], as_list=True))
	rows = []
	for at, option in enumerate(options):
		ours = option["costs_us"]
		rows.append(
			{
				"currency": currency,
				"plan": option["plan"].key,
				"gives": gives.get(option["plan"].key) or "",
				"extras": ", ".join(f"{count} × {one.label}" for one, count in option["extras"])
				or _("Nothing"),
				"monthly": option["monthly"],
				"costs_us": ours,
				"margin": f"{option['monthly'] / ours:.1f}×" if ours else "",
				"dearer_by": _("Short of {0}").format(", ".join(str(SHORT[one]) for one in option["unmet"]))
				if option["unmet"]
				else _("Cheapest")
				if at == 0
				else fmt_money(option["monthly"] - options[0]["monthly"], currency=currency),
				# Not columns: what the formatter colours Dearer By by.
				"cheapest": at == 0 and not option["unmet"],
				"short": bool(option["unmet"]),
				"theirs": _("Their plan") if held and option["plan"].key == held.offering else "",
			}
		)
	return _columns(bool(held)), rows, None, None, _summary(needs, options, currency, held)


def quote(needs: dict) -> tuple[list[dict], str]:
	"""Every plan with what brings it up to `needs`, cheapest first, and what
	each way costs us."""
	ladder, sold, costs = offerings.listed()
	said = []
	for option in plans.quote(needs, ladder, [one for one in sold if one.kind == "Add-on"]):
		ours = plans.cost(option.plan, costs) + sum(
			plans.cost(one, costs) * count for one, count in option.extras
		)
		said.append(
			{
				"plan": option.plan,
				"extras": option.extras,
				"unmet": option.unmet,
				"monthly": option.monthly,
				"costs_us": round(ours, 2),
			}
		)
	return said, offerings.currency()


@frappe.whitelist()
def needs_of(workspace: str) -> dict:
	"""What a workspace has now, as the four needs: the seats it pays for,
	the storage and database it uses, and the credits it gets a month or
	spent this month, whichever is more."""
	site.require_admin()
	frappe.only_for(site.OPERATOR)
	from onedesk.one_admin import operator

	held = frappe.get_doc("Tenant", workspace)
	plan = (
		frappe.db.get_value("Offering", held.offering, ["seats", "credits_a_month"], as_dict=True)
		if held.offering
		else None
	)
	spent = flt(operator.credit_standing(held.name).get("month_credits"))
	return {
		"seats": cint(held.seats) or cint(plan and plan.seats),
		"storage_gb": ceil(flt(held.storage_bytes) / GB),
		"database_gb": ceil(flt(held.database_bytes) / GB),
		"credits_a_month": max(
			cint(held.credits_a_month) or cint(plan and plan.credits_a_month), ceil(spent)
		),
	}


def _summary(needs: dict, options: list[dict], currency: str, held) -> list[dict]:
	"""The needs said back with their words, since a filled filter shows only
	its number, and the cheapest answer."""
	said = [
		{"label": _("Seats"), "value": cint(needs["seats"]), "datatype": "Int"},
		{"label": _("Storage"), "value": _("{0} GB").format(f"{needs['storage_gb']:g}"), "datatype": "Data"},
		{
			"label": _("Database"),
			"value": _("{0} GB").format(f"{needs['database_gb']:g}"),
			"datatype": "Data",
		},
		{"label": _("Credits a Month"), "value": f"{cint(needs['credits_a_month']):,}", "datatype": "Data"},
	]
	reached = [one for one in options if not one["unmet"]]
	if reached:
		said.append(
			{
				"label": _("Cheapest"),
				"value": _("{0} at {1}").format(
					reached[0]["plan"].label, fmt_money(reached[0]["monthly"], currency=currency)
				),
				"datatype": "Data",
				"indicator": "Green",
			}
		)
	else:
		said.append(
			{"label": _("Cheapest"), "value": _("No plan reaches it"), "datatype": "Data", "indicator": "Red"}
		)
	if held:
		said.append(
			{
				"label": _("Pays Now"),
				"value": fmt_money(billing.monthly(held), currency=currency),
				"datatype": "Data",
			}
		)
	return said


def _columns(workspace: bool) -> list[dict]:
	columns = [
		{
			"fieldname": "currency",
			"label": _("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
		{"fieldname": "plan", "label": _("Plan"), "fieldtype": "Link", "options": "Offering", "width": 90},
		{"fieldname": "gives", "label": _("Gives"), "fieldtype": "Data", "width": 240},
		{"fieldname": "extras", "label": _("Add-ons"), "fieldtype": "Data", "width": 240},
		{
			"fieldname": "monthly",
			"label": _("A Month"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 95,
		},
		{
			"fieldname": "costs_us",
			"label": _("Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			"width": 90,
		},
		{"fieldname": "margin", "label": _("Margin"), "fieldtype": "Data", "width": 75},
		{"fieldname": "dearer_by", "label": _("Dearer By"), "fieldtype": "Data", "width": 125},
	]
	if workspace:
		columns.append({"fieldname": "theirs", "label": _("Now"), "fieldtype": "Data", "width": 105})
	return columns
