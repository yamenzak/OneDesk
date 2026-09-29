"""What each workspace spent on AI, on which models and for which of OneAI's
actions, and what it cost us.

The numbers are `ledger.usage`'s — one row per model call, what it was charged
once the provider said what it used, and what the provider charged us for it
— because only the ledger reads its own tables. This is the cut and the
columns. Charged is the credits at the smallest credit pack's price a
credit (offerings.credit_price), so Margin is what OneAI makes on the calls
at list price.
"""

import frappe
from frappe.utils import add_days, flt, getdate

from onedesk.one_admin import ledger, site

#: How a period is cut. Each is what an operator asks: who spends, on which
#: models, on which of OneAI's actions, and who spends on what.
BY = {
	"Workspace": ["tenant"],
	"Model": ["why"],
	"Action": ["action"],
	"Workspace and Model": ["tenant", "why"],
	"Workspace and Action": ["tenant", "action"],
}

#: What the price list, the provider and so every column here is in.
CURRENCY = "USD"


def execute(filters=None):
	site.require_admin()
	filters = frappe._dict(filters or {})
	by = BY.get(filters.by) or BY["Workspace"]
	rows, whole = usage(filters, by)
	return _columns(by), rows, None, None, _summary(whole)


def usage(filters, by: list[str]) -> tuple[list[dict], dict | None]:
	"""The period's rows, cut `by`, each with what it was charged and what it
	cost us, and the whole period as one more row."""
	start = getdate(filters.from_date) if filters.get("from_date") else getdate().replace(day=1)
	end = add_days(getdate(filters.to_date) if filters.get("to_date") else getdate(), 1)
	rows = ledger.usage(start, end, by, tenant=filters.get("tenant"), model=filters.get("model"))
	if not rows:
		return [], None
	from onedesk.one_admin import offerings

	each = offerings.credit_price()
	models = dict(frappe.get_all("AI Model", fields=["name", "label"], as_list=True))
	actions = dict(frappe.get_all("AI Action", fields=["name", "label"], as_list=True))
	# frappe's own total row adds every number up, and a sum of "workspaces" or
	# of a margin is not a number anybody means. This one counts the whole
	# period, and its margin is the period's.
	whole = ledger.usage(start, end, [], tenant=filters.get("tenant"), model=filters.get("model"))[0]
	whole[by[0]] = frappe._("Total")
	whole.bold = 1
	for row in [*rows, whole]:
		row.currency = CURRENCY
		row.credits = round(flt(row.credits), 2)
		row.charged = round(row.credits * each, 4)
		row.cost_us = round(flt(row.usd), 4)
		row.margin = f"{row.charged / row.cost_us:.1f}×" if row.cost_us else ""
		if "why" in by and row is not whole:
			row.model = models.get(row.why) or row.why
		if "action" in by and row is not whole:
			row.action_name = frappe._(actions.get(row.action) or "") or frappe._("Not recorded")
	if "why" in by:
		whole.model = whole.pop("why", None)
	if "action" in by:
		whole.action_name = whole.pop("action", None)
	return [*rows, whole], whole


def _columns(by: list[str]) -> list[dict]:
	named = {
		"tenant": {
			"fieldname": "tenant",
			"label": frappe._("Workspace"),
			"fieldtype": "Link",
			"options": "Tenant",
			"width": 170,
		},
		"why": {"fieldname": "model", "label": frappe._("Model"), "fieldtype": "Data", "width": 220},
		"action": {
			"fieldname": "action_name",
			"label": frappe._("Action"),
			"fieldtype": "Data",
			"width": 200,
		},
	}
	columns = [
		{
			"fieldname": "currency",
			"label": frappe._("Currency"),
			"fieldtype": "Link",
			"options": "Currency",
			"hidden": 1,
		},
		*(named[key] for key in by),
	]
	# The other side of the cut, counted, so a row still says how wide it is.
	if by in (["tenant"], ["action"]):
		columns.append({"fieldname": "models", "label": frappe._("Models"), "fieldtype": "Int", "width": 80})
	if by in (["why"], ["action"]):
		columns.append(
			{"fieldname": "workspaces", "label": frappe._("Workspaces"), "fieldtype": "Int", "width": 115}
		)
	return [
		*columns,
		{"fieldname": "calls", "label": frappe._("Calls"), "fieldtype": "Int", "width": 70},
		{
			"fieldname": "credits",
			"label": frappe._("Credits"),
			"fieldtype": "Float",
			"precision": 2,
			"width": 90,
		},
		{
			"fieldname": "charged",
			"label": frappe._("Charged"),
			"fieldtype": "Currency",
			"options": "currency",
			# Calls cost fractions of a cent, and two places reads them as free.
			"precision": 4,
			"width": 100,
		},
		{
			"fieldname": "cost_us",
			"label": frappe._("Cost"),
			"fieldtype": "Currency",
			"options": "currency",
			# Calls cost fractions of a cent, and two places reads them as free.
			"precision": 4,
			"width": 100,
		},
		{"fieldname": "margin", "label": frappe._("Margin"), "fieldtype": "Data", "width": 80},
		{"fieldname": "last", "label": frappe._("Last Call"), "fieldtype": "Datetime", "width": 190},
	]


def _summary(whole) -> list[dict]:
	if not whole:
		return []
	money = {"datatype": "Currency", "currency": CURRENCY}
	return [
		{"label": frappe._("Calls"), "value": whole.calls, "datatype": "Int"},
		{"label": frappe._("Credits"), "value": f"{whole.credits:,.2f}", "datatype": "Data"},
		{"label": frappe._("Charged"), "value": whole.charged, **money},
		{"label": frappe._("Cost"), "value": whole.cost_us, **money},
		{
			"label": frappe._("Margin"),
			"value": whole.margin or "—",
			"datatype": "Data",
			"indicator": "Green" if whole.cost_us and whole.charged > whole.cost_us else "Red",
		},
		{"label": frappe._("Workspaces"), "value": whole.workspaces, "datatype": "Int"},
	]
