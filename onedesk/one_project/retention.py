"""Retention: a share of each invoice held back and paid later, as contractors
are paid. ERPNext has none of its own, so it's built of ERPNext's parts: the
invoice is for the whole amount, and its payment schedule holds the retention
as later payment terms (progress.py makes and keeps them).
"""

from typing import Annotated

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
	"""Each invoice's retention still held, in the company's currency: each
	retention term less what was paid against it (Release Retention), and
	no more than the invoice still owes (`still_held`)."""
	if not names:
		return {}
	found = {}
	for row in frappe.get_all(
		"Payment Schedule",
		filters={"parent": ["in", names], "parenttype": doctype, "payment_term": ["in", HELD]},
		fields=["parent", "due_date", "base_payment_amount", "base_outstanding"],
	):
		left = row.base_outstanding if row.base_outstanding is not None else row.base_payment_amount
		found.setdefault(row.parent, []).append((row.due_date, flt(left)))
	if not found:
		return {}
	return {
		one.name: still_held(found[one.name], _base(one))
		for one in frappe.get_all(
			doctype,
			filters={"name": ["in", list(found)], "docstatus": 1},
			fields=["name", "company", "outstanding_amount", "conversion_rate", "party_account_currency"],
		)
	}


def _base(invoice) -> float:
	"""What an invoice still owes, in the company's currency. ERPNext keeps
	it in the party account's currency."""
	company = frappe.get_cached_value("Company", invoice.company, "default_currency")
	rate = 1 if invoice.party_account_currency in (None, "", company) else flt(invoice.conversion_rate or 1)
	return flt(invoice.outstanding_amount) * rate


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


def ordered(doc, method=None) -> None:
	"""Sales Order before_insert: a customer's order on a project starts
	with the project's retention, which the order may change (0 on extra
	work, say). A subcontract's purchase order keeps its own."""
	project = doc.get("project")
	if not project or doc.get("one_retention") is not None or not on():
		return
	found = frappe.db.get_value(
		"Project", project, ["one_retention", "one_retention_due", "one_retention_handover"], as_dict=True
	)
	if not found or not flt(found.one_retention):
		return
	doc.update(
		{
			"one_retention": found.one_retention,
			"one_retention_due": doc.get("one_retention_due") or found.one_retention_due,
			"one_retention_handover": found.one_retention_handover,
		}
	)


def picked(parts: list[tuple], today: str) -> list[tuple]:
	"""Which held parts, as (invoice, term, due, amount), a payment is for:
	those due by today, or all of them when none is due yet. Pure."""
	due = [one for one in parts if str(one[2]) <= str(today)]
	return due or parts


@frappe.whitelist()
def release(
	project: Annotated[str, "The project."],
	doctype: Annotated[str, "Sales Invoice to release a customer's, Purchase Invoice to pay a supplier's."] = "Sales Invoice",
	invoice: Annotated[str | None, "Only this invoice."] = None,
	party: Annotated[str | None, "Only this customer's or supplier's."] = None,
):
	"""Release Retention (Pay Retention for a supplier): a draft Payment
	Entry for the retention still held on the project's invoices, matched to
	each invoice's retention terms, so ERPNext marks those parts paid. It's
	for the parts due by today, or all of it when none is due yet. Nothing
	is saved."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from onedesk.one_project import tree

	if doctype not in ("Sales Invoice", "Purchase Invoice"):
		frappe.throw(_("Retention is held on sales and purchase invoices."))
	frappe.has_permission("Project", "read", project, throw=True)
	frappe.has_permission("Payment Entry", "create", throw=True)
	key = "customer" if doctype == "Sales Invoice" else "supplier"
	names = [invoice] if invoice else invoices(doctype, sorted(tree.scope(project)))
	filters = {"name": ["in", names or [""]], "docstatus": 1, "outstanding_amount": [">", 0]}
	if party:
		filters[key] = party
	heads = frappe.get_list(
		doctype,
		filters=filters,
		fields=["name", f"{key} as party", "currency", "party_account_currency", "company", "conversion_rate", "outstanding_amount"],
		order_by="posting_date asc, creation asc",
	)
	today = str(getdate(nowdate()))
	found = {}
	for head in heads:
		own = head.party_account_currency == head.currency
		rows = frappe.get_all(
			"Payment Schedule",
			filters={"parent": head.name, "parenttype": doctype, "payment_term": ["in", HELD]},
			fields=["payment_term", "due_date", "outstanding", "base_outstanding"],
			order_by="due_date asc",
		)
		# In the party account's currency, as ERPNext matches a payment.
		amount = {str(row.due_date): flt(row.outstanding if own else row.base_outstanding) for row in rows}
		term = {str(row.due_date): row.payment_term for row in rows}
		left = [(term[due], due, held) for due, held in still_held(list(amount.items()), head.outstanding_amount)]
		if left:
			found[head.name] = (head, left)
	if not found:
		frappe.throw(_("No retention is held here."))
	if len({head.party for head, _left in found.values()}) > 1:
		frappe.throw(
			_("More than one customer holds retention here. Release it from each invoice.")
			if doctype == "Sales Invoice"
			else _("More than one supplier has retention held here. Pay it from each bill.")
		)
	chosen = picked([(name, *one) for name, (_head, left) in found.items() for one in left], today)
	total = flt(sum(amount for *_rest, amount in chosen), 2)
	payment = get_payment_entry(doctype, chosen[0][0], party_amount=total)
	payment.set("references", [])
	for name, term, due, amount in chosen:
		head = found[name][0]
		payment.append(
			"references",
			{
				"reference_doctype": doctype,
				"reference_name": name,
				"payment_term": term,
				"due_date": due,
				"outstanding_amount": head.outstanding_amount,
				"payment_term_outstanding": flt(amount, 2),
				"allocated_amount": flt(amount, 2),
			},
		)
	payment.project = project
	payment.set_missing_ref_details()
	payment.set_amounts()
	return payment


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
