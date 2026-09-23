"""This workspace's AI credits: what is left, what went, and on what.

The numbers are the account's — the ledger lives there and a workspace holds no
copy — asked for in one call per screen. What the workspace adds is the one
thing the account cannot know: whose a conversation was. A call is filed
against the conversation it was made for, and the conversation has an owner
here, so "by person" is a join only this side can make.
"""

import frappe
from frappe.utils import add_days, getdate

from onedesk.one import account, roles

#: How the table is cut.
BY = ("Model", "Person", "Day")


def execute(filters=None):
	roles.require()
	filters = frappe._dict(filters or {})
	end = getdate(filters.to_date) if filters.to_date else getdate()
	start = getdate(filters.from_date) if filters.from_date else add_days(end, -29)
	by = filters.by if filters.by in BY else "Model"

	from onedesk.one_admin import faults

	try:
		said = account.ask("onedesk.one_admin.proxy.ai_usage", start=str(start), end=str(end)) or {}
	except faults.Again:
		frappe.throw(frappe._("The account could not be reached just now. Try again in a moment."))
	except faults.Refused as raised:
		frappe.throw(frappe.utils.strip_html(str(raised)))
	rows = {"Model": _by_model, "Person": _by_person, "Day": _by_day}[by](said)
	return _columns(by), rows, None, _chart(said, start, end), _summary(said)


def _columns(by: str) -> list[dict]:
	first = {
		"Model": {"fieldname": "what", "label": frappe._("Model"), "fieldtype": "Data", "width": 260},
		"Person": {"fieldname": "what", "label": frappe._("Person"), "fieldtype": "Link", "options": "User", "width": 240},
		"Day": {"fieldname": "what", "label": frappe._("Day"), "fieldtype": "Date", "width": 140},
	}[by]
	return [
		first,
		{"fieldname": "calls", "label": frappe._("Calls"), "fieldtype": "Int", "width": 90},
		{"fieldname": "credits", "label": frappe._("Credits"), "fieldtype": "Float", "precision": 4, "width": 120},
		{"fieldname": "each", "label": frappe._("Per Call"), "fieldtype": "Float", "precision": 4, "width": 110},
	]


def _row(what, calls, credits) -> dict:
	calls, credits = int(calls or 0), round(float(credits or 0), 4)
	return {"what": what, "calls": calls, "credits": credits, "each": round(credits / calls, 4) if calls else 0}


def _by_model(said: dict) -> list[dict]:
	from onedesk.one_ai.chat import named

	return [_row(named(one.get("why")), one.get("calls"), one.get("credits")) for one in said.get("models") or []]


def _by_day(said: dict) -> list[dict]:
	return [_row(one.get("day"), one.get("calls"), one.get("credits")) for one in said.get("days") or []]


def _by_person(said: dict) -> list[dict]:
	"""Each call's reference read back to a person.

	A conversation's owner; a person, where the reference is one (a settings
	screen's preview is filed under whoever pressed Try it); and everything
	else — an action somebody's code ran — together.
	"""
	references = said.get("references") or []
	named = [one.get("reference") for one in references if one.get("reference")]
	owners = dict(
		frappe.get_all(
			"AI Chat", filters={"name": ["in", named or [""]]}, fields=["name", "owner"], as_list=True
		)
	)
	people = set(frappe.get_all("User", filters={"name": ["in", named or [""]]}, pluck="name"))

	totals: dict[str, list] = {}
	for one in references:
		reference = one.get("reference") or ""
		who = owners.get(reference) or (reference if reference in people else frappe._("Other"))
		held = totals.setdefault(who, [0, 0.0])
		held[0] += int(one.get("calls") or 0)
		held[1] += float(one.get("credits") or 0)
	rows = [_row(who, calls, credits) for who, (calls, credits) in totals.items()]
	return sorted(rows, key=lambda row: row["credits"], reverse=True)


def _chart(said: dict, start, end) -> dict:
	"""Credits a day, every day of the period — a quiet day is a zero, not a gap."""
	spent = {str(one.get("day")): round(float(one.get("credits") or 0), 4) for one in said.get("days") or []}
	days, day = [], start
	while day <= end:
		days.append(day)
		day = add_days(day, 1)
	return {
		"data": {
			# The day of the month and nothing more. frappe-charts allows two or
			# three letters a label at thirty bars and cuts anything longer to
			# dots, and the report view overwrites the option that would thin
			# them out. The period itself is in the filters above the chart.
			"labels": [str(day.day) for day in days],
			"datasets": [{"name": frappe._("Credits"), "values": [spent.get(str(day), 0) for day in days]}],
		},
		"type": "bar",
		"fieldtype": "Float",
		"colors": ["#7C5CFA"],
		"height": 220,
	}


def _summary(said: dict) -> list[dict]:
	standing = said.get("standing") or {}
	total = said.get("total") or {}
	left = float(standing.get("available") or 0)
	cards = [
		{
			"value": left,
			"label": frappe._("Credits Left"),
			"datatype": "Float",
			"indicator": "Red" if left <= 0 else "Green",
		},
		{"value": round(float(total.get("credits") or 0), 4), "label": frappe._("Used"), "datatype": "Float"},
		{"value": int(total.get("calls") or 0), "label": frappe._("Calls"), "datatype": "Int"},
	]
	if standing.get("expiring") and standing.get("expires_on"):
		cards.append(
			{
				"value": float(standing["expiring"]),
				"label": frappe._("Expiring {0}").format(frappe.format(standing["expires_on"], {"fieldtype": "Date"})),
				"datatype": "Float",
				"indicator": "Orange",
			}
		)
	return cards
