"""OneCRM on the calendar: the next step on each of the reader's own open leads
and deals, at the time it is due. Clicking one opens the lead or deal, where
**Next Step Done** is."""

import frappe
from frappe import _lt

from onedesk.one_calendar import layers
from onedesk.one_crm import next as next_step

LAYERS = [
	{
		"key": "deal-steps",
		"label": _lt("Deal Next Steps"),
		"color": "green",
		"group": "Mine",
		"doctype": "Opportunity",
		"rows": "onedesk.one_crm.calendar.deals",
	},
	{
		"key": "lead-steps",
		"label": _lt("Lead Next Steps"),
		"color": "yellow",
		"group": "Mine",
		"doctype": "Lead",
		"rows": "onedesk.one_crm.calendar.leads",
	},
]


def deals(start, end) -> list[dict]:
	return _steps("Opportunity", start, end)


def leads(start, end) -> list[dict]:
	return _steps("Lead", start, end)


def _steps(doctype: str, start, end) -> list[dict]:
	return [
		{
			"name": one.name,
			"title": f"{one.one_next_step or frappe._('Next Step')} · {one.title or one.name}",
			"start": one.one_next_on,
		}
		for one in frappe.get_list(
			doctype,
			filters=[
				[next_step.OWNER[doctype], "=", frappe.session.user],
				["status", "in", next_step.OPEN[doctype]],
				*layers.within("one_next_on", start, end),
			],
			fields=["name", "title", "one_next_step", "one_next_on"],
			limit=layers.MOST,
		)
	]
