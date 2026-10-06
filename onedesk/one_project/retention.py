"""Retention: a share of each invoice held back and paid later, as contractors
are paid. ERPNext has none of its own, so it's built of ERPNext's parts: the
invoice is for the whole amount, and its payment schedule holds the retention
as later payment terms (progress.py makes and keeps them).
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

#: The payment terms retention is held under: the part released at handover,
#: and the rest.
HANDOVER = "Retention at Handover"
RETENTION = "Retention"
HELD = (HANDOVER, RETENTION)

#: How far ahead a customer's retention is in Needs You.
AHEAD = 30


def on() -> bool:
	"""Whether the workspace holds retention."""
	return bool(frappe.db.get_single_value("Projects Settings", "one_retention"))


def boot(bootinfo) -> None:
	"""The desk hides the retention fields while it's off."""
	bootinfo["one_retention"] = on()


def parts(share: float, handover: float) -> list[tuple[str | None, float]]:
	"""An invoice's payment in parts, out of 100: the rest now, what's
	released at handover and the rest of the retention, those with nothing
	left out. Pure."""
	first = flt(share) * min(100.0, max(0.0, flt(handover))) / 100
	found = [(None, 100 - flt(share)), (HANDOVER, first), (RETENTION, flt(share) - first)]
	return [(term, portion) for term, portion in found if portion > 0]


def still_held(held: list[tuple], outstanding: float) -> list[tuple[str, float]]:
	"""What's still held on one invoice, part by part, soonest first, as
	(due, amount). Retention is paid last, so it's no more than what's left
	to pay, and its earlier part is paid before its later one. Pure."""
	held = sorted((str(due), flt(amount)) for due, amount in held)
	paid = max(0.0, sum(amount for _due, amount in held) - max(0.0, flt(outstanding)))
	left = []
	for due, amount in held:
		taken = min(amount, paid)
		paid -= taken
		if amount - taken >= 0.005:
			left.append((due, amount - taken))
	return left


def held_on(doctype: str, names: list[str]) -> dict[str, list[tuple[str, float]]]:
	"""Each invoice's retention still held, in the company's currency."""
	if not names:
		return {}
	found = {}
	for row in frappe.get_all(
		"Payment Schedule",
		filters={"parent": ["in", names], "parenttype": doctype, "payment_term": ["in", HELD]},
		fields=["parent", "due_date", "base_payment_amount"],
	):
		found.setdefault(row.parent, []).append((row.due_date, flt(row.base_payment_amount)))
	if not found:
		return {}
	return {
		one.name: still_held(found[one.name], flt(one.outstanding_amount) * flt(one.conversion_rate or 1))
		for one in frappe.get_all(
			doctype,
			filters={"name": ["in", list(found)], "docstatus": 1},
			fields=["name", "outstanding_amount", "conversion_rate"],
		)
	}


def invoices(doctype: str, projects: list[str]) -> list[str]:
	"""The submitted invoices with a line on the projects."""
	return list(
		set(
			frappe.get_all(
				f"{doctype} Item", filters={"project": ["in", projects], "docstatus": 1}, pluck="parent"
			)
		)
	)


def side(held: list[tuple[str, float]], rates: set) -> dict | None:
	"""One side of the Overview's Retention: what's held, the rate when the
	orders agree, and when the first of it is due. Pure."""
	held = [one for one in held if one[1] >= 0.005]
	if not held:
		return None
	return {
		"held": sum(amount for _due, amount in held),
		"percent": next(iter(rates)) if len(rates) == 1 else None,
		"due": min(due for due, _amount in held),
	}


def sides(projects: list[str], ordered: list[dict], suppliers: list[dict]) -> dict | None:
	"""What the customer holds and what's held from suppliers on the tree."""
	found = {}
	for key, doctype, rates in (
		("customer", "Sales Invoice", {one["retention"] for one in ordered if one["retention"]}),
		("suppliers", "Purchase Invoice", {one["rate"] for one in suppliers if one.get("rate")}),
	):
		held = [part for one in held_on(doctype, invoices(doctype, projects)).values() for part in one]
		said = side(held, rates)
		if said:
			found[key] = said
	return found or None


def when(days: int) -> str:
	"""When retention is due, in plain words."""
	if days < 0:
		return _("1 day late") if days == -1 else _("{0} days late").format(-days)
	if days == 0:
		return _("Due today")
	return _("Due tomorrow") if days == 1 else _("Due in {0} days").format(days)


def asks(projects: list[str], user: str) -> list[dict]:
	"""Needs You: each customer's retention due within a month or past due,
	to ask them for."""
	if not on() or not frappe.has_permission("Sales Invoice", "read"):
		return []
	names = invoices("Sales Invoice", projects)
	held = held_on("Sales Invoice", names)
	if not held:
		return []
	heads = {
		one.name: one
		for one in frappe.get_all(
			"Sales Invoice", filters={"name": ["in", list(held)]}, fields=["name", "customer_name", "owner"]
		)
	}
	today = getdate(nowdate())
	horizon = str(add_days(today, AHEAD))
	found = []
	for name, kept in held.items():
		near = [(due, amount) for due, amount in kept if due <= horizon]
		if not near or name not in heads:
			continue
		days = (getdate(near[0][0]) - today).days
		head = heads[name]
		found.append(
			{
				"tone": "red" if days < 0 else "orange",
				"text": _("Ask for retention from {0}").format(head.customer_name),
				"dim": " · ".join(filter(None, [when(days), _("You") if head.owner == user else None])),
				"money": sum(amount for _due, amount in near),
				"route": f"/desk/sales-invoice/{name}",
				"mine": head.owner == user,
				"days": days,
			}
		)
	found.sort(key=lambda one: one["days"])
	for one in found:
		del one["days"]
	return found


def handed_over(doc, method=None) -> None:
	"""Project on_update: marked Completed, the retention released at
	handover falls due on every invoice made from its orders."""
	if doc.status != "Completed" or not doc.has_value_changed("status"):
		return
	today = getdate(nowdate())
	for order_type, invoice_type, link in (
		("Sales Order", "Sales Invoice", "sales_order"),
		("Purchase Order", "Purchase Invoice", "purchase_order"),
	):
		orders = set(
			frappe.get_all(
				f"{order_type} Item", filters={"project": doc.name, "docstatus": 1}, pluck="parent"
			)
		)
		if not orders:
			continue
		for invoice in set(
			frappe.get_all(
				f"{invoice_type} Item", filters={link: ["in", list(orders)], "docstatus": 1}, pluck="parent"
			)
		):
			for row in frappe.get_all(
				"Payment Schedule",
				filters={"parent": invoice, "parenttype": invoice_type, "payment_term": HANDOVER},
				fields=["name", "due_date"],
			):
				if getdate(row.due_date) > today:
					frappe.db.set_value("Payment Schedule", row.name, "due_date", today)


def due() -> None:
	"""Daily: retention falling due today, on either side, is told to the
	manager of its project (Retention Due)."""
	if not on():
		return
	from onedesk.one_project import tell

	today = str(getdate(nowdate()))
	for doctype, party in (("Sales Invoice", "customer_name"), ("Purchase Invoice", "supplier_name")):
		names = list(
			set(
				frappe.get_all(
					"Payment Schedule",
					filters={"parenttype": doctype, "payment_term": ["in", HELD], "due_date": today},
					pluck="parent",
				)
			)
		)
		for name, kept in held_on(doctype, names).items():
			amount = sum(value for when_, value in kept if when_ == today)
			if not amount:
				continue
			head = frappe.db.get_value(doctype, name, [party, "company", "project"], as_dict=True)
			project = head.project or frappe.db.get_value(
				f"{doctype} Item", {"parent": name, "project": ["is", "set"]}, "project"
			)
			if not project:
				continue
			tell.retention_due(doctype, name, project, amount, head.company, head.get(party))
