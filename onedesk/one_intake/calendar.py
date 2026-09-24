"""Intake on the calendar, and in the Deadlines report (docs/INTAKE.md §6).

Three kinds of date come out of what was read, and each is shown to whoever
may read the record it sits on:

- **a reading's deadline**: a bill's due date, an authority's "within one
  month", a document's expiry. It is shown to the person it was read for,
  with the day it was counted from and the rule, so the arithmetic can be
  checked. A matter that is closed has none.
- **a contract's last day to cancel**, from its notice period, for whoever
  may read the contract.
- **an employee's document expiring**, a passport or a permit, for whoever
  may read the employee.

Nothing is copied: each is read from its record as the person looking.
"""

import frappe
from frappe import _, _lt

from onedesk.one_calendar import layers

#: What a reading's date must be to be a deadline. A sick note's "valid
#: until" is the day somebody is back, which nobody has to act on; a
#: passport's is.
DEADLINES = ("Due", "Deadline", "Valid Until")
RENEWED = ("Identity Document", "Certificate", "Contract")

#: The records Intake made for a reading that, once done, settle its dates.
INVOICES = ("Purchase Invoice", "Sales Invoice")

LAYERS = [
	{
		"key": "deadlines",
		"label": _lt("Deadlines"),
		"color": "amber",
		"group": "Mine",
		"doctype": "File",
		"rows": "onedesk.one_intake.calendar.deadlines",
	},
	{
		"key": "cancel-by",
		"label": _lt("Last Day to Cancel"),
		"color": "orange",
		"group": "Workspace",
		"doctype": "Contract",
		"rows": "onedesk.one_intake.calendar.cancel_by",
	},
	{
		"key": "expiring",
		"label": _lt("Expiring Documents"),
		"color": "teal",
		"group": "Workspace",
		"doctype": "Employee",
		"on": False,
		"rows": "onedesk.one_intake.calendar.expiring",
	},
]


def _row(one: dict) -> dict:
	return {"name": one["name"], "doctype": one["doctype"], "title": one["title"], "start": one["date"], "all_day": 1, "id": one["id"], "description": one.get("rule")}


def deadlines(start, end) -> list[dict]:
	return [_row(one) for one in of_readings(start, end)]


def cancel_by(start, end) -> list[dict]:
	return [_row(one) for one in of_contracts(start, end)]


def expiring(start, end) -> list[dict]:
	return [_row(one) for one in of_employees(start, end)]


def of_readings(start, end, everyone: bool = False) -> list[dict]:
	"""The deadlines in what was read for the reader, or for anybody when an
	administrator asks for everyone's. Each opens the document it was read
	from."""
	found = frappe.get_all(
		"Reading Date",
		filters={"parenttype": "Reading", "what": ["in", DEADLINES], "date": ["between", [str(start), str(end)]]},
		fields=["parent", "date", "what", "about", "counted_from", "rule", "idx"],
		order_by="date asc",
		limit=layers.MOST,
	)
	if not found:
		return []
	conditions = {"name": ["in", list({one.parent for one in found})], "state": "Understood", "copy_of": ["is", "not set"]}
	if not everyone:
		conditions["on_behalf_of"] = frappe.session.user
	readings = {
		one.name: one
		for one in frappe.get_all("Reading", filters=conditions, fields=["name", "title", "kind", "source_doctype", "source_name", "on_behalf_of", "matter"])
	}
	done = settled(readings)
	out = []
	for one in found:
		reading = readings.get(one.parent)
		if not reading or not reading.source_name or reading.name in done:
			continue
		if one.what == "Valid Until" and reading.kind not in RENEWED:
			continue
		out.append(
			{
				"id": f"{one.parent}:{one.idx}",
				"date": one.date,
				"what": _(one.what),
				"title": f"{_(one.what)} · {reading.title or _(reading.kind or 'Document')}",
				"about": one.about,
				"doctype": reading.source_doctype,
				"name": reading.source_name,
				"counted_from": one.counted_from,
				"rule": one.rule,
				"person": reading.on_behalf_of,
			}
		)
	return out


def settled(readings: dict) -> set[str]:
	"""The readings nothing is left to do about: their matter is closed, the
	task Intake made for them is done, or the invoice it booked is paid."""
	if not readings:
		return set()
	heads = {one.matter for one in readings.values() if one.matter}
	closed = set(frappe.get_all("Reading", filters={"name": ["in", list(heads)], "matter_state": "Closed"}, pluck="name")) if heads else set()
	out = {name for name, one in readings.items() if one.matter in closed}
	made = frappe.get_all(
		"Intake Action",
		filters={"reading": ["in", list(readings)], "kind": ["in", ("Create", "Link")], "target_doctype": ["in", ("Task", *INVOICES)], "undone_by": ["is", "not set"]},
		fields=["reading", "target_doctype", "target_name"],
	)
	by_doctype: dict[str, dict] = {}
	for one in made:
		by_doctype.setdefault(one.target_doctype, {}).setdefault(one.target_name, set()).add(one.reading)
	finished = {
		"Task": {"status": ["in", ("Completed", "Cancelled")]},
		**{doctype: {"docstatus": 1, "outstanding_amount": 0} for doctype in INVOICES},
	}
	for doctype, targets in by_doctype.items():
		for name in frappe.get_all(doctype, filters={"name": ["in", list(targets)], **finished[doctype]}, pluck="name"):
			out |= targets[name]
	return out


def of_contracts(start, end) -> list[dict]:
	"""Contracts whose last day to cancel falls between two days."""
	if not frappe.db.has_column("Contract", "one_cancel_by"):
		return []
	return [
		{
			"id": f"Contract:{one.name}",
			"date": one.one_cancel_by,
			"what": _("Last Day to Cancel"),
			"title": f"{_('Last Day to Cancel')} · {one.party_name}",
			"about": one.one_notice_period,
			"doctype": "Contract",
			"name": one.name,
		}
		for one in frappe.get_list(
			"Contract",
			filters=[["docstatus", "<", 2], *layers.within("one_cancel_by", start, end)],
			fields=["name", "party_name", "one_cancel_by", "one_notice_period"],
			limit=layers.MOST,
		)
	]


def of_employees(start, end) -> list[dict]:
	"""Employees' documents expiring between two days, for whoever may read
	the employee."""
	people = {
		one.name: one.employee_name
		for one in frappe.get_list("Employee", filters={"status": "Active"}, fields=["name", "employee_name"], limit=0)
	}
	if not people:
		return []
	return [
		{
			"id": f"Employee Document:{one.name}",
			"date": one.expires_on,
			"what": _("Expires"),
			"title": f"{_(one.document_type)} · {people[one.parent]}",
			"about": one.number,
			"doctype": "Employee",
			"name": one.parent,
		}
		for one in frappe.get_all(
			"Employee Document",
			filters={"parenttype": "Employee", "parent": ["in", list(people)], "expires_on": ["between", [str(start), str(end)]]},
			fields=["name", "parent", "document_type", "number", "expires_on"],
			order_by="expires_on asc",
			limit=layers.MOST,
		)
	]
