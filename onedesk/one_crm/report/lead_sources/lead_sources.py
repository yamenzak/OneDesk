"""Which sources bring leads that turn into sales, and how fast they are answered.

A lead's source is its UTM Source; a lead with none is a row of its own, Not
Recorded, because a workspace that never records the source should see that
rather than a report that looks empty. A lead's deals are the deals made from
it, and one is won on the day it was won (`measure.closed`).
"""

from statistics import median

import frappe
from frappe import _
from frappe.utils import get_datetime, time_diff_in_hours

from onedesk.one_crm import measure


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	where = {}
	if filters.from_date and filters.to_date:
		where["creation"] = ["between", [filters.from_date, f"{filters.to_date} 23:59:59"]]
	leads = frappe.get_list(
		"Lead", filters=where, fields=["name", "utm_source", "creation", "one_first_reply_at"], limit=0
	)
	made = {}
	for deal in measure.deals(
		{"opportunity_from": "Lead", "party_name": ["in", [one.name for one in leads] or [""]]},
		fields=("party_name",),
	):
		made.setdefault(deal.party_name, []).append(deal)
	shut = measure.closed([deal.name for deals in made.values() for deal in deals])

	rows = {}
	for lead in leads:
		source = lead.utm_source or measure.not_recorded()
		row = rows.setdefault(source, _row(source))
		row["leads"] += 1
		if lead.one_first_reply_at:
			row["replies"].append(time_diff_in_hours(get_datetime(lead.one_first_reply_at), lead.creation))
		for deal in made.get(lead.name, []):
			row["deals"] += 1
			if shut.get(deal.name, frappe._dict()).outcome == "Won":
				row["won"] += 1
				row["won_value"] += measure.value(deal)

	out = []
	for row in rows.values():
		replies = row.pop("replies")
		row["replied"] = round(100 * len(replies) / row["leads"], 1)
		row["first_reply"] = round(median(replies), 1) if replies else None
		row["conversion"] = round(100 * row["won"] / row["leads"], 1)
		out.append(row)
	return _columns(), sorted(out, key=lambda row: -row["leads"])


def _row(source) -> dict:
	return {"source": source, "leads": 0, "replies": [], "deals": 0, "won": 0, "won_value": 0.0}


def _columns() -> list[dict]:
	return [
		{"fieldname": "source", "label": _("Source"), "fieldtype": "Data", "width": 160},
		{"fieldname": "leads", "label": _("Leads"), "fieldtype": "Int", "width": 80},
		{"fieldname": "replied", "label": _("Replied (%)"), "fieldtype": "Percent", "width": 110},
		{"fieldname": "first_reply", "label": _("Median First Reply (Hours)"), "fieldtype": "Float", "width": 190},
		{"fieldname": "deals", "label": _("Deals"), "fieldtype": "Int", "width": 80},
		{"fieldname": "won", "label": _("Won"), "fieldtype": "Int", "width": 80},
		{"fieldname": "won_value", "label": _("Won Value"), "fieldtype": "Currency", "width": 140},
		{"fieldname": "conversion", "label": _("Leads Won (%)"), "fieldtype": "Percent", "width": 130},
	]
