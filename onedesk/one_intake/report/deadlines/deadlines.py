"""Deadlines: every date something must be done by, from what was read
(onedesk/one_intake/README.md §6).

The calendar's three kinds of date, in one list a person can work down.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from onedesk.one_intake import calendar

SOURCES = {"Documents": calendar.of_readings, "Contracts": calendar.of_contracts, "Employees": calendar.of_employees}


def execute(filters=None):
	from onedesk.one.roles import administers

	filters = frappe._dict(filters or {})
	start = getdate(filters.get("from_date") or today())
	end = getdate(filters.get("to_date") or add_days(start, 90))
	data = []
	for source, read in SOURCES.items():
		if filters.get("source") and filters.source != source:
			continue
		if source == "Contracts" and not frappe.has_permission("Contract", "read"):
			continue
		if source == "Employees" and not frappe.has_permission("Employee", "read"):
			continue
		found = read(start, end, administers()) if source == "Documents" else read(start, end)
		data += [{**one, "source": _(source), "days": (getdate(one["date"]) - getdate(today())).days} for one in found]
	data.sort(key=lambda one: getdate(one["date"]))
	columns = [
		{"fieldname": "date", "label": _("Date"), "fieldtype": "Date", "width": 110},
		{"fieldname": "days", "label": _("Days Left"), "fieldtype": "Int", "width": 90},
		{"fieldname": "title", "label": _("What"), "fieldtype": "Data", "width": 320},
		{"fieldname": "doctype", "label": _("Document Type"), "fieldtype": "Data", "hidden": 1},
		{"fieldname": "name", "label": _("Record"), "fieldtype": "Data", "hidden": 1},
		{"fieldname": "about", "label": _("About"), "fieldtype": "Data", "width": 240},
		{"fieldname": "counted_from", "label": _("Counted From"), "fieldtype": "Date", "width": 130},
		{"fieldname": "rule", "label": _("Rule"), "fieldtype": "Data", "width": 380},
	]
	return columns, data
