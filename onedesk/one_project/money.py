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
cost is, for each cost type, what's been spent and what suppliers still have
to bill on their orders, or its budget while that's more; then the same for
the rest of the budget. A cost type over its budget shows, even while
another is under. With no budget there's no forecast (`forecast`).
"""

import json
from typing import Annotated
from urllib.parse import quote

import frappe
from frappe import _
from frappe.query_builder.functions import Sum
from frappe.utils import flt, getdate, nowdate

from onedesk.one_project import tree
from onedesk.one_project.progress import LUMP_SUM

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


def forecast(
	contract: float,
	spent: float,
	open_orders: float,
	budget: float,
	types: list[dict] | None = None,
	rest: dict | None = None,
) -> dict:
	"""The forecast cost and margin. Pure.

	What's spent and still to be billed on orders will be spent whatever the
	budget says; the budget is what the rest is expected to cost, so each
	cost type's forecast is never under its budget, and one over its budget
	isn't made up for by another under. Without cost types the whole budget
	is one. With no budget there's nothing to forecast against: None."""
	if not flt(budget):
		return {"cost": None, "margin": None}
	if types:
		cost = sum(max(flt(one["budget"]), flt(one["spent"]) + flt(one["committed"])) for one in types)
		if rest:
			cost += max(flt(rest["budget"]), flt(rest["spent"]) + flt(rest["committed"]))
	else:
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
MOVES = {*LINES, "Quotation", "Payment Entry", "Timesheet", "Expense Claim", "Stock Entry", "Journal Entry"}

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
	projects = sorted(tree.scope(project))
	kept = tree.totals(project)["own" if tree.narrowed(project) else "tree"]

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
	received = _paid_on(projects, "Sales Invoice")
	owed = received["owed"] if received else 0.0
	advance = received["advance"] if received else 0.0
	if received is not None:
		customer.append(
			_figure(_("Paid"), received["paid"], "Payment Entry", projects) | {"route": received["route"]}
		)
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
	paid = _paid_on(projects, "Purchase Invoice")
	if paid is not None:
		cost.append(_figure(_("Paid"), paid["paid"], "Payment Entry", projects) | {"route": paid["route"]})
	time = flt(kept["total_costing_amount"])
	stock = flt(kept["total_consumed_material_cost"])
	claims = flt(kept["total_expense_claim"])
	journals = _journals(projects)
	own = [
		_figure(_("Time"), time, "Timesheet" if _sees("Timesheet") else None, projects),
		_figure(_("Stock Used"), stock, "Stock Entry" if _sees("Stock Entry") else None, projects),
		_figure(_("Expense Claims"), claims, "Expense Claim" if _sees("Expense Claim") else None, projects),
		_figure(
			_("Journal Entries"), journals, "Journal Entry" if _sees("Journal Entry") else None, projects
		),
	]

	from onedesk.one_project import budget, kinds

	kind = frappe.db.get_value("Project", project, "one_kind")
	invoiced = _lines("Sales Invoice", projects)
	spent = billed + time + stock + claims + journals
	# Time and materials earns as the work is done: what's invoiced and what's
	# still to invoice. Everything else earns as it's invoiced.
	to_invoice = _to_invoice(project) if kind == kinds.TIME else 0.0
	earned = invoiced + to_invoice
	if kind == kinds.RETAINER:
		# The fee is what it brings in, not its hours at their rates.
		contract = ordered
	elif kind == kinds.TIME:
		contract = ordered or earned
	else:
		contract = ordered or flt(kept["total_billable_amount"])

	if to_invoice and _sees("Sales Invoice"):
		customer.append(_figure(_("Not Invoiced Yet"), to_invoice, None, projects))

	types = budget.types(project, projects)
	rest = budget.other(types, flt(kept["estimated_costing"]), spent, open_orders) if types else None
	ahead = forecast(contract, spent, open_orders, flt(kept["estimated_costing"]), types, rest)
	# A margin to forecast needs a price to forecast it against: a contract,
	# or an order capping time and materials. A retainer is measured by the
	# month, an internal project against its budget.
	if kind in (kinds.RETAINER, kinds.INTERNAL) or (kind == kinds.TIME and not ordered):
		ahead["margin"] = None
	return {
		"project": project,
		"currency": frappe.db.get_default("currency"),
		"customer": customer,
		"cost": cost,
		"own": own,
		"suppliers": _placed(_suppliers(projects), project) if _sees("Purchase Order") else [],
		"can_pay": bool(frappe.has_permission("Payment Entry", "create")),
		"can_bill": bool(frappe.has_permission("Purchase Invoice", "create")),
		"can_order": bool(frappe.has_permission("Purchase Order", "create")),
		"contract": contract,
		"budget": flt(kept["estimated_costing"]),
		"spent": spent,
		"open_orders": open_orders,
		"forecast_cost": ahead["cost"],
		"forecast_margin": ahead["margin"],
		"invoiced": invoiced,
		"to_invoice": to_invoice,
		# What the customer still owes on the invoices, and has paid ahead of
		# them, tax included as it's paid.
		"owed": owed,
		"advance": advance,
		"earned": earned,
		"margin": earned - spent,
		"kind": kind,
		"cost_types": {
			"can_set": bool(frappe.has_permission("Budget", "create")),
			"lines": types,
			"other": rest,
		},
	}


def moved(doc, method=None) -> None:
	"""Tell a project's open page its money changed, and its parents' pages,
	whose figures include it."""
	if doc.doctype not in MOVES:
		return
	named = {doc.get("project")} | {
		row.get("project") for row in doc.get("items") or doc.get("time_logs") or doc.get("accounts") or []
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


#: An invoice's order, on its lines, and the payment kind that pays it.
PAID = {
	"Sales Invoice": ("sales_order", "Sales Order", "Receive"),
	"Purchase Invoice": ("purchase_order", "Purchase Order", "Pay"),
}


def paid_share(invoices: list, mine: dict) -> float:
	"""What's been paid of the invoices, in the company's currency: each
	one's total less what's still owed, in the share of it that's the
	project's. Tax is included, as it's paid. Pure."""
	paid = 0.0
	for one in invoices:
		whole = flt(one.base_net_total)
		share = flt(mine.get(one.name)) / whole if whole else 1.0
		owed = flt(one.outstanding_amount) * flt(one.conversion_rate or 1)
		paid += (flt(one.base_grand_total) - owed) * share
	return paid


def owed_share(invoices: list, mine: dict) -> float:
	"""What's still owed on the invoices, in the company's currency, in the
	share of each that's the project's. Tax included, as it's owed. Pure."""
	owed = 0.0
	for one in invoices:
		whole = flt(one.base_net_total)
		share = flt(mine.get(one.name)) / whole if whole else 1.0
		owed += flt(one.outstanding_amount) * flt(one.conversion_rate or 1) * share
	return owed


def _paid_on(projects: list[str], doctype: str) -> dict | None:
	"""What's been paid on the tree's invoices, whichever payment paid them,
	with the advances on its orders not yet set against an invoice and the
	payments naming the project that aren't allocated yet; what's still owed
	on them; the advance alone; and the payments behind it, as a list."""
	if not _sees(doctype) or not _sees("Payment Entry"):
		return None
	on_order, order_type, kind = PAID[doctype]
	child = frappe.qb.DocType(LINES[doctype])
	rows = (
		frappe.qb.from_(child)
		.select(child.parent, child[on_order], Sum(child.base_net_amount).as_("amount"))
		.where(child.project.isin(projects) & (child.docstatus == 1))
		.groupby(child.parent, child[on_order])
		.run(as_dict=True)
	)
	mine: dict = {}
	for row in rows:
		mine[row.parent] = mine.get(row.parent, 0.0) + flt(row.amount)
	invoices = frappe.get_all(
		doctype,
		filters={"name": ["in", list(mine) or [""]]},
		fields=[
			"name",
			"base_net_total",
			"base_grand_total",
			"outstanding_amount",
			"conversion_rate",
			"total_advance",
		],
	)
	paid = paid_share(invoices, mine)
	owed = owed_share(invoices, mine)
	advance = 0.0
	# An order's advance not yet set against its invoices.
	order_lines = frappe.qb.DocType(LINES[order_type])
	orders = [
		one[0]
		for one in frappe.qb.from_(order_lines)
		.select(order_lines.parent)
		.distinct()
		.where(order_lines.project.isin(projects) & (order_lines.docstatus == 1))
		.run()
	]
	set_off: dict = {}
	advanced = {one.name: flt(one.total_advance) for one in invoices}
	for row in rows:
		if row.get(on_order):
			set_off[row[on_order]] = set_off.get(row[on_order], 0.0) + advanced.pop(row.parent, 0.0)
	for one in frappe.get_all(
		order_type,
		filters={"name": ["in", orders or [""]]},
		fields=["name", "advance_paid", "conversion_rate"],
	):
		advance += max(
			0.0, flt(one.advance_paid) * flt(one.conversion_rate or 1) - set_off.get(one.name, 0.0)
		)
	# Paid on account, naming the project, not matched to anything yet.
	pe = frappe.qb.DocType("Payment Entry")
	party = pe.paid_amount if kind == "Receive" else pe.received_amount
	base = pe.base_paid_amount if kind == "Receive" else pe.base_received_amount
	for one in (
		frappe.qb.from_(pe)
		.select(pe.unallocated_amount, party.as_("amount"), base.as_("base"))
		.where(
			pe.project.isin(projects)
			& (pe.docstatus == 1)
			& (pe.payment_type == kind)
			& (pe.unallocated_amount > 0)
		)
		.run(as_dict=True)
	):
		advance += flt(one.unallocated_amount) * (flt(one.base) / flt(one.amount) if flt(one.amount) else 1)
	route = _route(
		"Payment Entry",
		{
			"payment_type": kind,
			"docstatus": 1,
			"Payment Entry Reference.reference_name": ["in", sorted(mine) + orders],
		}
		if mine or orders
		else {"payment_type": kind, "docstatus": 1, "project": ["in", projects]},
	)
	return {"paid": paid + advance, "owed": owed, "advance": advance, "route": route}


def _journals(projects: list[str]) -> float:
	"""What journal entries charged to the tree's expense accounts: payroll,
	depreciation, accruals."""
	gl = frappe.qb.DocType("GL Entry")
	account = frappe.qb.DocType("Account")
	found = (
		frappe.qb.from_(gl)
		.join(account)
		.on(gl.account == account.name)
		.select(Sum(gl.debit) - Sum(gl.credit))
		.where(
			gl.project.isin(projects)
			& (gl.voucher_type == "Journal Entry")
			& (gl.is_cancelled == 0)
			& (account.root_type == "Expense")
		)
		.run()
	)
	return flt(found[0][0]) if found else 0.0


def _to_invoice(project: str) -> float:
	"""What time and materials has still to invoice, in the company's
	currency: the billable time not invoiced and the costs not billed on,
	with their markup (billing.py)."""
	from onedesk.one_project import billing

	rows = billing._rows(project)
	time = sum(
		flt(one)
		for one in frappe.get_all(
			"Timesheet Detail",
			filters={"name": ["in", [row.name for row in rows] or [""]]},
			pluck="base_billing_amount",
		)
	)
	return time + sum(one["charge"] for one in billing.costs(project))


def _retained(projects: list[str]) -> float:
	"""The customer's retention still held on the tree's invoices
	(retention.py)."""
	from onedesk.one_project import retention

	held = retention.held_on("Sales Invoice", retention.invoices("Sales Invoice", projects))
	return sum(amount for kept in held.values() for _due, amount in kept)


def _suppliers(projects: list[str]) -> list[dict]:
	"""Each order from a supplier on the tree: what it's for, whether it's a
	subcontract or goods (`subcontract`), what's billed, what's left to bill,
	what's received, the retention still held, the advance not yet set off,
	what's been paid, and what's to pay now, by when or how late
	(progress.py, view.past_due)."""
	from onedesk.one_project import retention

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
				"per_received",
			],
		)
	}
	lines = frappe.get_all(
		"Purchase Order Item",
		filters={"parent": ["in", list(orders)]},
		fields=[
			"parent",
			"amount",
			"billed_amt",
			"base_net_amount",
			"item_name",
			"project",
			"item_code",
			"uom",
		],
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
		name: sum(amount for _due, amount in held)
		for name, held in retention.held_on("Purchase Invoice", list(invoices)).items()
	}
	stock = _stock({one.item_code for one in lines if one.item_code})
	terms = _terms("Purchase Invoice", list(invoices))
	# Each supplier's logo (one_mail/faces.py dresses a supplier without one).
	logos = dict(
		frappe.get_all(
			"Supplier",
			filters={"name": ["in", list({one.supplier for one in heads.values()})]},
			fields=["name", "image"],
			as_list=True,
		)
	)
	today = getdate(nowdate())
	found = []
	for name, ordered in orders.items():
		head = heads[name]
		mine = {bill.parent for bill in bills if bill.purchase_order == name}
		billed = sum(flt(bill.base_net_amount) for bill in bills if bill.purchase_order == name)
		left = 0.0 if head.status == "Closed" else unbilled([one for one in lines if one.parent == name])
		retained = paid = advanced = owing = overdue = 0.0
		since = due = None
		for invoice in (invoices[one] for one in mine if one in invoices):
			owed = flt(invoice.outstanding_amount) * flt(invoice.conversion_rate or 1)
			retained += kept.get(invoice.name, 0.0)
			paid += flt(invoice.base_grand_total) - owed
			advanced += flt(invoice.total_advance)
			owing += owed
			late = past_due(terms.get(invoice.name, []), invoice.outstanding_amount, today)
			if late:
				overdue += late["due"] * flt(invoice.conversion_rate or 1)
				since = min(filter(None, [since, str(late["since"])]))
			coming = next_due(terms.get(invoice.name, []), invoice.outstanding_amount, today)
			due = min(filter(None, [due, coming])) if coming else due
		own = [one for one in lines if one.parent == name]
		advance = max(0.0, flt(head.advance_paid) * flt(head.conversion_rate or 1) - advanced)
		found.append(
			{
				"order": name,
				"supplier": head.supplier_name or head.supplier,
				"supplier_id": head.supplier,
				"image": logos.get(head.supplier),
				"for": bought(own),
				"project": head.project or next((one.project for one in own if one.project), None),
				# What's billed and not paid, less the retention held till later.
				"to_pay": max(0.0, owing - retained),
				# What of it is past its date, since when, and when the rest
				# falls due.
				"overdue": overdue,
				"late": (today - getdate(since)).days if since else None,
				"due": due,
				"subcontract": subcontract(own, stock),
				"received": flt(head.per_received),
				"goods": any(one.item_code in stock for one in own),
				"ordered": flt(ordered),
				"billed": billed,
				"left": left,
				"retention": retained,
				"rate": flt(head.one_retention),
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


def subcontract(lines: list, stock: set) -> bool:
	"""Whether an order is a subcontract, a package of work billed as it gets
	done, rather than goods billed as they're received: a line ordered as a
	Lump Sum, or for something that isn't kept in stock. Pure."""
	return any(one.uom == LUMP_SUM or one.item_code not in stock for one in lines)


def next_due(terms: list, outstanding: float, today) -> str | None:
	"""When the next payment on a bill or invoice falls due, retention
	left out: its earliest term not yet paid nor past. Pure."""
	terms = sorted(terms, key=lambda one: str(one["due_date"]))
	paid = max(0.0, sum(flt(one["amount"]) for one in terms) - flt(outstanding))
	for one in terms:
		left = flt(one["amount"]) - min(flt(one["amount"]), paid)
		paid -= min(flt(one["amount"]), paid)
		if left >= 0.005 and not one["held"] and str(one["due_date"]) >= str(today):
			return str(one["due_date"])
	return None


def past_due(terms: list, outstanding: float, today) -> dict | None:
	"""What's past due on one invoice or bill: its payment terms, soonest
	first, with what's been paid taken off the earliest, as payments are;
	what's left of those already due, since when, and whether it's only
	retention. ERPNext's own per-term outstanding moves only when a payment
	names the term, so it's worked out here. None when nothing's due. Pure."""
	terms = sorted(terms, key=lambda one: str(one["due_date"]))
	paid = max(0.0, sum(flt(one["amount"]) for one in terms) - flt(outstanding))
	due, since, held = 0.0, None, True
	for one in terms:
		left = flt(one["amount"]) - min(flt(one["amount"]), paid)
		paid -= min(flt(one["amount"]), paid)
		if left < 0.005 or str(one["due_date"]) >= str(today):
			continue
		due += left
		since = since or one["due_date"]
		held = held and one["held"]
	return {"due": due, "since": since, "held": held} if due >= 0.005 else None


def _terms(doctype: str, names: list[str]) -> dict[str, list[dict]]:
	"""Each invoice's or bill's payment terms, and whether each is retention."""
	from onedesk.one_project import retention

	found: dict = {}
	for one in frappe.get_all(
		"Payment Schedule",
		filters={"parenttype": doctype, "parent": ["in", names or [""]]},
		fields=["parent", "due_date", "payment_amount", "payment_term"],
	):
		found.setdefault(one.parent, []).append(
			{
				"due_date": one.due_date,
				"amount": one.payment_amount,
				"held": one.payment_term in retention.HELD,
			}
		)
	return found


def _stock(items: set) -> set:
	"""Which of the items are kept in stock."""
	return set(
		frappe.get_all(
			"Item", filters={"name": ["in", list(items) or [""]], "is_stock_item": 1}, pluck="name"
		)
	)


def kinds(orders: list[str]) -> dict[str, bool]:
	"""Each order: a subcontract or not (`subcontract`)."""
	lines = frappe.get_all(
		"Purchase Order Item",
		filters={"parent": ["in", orders or [""]]},
		fields=["parent", "item_code", "uom"],
	)
	stock = _stock({one.item_code for one in lines if one.item_code})
	return {name: subcontract([one for one in lines if one.parent == name], stock) for name in orders}


def _placed(orders: list[dict], project: str) -> list[dict]:
	"""Each order with the sub-project it's for, by name, when it isn't the
	page's own project."""
	titles = dict(
		frappe.get_all(
			"Project",
			filters={"name": ["in", [one["project"] for one in orders if one.get("project")] or [""]]},
			fields=["name", "project_name"],
			as_list=True,
		)
	)
	for one in orders:
		one["where"] = (
			titles.get(one["project"]) if one.get("project") and one["project"] != project else None
		)
	return orders


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
