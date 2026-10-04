"""A project's money, in two sides, and where it is heading.

**Customer**: what they've been quoted, what they've ordered, what's been
delivered and invoiced, and what they've paid. **Cost**: what's been ordered
from suppliers, received and billed, what they've been paid, and the team's
time, stock used and expense claims. Each figure opens the documents behind
it, and the project's sub-projects are included, as the head's are.

Every figure is ERPNext's own record added up, before tax, as ERPNext adds up a
project's Billed and Purchases: a document's lines that name the project, on
submitted documents. Payments are what was paid, tax included. Time, stock used
and expense claims are the totals ERPNext keeps on the project.

**The forecast** answers before the money's gone. The contract is what the
customer ordered, or the billable time when nothing was ordered. The forecast
cost is what's been spent, plus what suppliers still have to bill on their
orders, plus the budget not yet used: at least the budget, more once the
spending and the orders pass it (`forecast`).
"""

import json
from typing import Annotated
from urllib.parse import quote

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt

from onedesk.one_project import tree

#: Documents whose lines name the project: the line table, and what a figure
#: adds up on it.
LINES = {
	"Sales Order": "Sales Order Item",
	"Delivery Note": "Delivery Note Item",
	"Sales Invoice": "Sales Invoice Item",
	"Purchase Order": "Purchase Order Item",
	"Purchase Receipt": "Purchase Receipt Item",
	"Purchase Invoice": "Purchase Invoice Item",
}


def forecast(contract: float, spent: float, open_orders: float, budget: float) -> dict:
	"""The forecast cost and margin. Pure.

	What's spent and what's still to be billed on orders will be spent
	whatever the budget says; the budget is what the rest is expected to
	cost, so the forecast is never under it."""
	cost = max(flt(budget), flt(spent) + flt(open_orders))
	return {"cost": cost, "margin": flt(contract) - cost}


def unbilled(rows: list) -> float:
	"""What suppliers still have to bill on their order lines, in the
	company's currency: each line's share not yet billed. Pure."""
	left = 0.0
	for row in rows:
		if flt(row.amount) <= 0:
			continue
		share = max(0.0, flt(row.amount) - flt(row.billed_amt)) / flt(row.amount)
		left += flt(row.base_net_amount) * share
	return left


#: Documents whose submitting or cancelling changes a project's money.
MOVES = {*LINES, "Quotation", "Payment Entry", "Timesheet", "Expense Claim", "Stock Entry"}

#: Where a list finds the project when it isn't the document's own `project`.
WHERE = {
	**{doctype: f"{child}.project" for doctype, child in LINES.items()},
	"Timesheet": "Timesheet Detail.project",
}


def _route(doctype: str, filters: dict) -> str:
	"""A list, filtered in the address as the desk writes it."""
	query = "&".join(
		f"{quote(field, safe='')}="
		+ quote(value if isinstance(value, str) else json.dumps(value, separators=(",", ":")), safe="")
		for field, value in filters.items()
	)
	return f"/desk/{frappe.scrub(doctype).replace('_', '-')}?{query}"


def _sees(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def _lines(doctype: str, projects: list[str]) -> float:
	child = frappe.qb.DocType(LINES[doctype])
	found = (
		frappe.qb.from_(child)
		.select(Sum(child.base_net_amount))
		.where(child.project.isin(projects) & (child.docstatus == 1))
		.run()
	)
	return flt(found[0][0]) if found else 0.0


def _figure(label: str, value: float, doctype: str | None, projects: list[str], **filters) -> dict:
	"""One figure, opening the submitted documents behind it."""
	said = {"label": label, "value": value}
	if doctype:
		where = {WHERE.get(doctype, "project"): ["in", projects]}
		said["route"] = _route(doctype, {**where, "docstatus": 1, **filters})
	return said


@frappe.whitelist()
@frappe.read_only()
def money(project: Annotated[str, "The project."]) -> dict:
	"""The project's two sides and its forecast, its sub-projects included."""
	frappe.has_permission("Project", "read", doc=project, throw=True)
	projects = sorted(tree.below({project}, tree.parents()))
	kept = tree.totals(project)["tree"]

	customer, cost = [], []
	if _sees("Quotation"):
		q = frappe.qb.DocType("Quotation")
		quoted = (
			frappe.qb.from_(q)
			.select(Sum(q.base_net_total))
			.where(q.project.isin(projects) & (q.docstatus == 1) & (q.status != "Lost"))
			.run()
		)
		customer.append(_figure(_("Quoted"), flt(quoted[0][0]), "Quotation", projects, status=["!=", "Lost"]))
	ordered = _lines("Sales Order", projects)
	for doctype, label, value in (
		("Sales Order", _("Ordered"), ordered),
		("Delivery Note", _("Delivered"), None),
		("Sales Invoice", _("Invoiced"), None),
	):
		if _sees(doctype):
			customer.append(
				_figure(label, value if value is not None else _lines(doctype, projects), doctype, projects)
			)
	received = _paid(projects, "Receive")
	if received is not None:
		customer.append(_figure(_("Paid"), received, "Payment Entry", projects, payment_type="Receive"))

	open_orders = 0.0
	if _sees("Purchase Order"):
		cost.append(_figure(_("Ordered"), _lines("Purchase Order", projects), "Purchase Order", projects))
		open_orders = _open_orders(projects)
	if _sees("Purchase Receipt"):
		cost.append(
			_figure(_("Received"), _lines("Purchase Receipt", projects), "Purchase Receipt", projects)
		)
	billed = _lines("Purchase Invoice", projects)
	if _sees("Purchase Invoice"):
		cost.append(_figure(_("Billed"), billed, "Purchase Invoice", projects))
	paid = _paid(projects, "Pay")
	if paid is not None:
		cost.append(_figure(_("Paid"), paid, "Payment Entry", projects, payment_type="Pay"))
	time = flt(kept["total_costing_amount"])
	stock = flt(kept["total_consumed_material_cost"])
	claims = flt(kept["total_expense_claim"])
	own = [
		_figure(_("Time"), time, "Timesheet" if _sees("Timesheet") else None, projects),
		_figure(_("Stock Used"), stock, "Stock Entry" if _sees("Stock Entry") else None, projects),
		_figure(_("Expense Claims"), claims, "Expense Claim" if _sees("Expense Claim") else None, projects),
	]

	invoiced = _lines("Sales Invoice", projects)
	spent = billed + time + stock + claims
	contract = ordered or flt(kept["total_billable_amount"])
	ahead = forecast(contract, spent, open_orders, flt(kept["estimated_costing"]))
	return {
		"project": project,
		"currency": frappe.db.get_default("currency"),
		"customer": customer,
		"cost": cost,
		"own": own,
		"contract": contract,
		"budget": flt(kept["estimated_costing"]),
		"spent": spent,
		"open_orders": open_orders,
		"forecast_cost": ahead["cost"],
		"forecast_margin": ahead["margin"],
		"invoiced": invoiced,
		"margin": invoiced - spent,
	}


def moved(doc, method=None) -> None:
	"""Tell a project's open page its money changed, and its parents' pages,
	whose figures include it."""
	if doc.doctype not in MOVES:
		return
	named = {doc.get("project")} | {
		row.get("project") for row in doc.get("items") or doc.get("time_logs") or []
	}
	named.discard(None)
	named.discard("")
	if not named:
		return
	of = tree.parents()
	for project in {one for each in named for one in tree.above(each, of)}:
		frappe.publish_realtime(
			"one_project_money", {"project": project}, doctype="Project", docname=project, after_commit=True
		)


def _paid(projects: list[str], kind: str) -> float | None:
	if not _sees("Payment Entry"):
		return None
	pe = frappe.qb.DocType("Payment Entry")
	amount = pe.base_received_amount if kind == "Receive" else pe.base_paid_amount
	found = (
		frappe.qb.from_(pe)
		.select(Sum(amount))
		.where(pe.project.isin(projects) & (pe.docstatus == 1) & (pe.payment_type == kind))
		.run()
	)
	return flt(found[0][0]) if found else 0.0


def _open_orders(projects: list[str]) -> float:
	"""What suppliers still have to bill on the tree's orders. A closed order
	won't be billed any further."""
	item = frappe.qb.DocType("Purchase Order Item")
	po = frappe.qb.DocType("Purchase Order")
	rows = (
		frappe.qb.from_(item)
		.join(po)
		.on(item.parent == po.name)
		.select(item.amount, item.billed_amt, item.base_net_amount)
		.where(item.project.isin(projects) & (po.docstatus == 1) & (po.status != "Closed"))
		.run(as_dict=True)
	)
	return unbilled(rows)
