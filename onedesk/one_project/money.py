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


#: A quotation that still stands: open, or ordered. A lost or expired one
#: doesn't, and an amended one is cancelled, so a revision counts once.
QUOTED = ("Open", "Replied", "Partially Ordered", "Ordered")
#: A quotation the customer hasn't answered yet.
OPEN_QUOTE = ("Open", "Replied")

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
	said = {"label": label, "value": value, "doctype": doctype}
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
			.where(q.project.isin(projects) & (q.docstatus == 1) & q.status.isin(QUOTED))
			.run()
		)
		customer.append(
			_figure(_("Quoted"), flt(quoted[0][0]), "Quotation", projects, status=["in", list(QUOTED)])
		)
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
	if _sees("Sales Invoice"):
		retention = _retained(projects)
		if retention:
			customer.append(_figure(_("Retention Held"), retention, None, projects))

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
		"suppliers": _suppliers(projects) if _sees("Purchase Order") else [],
		"can_bill": bool(frappe.has_permission("Purchase Invoice", "create")),
		"can_order": bool(frappe.has_permission("Purchase Order", "create")),
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
	from onedesk.one_project import budget

	for project in named:
		# A cost type this took over its budget is told (budget.py).
		budget.over(project)
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


def _retained(projects: list[str]) -> float:
	"""The customer's retention still held on the tree's invoices
	(progress.py): on each, the retention or what's owed, whichever is less."""
	from onedesk.one_project.progress import RETENTION, held

	names = list(
		set(
			frappe.get_all(
				"Sales Invoice Item", filters={"project": ["in", projects], "docstatus": 1}, pluck="parent"
			)
		)
	)
	if not names:
		return 0.0
	kept = {
		one.parent: flt(one.base_payment_amount)
		for one in frappe.get_all(
			"Payment Schedule",
			filters={"parent": ["in", names], "parenttype": "Sales Invoice", "payment_term": RETENTION},
			fields=["parent", "base_payment_amount"],
		)
	}
	if not kept:
		return 0.0
	owed = frappe.get_all(
		"Sales Invoice",
		filters={"name": ["in", list(kept)]},
		fields=["name", "outstanding_amount", "conversion_rate"],
	)
	return sum(
		held(kept[one.name], flt(one.outstanding_amount) * flt(one.conversion_rate or 1)) for one in owed
	)


def _suppliers(projects: list[str]) -> list[dict]:
	"""Each order from a supplier on the tree, the subcontracts: what it's
	for, what's billed, what's left to bill, the retention still held, the
	advance not yet set off, and what's been paid (progress.py)."""
	from onedesk.one_project.progress import RETENTION, held

	item = frappe.qb.DocType("Purchase Order Item")
	rows = (
		frappe.qb.from_(item)
		.select(item.parent, Sum(item.base_net_amount).as_("ordered"))
		.where(item.project.isin(projects) & (item.docstatus == 1))
		.groupby(item.parent)
		.run(as_dict=True)
	)
	if not rows:
		return []
	orders = {row.parent: row.ordered for row in rows}
	heads = {
		one.name: one
		for one in frappe.get_all(
			"Purchase Order",
			filters={"name": ["in", list(orders)]},
			fields=[
				"name",
				"supplier",
				"supplier_name",
				"status",
				"per_billed",
				"transaction_date",
				"advance_paid",
				"conversion_rate",
				"one_retention",
				"project",
			],
		)
	}
	lines = frappe.get_all(
		"Purchase Order Item",
		filters={"parent": ["in", list(orders)]},
		fields=["parent", "amount", "billed_amt", "base_net_amount", "item_name", "project"],
		order_by="idx asc",
	)
	bills = frappe.get_all(
		"Purchase Invoice Item",
		filters={"purchase_order": ["in", list(orders)], "docstatus": 1},
		fields=["parent", "purchase_order", "base_net_amount"],
	)
	invoices = {
		one.name: one
		for one in frappe.get_all(
			"Purchase Invoice",
			filters={"name": ["in", list({bill.parent for bill in bills})]},
			fields=["name", "base_grand_total", "outstanding_amount", "conversion_rate", "total_advance"],
		)
	}
	kept = {
		one.parent: flt(one.base_payment_amount)
		for one in frappe.get_all(
			"Payment Schedule",
			filters={
				"parent": ["in", list(invoices)],
				"parenttype": "Purchase Invoice",
				"payment_term": RETENTION,
			},
			fields=["parent", "base_payment_amount"],
		)
	}
	found = []
	for name, ordered in orders.items():
		head = heads[name]
		mine = {bill.parent for bill in bills if bill.purchase_order == name}
		billed = sum(flt(bill.base_net_amount) for bill in bills if bill.purchase_order == name)
		left = 0.0 if head.status == "Closed" else unbilled([one for one in lines if one.parent == name])
		retained = paid = advanced = owing = 0.0
		for invoice in (invoices[one] for one in mine if one in invoices):
			owed = flt(invoice.outstanding_amount) * flt(invoice.conversion_rate or 1)
			retained += held(kept.get(invoice.name), owed)
			paid += flt(invoice.base_grand_total) - owed
			advanced += flt(invoice.total_advance)
			owing += owed
		own = [one for one in lines if one.parent == name]
		advance = max(0.0, flt(head.advance_paid) * flt(head.conversion_rate or 1) - advanced)
		found.append(
			{
				"order": name,
				"supplier": head.supplier_name or head.supplier,
				"for": bought(own),
				"project": head.project or next((one.project for one in own if one.project), None),
				# What's billed and not paid, less the retention held till later.
				"to_pay": max(0.0, owing - retained),
				"ordered": flt(ordered),
				"billed": billed,
				"left": left,
				"retention": retained,
				"advance": advance,
				"paid": paid + advance,
				"status": head.status,
				"ordered_on": str(head.transaction_date) if head.transaction_date else None,
				# Bill Progress drafts the next bill; an order closed, held or
				# billed in full has none.
				"can_bill": head.status not in ("Closed", "On Hold", "Completed")
				and flt(head.per_billed) < 100,
				"route": f"/desk/purchase-order/{quote(name, safe='')}",
			}
		)
	return sorted(found, key=lambda one: -one["ordered"])


def bought(lines: list) -> str | None:
	"""What an order is for: its first line, and how many more. Pure."""
	names = [one.item_name for one in lines if one.item_name]
	if not names:
		return None
	return names[0] if len(names) == 1 else _("{0} +{1}").format(names[0], len(names) - 1)


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
