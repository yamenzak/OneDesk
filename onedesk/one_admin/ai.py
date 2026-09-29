"""What OneAI does in OneAdmin: says what needs the operator, and why.

The operator's own reader, on the admin site only and for One Operator only,
as every console read is (`operator._may`). It is Home's own list
(`home.needs`), so the panel and the page say the same thing. Nothing is
changed from here: resuming a job, building a signup or checking a domain is
Home's button, which the operator presses.
"""

import frappe
from frappe import _lt

SUGGESTIONS = {
	"workspace:One Admin": [
		{
			"label": _lt("What needs me today?"),
			"ask": _lt(
				"What needs me in OneAdmin today? Say what is most urgent first, why each one is stuck, and what I should do about it."
			),
			"expects": "console_today",
		},
	],
	"Provisioning Job": [
		{
			"label": _lt("Why did this job fail?"),
			"ask": _lt(
				"Why did this job fail? Say where it stopped, what the error means in plain words, and whether resuming it is likely to work."
			),
			"can": "read",
			"view": "Form",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneAdmin's Home."""
	if said.get("workspace") != "One Admin":
		return None
	return (
		"The reader is an operator of One, on OneAdmin's Home: how many workspaces are live, being built, "
		"owing, failed, or paid for and not built, and a list of what needs them. console_today reads that "
		"list with each item's reason. Nothing is changed from the panel: Resume, Build It and Check Again "
		"are buttons on Home. How the console works is in OneAdmin's documentation (how_to)."
	)


def console_today() -> dict:
	"""For an operator of One only: what needs them in OneAdmin, as Home lists
	it. Jobs that failed with their step and error, workspaces paid for and not
	built, workspaces owing and since when, and domains not working or waiting
	for their DNS; and how many workspaces are live and being built."""
	from onedesk.one_admin import home, site

	if not site.is_admin() or site.OPERATOR not in frappe.get_roles():
		return {"error": "Only an operator of One, on the admin site, sees the console."}
	return {
		"counts": {one["key"]: one["value"] for one in home.counts()},
		"needs": [
			{key: one.get(key) for key in ("kind", "doctype", "name", "title", "why", "detail", "since")}
			for one in home.needs()
		],
	}
