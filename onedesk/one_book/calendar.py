"""OneBook on the calendar: the reader's company's invoices and bills still
owed, on the day each falls due, each opening its invoice."""

import frappe
from frappe import _lt

from onedesk.one_calendar import layers

LAYERS = [
	{
		"key": "invoices-due",
		"label": _lt("Invoices Due"),
		"color": "green",
		"group": "Workspace",
		"on": False,
		"doctype": "Sales Invoice",
		"rows": "onedesk.one_book.calendar.invoices",
	},
	{
		"key": "bills-due",
		"label": _lt("Bills Due"),
		"color": "red",
		"group": "Workspace",
		"on": False,
		"doctype": "Purchase Invoice",
		"rows": "onedesk.one_book.calendar.bills",
	},
]

def invoices(start, end) -> list[dict]:
	return _owed("Sales Invoice", "customer", start, end, [])


def bills(start, end) -> list[dict]:
	return _owed("Purchase Invoice", "supplier", start, end, [])


def _owed(doctype: str, party: str, start, end, which: list) -> list[dict]:
	"""Submitted and not yet paid, the reader's company's, by due date."""
	from erpnext import get_default_company

	return [
		{
			"name": one.name,
			"title": f"{one.party_name} · {frappe.format(one.outstanding_amount, {'fieldtype': 'Currency', 'options': one.party_account_currency})}",
			"start": one.due_date,
			"all_day": 1,
		}
		for one in frappe.get_list(
			doctype,
			filters=[
				*which,
				["docstatus", "=", 1],
				["outstanding_amount", ">", 0],
				["company", "=", get_default_company()],
				*layers.within("due_date", start, end),
			],
			fields=["name", f"{party}_name as party_name", "outstanding_amount", "party_account_currency", "due_date"],
			limit=layers.MOST,
		)
	]
