"""What each workspace spent on AI, and on which models.

The numbers are `ledger.usage`'s — one row per model call, what it was charged
once the provider said what it used — because only the ledger reads its own
tables. This is the cut and the columns.
"""

import frappe
from frappe.utils import add_days, getdate

from onedesk.one_admin import ledger, site

#: How a period is cut. Each is what an operator asks: who spends, what is
#: spent on, and who spends on what.
BY = {
	"Workspace": ["tenant"],
	"Model": ["why"],
	"Workspace and Model": ["tenant", "why"],
}


def execute(filters=None):
	site.require_admin()
	filters = frappe._dict(filters or {})
	by = BY.get(filters.by) or BY["Workspace"]
	return _columns(by), _rows(filters, by)


def _columns(by: list[str]) -> list[dict]:
	named = {
		"tenant": {"fieldname": "tenant", "label": frappe._("Workspace"), "fieldtype": "Link", "options": "Tenant", "width": 200},
		"why": {"fieldname": "why", "label": frappe._("Model"), "fieldtype": "Link", "options": "AI Model", "width": 300},
	}
	columns = [named[key] for key in by]
	# The other side of the cut, counted, so a row still says how wide it is.
	if by == ["tenant"]:
		columns.append({"fieldname": "models", "label": frappe._("Models"), "fieldtype": "Int", "width": 90})
	if by == ["why"]:
		columns.append({"fieldname": "workspaces", "label": frappe._("Workspaces"), "fieldtype": "Int", "width": 110})
	return columns + [
		{"fieldname": "calls", "label": frappe._("Calls"), "fieldtype": "Int", "width": 90},
		{"fieldname": "credits", "label": frappe._("Credits"), "fieldtype": "Float", "precision": 4, "width": 120},
		{"fieldname": "each", "label": frappe._("Per Call"), "fieldtype": "Float", "precision": 4, "width": 110},
		{"fieldname": "last", "label": frappe._("Last Call"), "fieldtype": "Datetime", "width": 170},
	]


def _rows(filters, by: list[str]) -> list[dict]:
	start = getdate(filters.from_date) if filters.from_date else getdate().replace(day=1)
	end = add_days(getdate(filters.to_date) if filters.to_date else getdate(), 1)
	rows = ledger.usage(start, end, by, tenant=filters.tenant, model=filters.model)
	if not rows:
		return []
	# frappe's own total row adds every number up, and a sum of "workspaces" or
	# of "per call" is not a number anybody means. This one counts the whole
	# period, and per call is the period's credits over its calls.
	whole = ledger.usage(start, end, [], tenant=filters.tenant, model=filters.model)[0]
	whole[by[0]] = frappe._("Total")
	whole.bold = 1
	for row in [*rows, whole]:
		row.credits = round(row.credits or 0, 4)
		row.each = round(row.credits / row.calls, 4) if row.calls else 0
	return [*rows, whole]
