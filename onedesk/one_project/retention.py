"""Retention: a share of each invoice held back and paid later, as contractors
are paid. ERPNext has none of its own, so it's built of ERPNext's parts, held
in the invoice's payment terms or, taxed when released, in Retention lines
(the README's Under the hood). progress.py makes and keeps both.
"""

from typing import Annotated

import frappe
from frappe import _
from frappe.utils import add_days, add_months, flt, getdate, nowdate

#: The payment terms retention is held under: the part released at handover,
#: and the rest.
HANDOVER = "Retention at Handover"
RETENTION = "Retention"
HELD = (HANDOVER, RETENTION)

#: How far ahead a customer's retention is in Needs You.
AHEAD = 30

#: When tax on retention is charged: with the invoice that holds it, or by
#: the invoice that releases it.
WITH_INVOICE = "With the Invoice"
WHEN_RELEASED = "When Released"

#: Where retention is taxed when it's released, so a new workspace there
#: starts that way: the UAE (the FTA's guide) and the UK (a retention's tax
#: point is its payment or its invoice).
RELEASED_IN = ("United Arab Emirates", "United Kingdom")

#: Where tax on retention falls due on its own, so many months after the
#: work is certified complete, invoiced or not: the UAE (the FTA's guide).
TAXED_AFTER = {"United Arab Emirates": 12}

#: The item a Retention line is, held or released.
ITEM = "Retention"

#: Where retention held waits when it's taxed on release: the customer's in
#: an asset, the supplier's in a liability, each beside the party accounts.
ACCOUNTS = {
	"Sales Invoice": ("Retention Receivable", "Receivable", "income_account"),
	"Purchase Invoice": ("Retention Payable", "Payable", "expense_account"),
}


def on() -> bool:
	"""Whether the workspace holds retention."""
	return bool(frappe.db.get_single_value("Projects Settings", "one_retention"))


def when_released() -> bool:
	"""Whether retention is taxed by the invoice that releases it."""
	return on() and frappe.db.get_single_value("Projects Settings", "one_retention_tax") == WHEN_RELEASED


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


def held_on(doctype: str, names: list[str], owed: bool | None = None) -> dict[str, list[tuple[str, float]]]:
	"""Each invoice's retention still held, in the company's currency, as
	(due, amount), soonest first. Held in its payment terms, the retention is
	part of what the invoice owes; held in Retention lines, it isn't invoiced
	yet. `owed` asks for only the first (True) or only the second (False)."""
	if not names:
		return {}
	found = {} if owed is False else _scheduled(doctype, names)
	if owed is not True:
		found.update(withheld(doctype, names))
	return found


def _scheduled(doctype: str, names: list[str]) -> dict[str, list[tuple[str, float]]]:
	"""Retention held in payment terms: each term less what was paid against
	it (Release Retention), and no more than the invoice still owes
	(`still_held`)."""
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


def withheld(doctype: str, names: list[str]) -> dict[str, list[tuple[str, float]]]:
	"""Retention held in Retention lines, less what the invoices releasing it
	have invoiced, the soonest due first (`still_held`)."""
	found = {}
	for row in frappe.get_all(
		f"{doctype} Item",
		filters={"parent": ["in", names], "one_held": ["is", "set"], "docstatus": 1},
		fields=["parent", "one_release_on", "base_net_amount"],
	):
		found.setdefault(row.parent, []).append((row.one_release_on, -flt(row.base_net_amount)))
	# A credit note's Retention lines give back what its invoice held.
	for name in frappe.get_all(doctype, filters={"name": ["in", list(found) or [""]], "is_return": 1}, pluck="name"):
		del found[name]
	if not found:
		return {}
	released = {}
	head = frappe.qb.DocType(doctype)
	line = frappe.qb.DocType(f"{doctype} Item")
	for against, amount in (
		frappe.qb.from_(line)
		.join(head)
		.on(head.name == line.parent)
		.select(head.return_against, line.base_net_amount)
		.where((head.docstatus == 1) & (head.is_return == 1) & head.return_against.isin(list(found)) & (line.one_held != ""))
		.run()
	):
		# Below nothing on the invoice, above it on its credit note.
		released[against] = released.get(against, 0.0) + flt(amount)
	for row in frappe.get_all(
		f"{doctype} Item",
		filters={"one_retention_of": ["in", list(found)], "docstatus": 1},
		fields=["one_retention_of", "base_net_amount"],
	):
		released[row.one_retention_of] = released.get(row.one_retention_of, 0.0) + flt(row.base_net_amount)
	return {
		name: still_held(held, sum(amount for _due, amount in held) - released.get(name, 0.0))
		for name, held in found.items()
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
	to ask them for, after any whose tax falls due first (`tax_asks`)."""
	if not on() or not frappe.has_permission("Sales Invoice", "read"):
		return []
	taxed = tax_asks(projects, user)
	names = invoices("Sales Invoice", projects)
	held = held_on("Sales Invoice", names)
	if not held:
		return taxed
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
	return taxed + found


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


def taxed_by(project: str) -> str | None:
	"""When tax on the retention held on a project falls due whether it's
	invoiced or not, where the law says so: so many months after the work
	was completed."""
	done, company = frappe.db.get_value("Project", project, ["one_completed_on", "company"]) or (None, None)
	months = TAXED_AFTER.get(frappe.get_cached_value("Company", company, "country")) if company else None
	return str(add_months(done, months)) if done and months else None


def tax_asks(projects: list[str], user: str) -> list[dict]:
	"""Needs You: retention held in Retention lines on a project whose tax
	falls due within a month, invoiced or not, to be invoiced before then."""
	names = invoices("Sales Invoice", projects)
	held = withheld("Sales Invoice", names)
	if not any(held.values()):
		return []
	today = getdate(nowdate())
	found = []
	for one in frappe.get_all(
		"Sales Invoice",
		filters={"name": ["in", [name for name, kept in held.items() if kept]]},
		fields=["name", "customer_name", "owner", "project"],
	):
		project = one.project or frappe.db.get_value("Sales Invoice Item", {"parent": one.name, "project": ["is", "set"]}, "project")
		by = project and taxed_by(project)
		if not by or by > str(add_days(today, AHEAD)):
			continue
		days = (getdate(by) - today).days
		found.append(
			{
				"tone": "red" if days < 0 else "orange",
				"text": _("Invoice the retention from {0} before its tax falls due").format(one.customer_name),
				"dim": " · ".join(filter(None, [when(days), _("You") if one.owner == user else None])),
				"money": sum(amount for _due, amount in held[one.name]),
				"route": f"/desk/sales-invoice/{one.name}",
				"mine": one.owner == user,
			}
		)
	return found


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
	"""Release Retention (Pay Retention for a supplier): what releases the
	retention still held on the project's invoices, for the parts due by
	today, or all of it when none is due yet. Held in payment terms, that's a
	draft Payment Entry matched to each invoice's retention terms, so ERPNext
	marks those parts paid; held in Retention lines, it's a draft invoice for
	the retention, with its tax (`released`). Nothing is saved."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	from onedesk.one_project import tree

	if doctype not in ("Sales Invoice", "Purchase Invoice"):
		frappe.throw(_("Retention is held on sales and purchase invoices."))
	frappe.has_permission("Project", "read", project, throw=True)
	key = "customer" if doctype == "Sales Invoice" else "supplier"
	names = [invoice] if invoice else invoices(doctype, sorted(tree.scope(project)))
	today = str(getdate(nowdate()))
	lines = withheld(doctype, names)
	if any(lines.values()):
		return released(doctype, project, lines, key, party, today)
	frappe.has_permission("Payment Entry", "create", throw=True)
	filters = {"name": ["in", names or [""]], "docstatus": 1, "outstanding_amount": [">", 0]}
	if party:
		filters[key] = party
	heads = frappe.get_list(
		doctype,
		filters=filters,
		fields=["name", f"{key} as party", "currency", "party_account_currency", "company", "conversion_rate", "outstanding_amount"],
		order_by="posting_date asc, creation asc",
	)
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
	_one_party(doctype, {head.party for head, _left in found.values()})
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


def _one_party(doctype: str, parties: set) -> None:
	if len(parties) > 1:
		frappe.throw(
			_("More than one customer holds retention here. Release it from each invoice.")
			if doctype == "Sales Invoice"
			else _("More than one supplier has retention held here. Pay it from each bill.")
		)


def released(doctype: str, project: str, lines: dict, key: str, party: str | None, today: str):
	"""Retention taxed when it's released: a draft invoice (or bill) for what
	the invoices still hold, one Retention line for each, taxed as the first
	of them was. Paying it is then an ordinary payment."""
	frappe.has_permission(doctype, "create", throw=True)
	heads = {
		one.name: one
		for one in frappe.get_list(
			doctype,
			filters={"name": ["in", list(lines)], "docstatus": 1, **({key: party} if party else {})},
			fields=["name", f"{key} as party", "conversion_rate", "posting_date"],
			order_by="posting_date asc, creation asc",
		)
	}
	_one_party(doctype, {head.party for head in heads.values()})
	chosen = picked([(name, None, due, amount) for name, held in lines.items() if name in heads for due, amount in held], today)
	if not chosen:
		frappe.throw(_("No retention is held here."))
	first = frappe.get_doc(doctype, chosen[0][0])
	made = frappe.new_doc(doctype)
	for field in (key, "company", "currency", "conversion_rate", "taxes_and_charges", "cost_center", "project"):
		if first.get(field) is not None:
			made.set(field, first.get(field))
	made.project = project
	made.one_retention = 0
	# One line for each invoice, its parts together.
	owed: dict[str, float] = {}
	for name, _term, _due, amount in chosen:
		owed[name] = owed.get(name, 0.0) + amount
	for name, amount in owed.items():
		made.append(
			"items",
			{
				"item_code": ITEM,
				"qty": 1,
				# Held in the company's currency; the invoice is in the customer's.
				"rate": flt(amount / flt(heads[name].conversion_rate or 1), 2),
				"description": _("Retention held on {0}").format(name),
				"one_retention_of": name,
				"project": project,
			},
		)
	for tax in first.get("taxes") or []:
		made.append(
			"taxes",
			{
				field: tax.get(field)
				for field in (
					"charge_type",
					"account_head",
					"description",
					"rate",
					"cost_center",
					"included_in_print_rate",
					"category",
					"add_deduct_tax",
				)
				if tax.get(field) is not None
			},
		)
	made.run_method("set_missing_values")
	book(made)
	made.run_method("calculate_taxes_and_totals")
	return made


def handed_over(doc, method=None) -> None:
	"""Project on_update: marked Completed, the project is completed today
	unless somebody said otherwise, and the retention released at handover
	falls due on every invoice made from its orders."""
	if doc.status != "Completed" or not doc.has_value_changed("status"):
		return
	today = getdate(nowdate())
	if not doc.get("one_completed_on"):
		doc.db_set("one_completed_on", today, update_modified=False)
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
			frappe.db.set_value(
				f"{invoice_type} Item",
				{"parent": invoice, "one_held": HANDOVER, "one_release_on": [">", today]},
				"one_release_on",
				today,
			)


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
			| set(
				frappe.get_all(
					f"{doctype} Item",
					filters={"one_held": ["is", "set"], "one_release_on": today, "docstatus": 1},
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


def account(company: str, doctype: str) -> str:
	"""Retention Receivable (or Payable) for the company, made beside its
	debtors' (or creditors') account the first time it's asked for. It isn't
	a party account: what's held is owed by nobody yet."""
	name, near, _field = ACCOUNTS[doctype]
	found = frappe.db.get_value("Account", {"company": company, "account_name": name, "is_group": 0})
	if found:
		return found
	parent = frappe.db.get_value("Account", {"company": company, "account_type": near, "is_group": 0}, "parent_account")
	if not parent:
		frappe.throw(_("{0} has no account for its {1} to put {2} beside.").format(company, _(near), _(name)))
	return (
		frappe.get_doc(
			{"doctype": "Account", "account_name": name, "parent_account": parent, "company": company, "account_type": ""}
		)
		.insert(ignore_permissions=True)
		.name
	)


def book(doc) -> None:
	"""A Retention line, held or released, is booked to the retention
	account, whatever the item's defaults say."""
	field = ACCOUNTS[doc.doctype][2]
	for row in doc.get("items") or []:
		if row.item_code == ITEM or row.get("one_held"):
			row.set(field, account(doc.company, doc.doctype))


def ready(doc=None, method=None) -> None:
	"""Projects Settings on_update, and every migrate: Tax on Retention starts
	as the company's country does it, and taxed when released, the Retention
	item is there and a Retention line may be below nothing, which ERPNext
	allows only when Selling and Buying Settings say so."""
	settings = frappe.get_single("Projects Settings")
	if not settings.get("one_retention_tax"):
		company = frappe.defaults.get_global_default("company") or frappe.db.get_value("Company", {})
		country = company and frappe.db.get_value("Company", company, "country")
		frappe.db.set_single_value(
			"Projects Settings", "one_retention_tax", WHEN_RELEASED if country in RELEASED_IN else WITH_INVOICE
		)
	if not when_released():
		return
	if not frappe.db.exists("Item", ITEM):
		group = frappe.db.exists("Item Group", "Services") or frappe.db.get_value("Item Group", {"is_group": 0})
		unit = frappe.db.exists("UOM", "Nos") or frappe.db.get_value("Stock Settings", None, "stock_uom") or "Unit"
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": ITEM,
				"item_name": ITEM,
				"item_group": group,
				"stock_uom": unit,
				"is_stock_item": 0,
				"is_sales_item": 1,
				"is_purchase_item": 1,
				"include_item_in_manufacturing": 0,
				"description": "Held back from an invoice, and released by one of its own.",
			}
		).insert(ignore_permissions=True)
	for settings_doctype in ("Selling Settings", "Buying Settings"):
		if not frappe.db.get_single_value(settings_doctype, "allow_negative_rates_for_items"):
			frappe.db.set_single_value(settings_doctype, "allow_negative_rates_for_items", 1)
