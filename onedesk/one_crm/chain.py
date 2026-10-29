"""Where an opportunity went: the quotations made from it, the sales orders
made from those, and the sales invoices made from the orders, followed
forward since ERPNext links each only to the one before it. How it works is
in the module's AGENTS.md, under chain.py.
"""

import frappe
from erpnext import get_default_company
from frappe.utils import flt


def _may(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def _from(child: str, link: str, parents: list) -> dict[str, set]:
	"""For each paper a child table points back to, the documents pointing."""
	found = {}
	if not parents:
		return found
	for row in frappe.get_all(
		child,
		filters={link: ["in", parents], "docstatus": ["<", 2]},
		fields=["parent", link],
		distinct=True,
	):
		found.setdefault(row[link], set()).add(row.parent)
	return found


def follow(opportunities: list[str]) -> dict[str, frappe._dict]:
	"""For each opportunity: its quotations, orders and invoices, each a list
	of rows, drafts included and cancelled ones left out."""
	out = {name: frappe._dict(quotations=[], orders=[], invoices=[]) for name in opportunities}
	if not opportunities or not _may("Quotation"):
		return out
	quotes = frappe.get_list(
		"Quotation",
		filters={"opportunity": ["in", opportunities], "docstatus": ["<", 2], "company": get_default_company()},
		fields=[
			"name",
			"opportunity",
			"status",
			"docstatus",
			"grand_total",
			"base_grand_total",
			"currency",
			"valid_till",
		],
		order_by="transaction_date desc, creation desc",
		limit=0,
	)
	for one in quotes:
		out[one.opportunity].quotations.append(one)
	if not _may("Sales Order"):
		return out
	ordered = _from("Sales Order Item", "prevdoc_docname", [one.name for one in quotes if one.docstatus == 1])
	names = set().union(*ordered.values()) if ordered else set()
	orders = {
		one.name: one
		for one in frappe.get_list(
			"Sales Order",
			filters={"name": ["in", list(names) or [""]], "docstatus": ["<", 2], "company": get_default_company()},
			fields=[
				"name",
				"status",
				"docstatus",
				"base_grand_total",
				"per_delivered",
				"per_billed",
				"project",
			],
			limit=0,
		)
	}
	billed = {}
	if _may("Sales Invoice"):
		invoiced = _from(
			"Sales Invoice Item", "sales_order", [name for name, one in orders.items() if one.docstatus == 1]
		)
		parents = set().union(*invoiced.values()) if invoiced else set()
		invoices = {
			one.name: one
			for one in frappe.get_list(
				"Sales Invoice",
				filters={
					"name": ["in", list(parents) or [""]],
					"docstatus": ["<", 2],
					"is_return": 0,
					"company": get_default_company(),
				},
				fields=[
					"name",
					"status",
					"docstatus",
					"base_grand_total",
					"outstanding_amount",
					"conversion_rate",
					"party_account_currency",
					"currency",
					"posting_date",
				],
				limit=0,
			)
		}
		billed = {
			order: [invoices[name] for name in sorted(made) if name in invoices]
			for order, made in invoiced.items()
		}
	for quote in quotes:
		chain = out[quote.opportunity]
		for name in sorted(ordered.get(quote.name, ())):
			if name in orders and orders[name] not in chain.orders:
				chain.orders.append(orders[name])
				for invoice in billed.get(name, []):
					if invoice not in chain.invoices:
						chain.invoices.append(invoice)
	return out


def owed(invoice) -> float:
	"""What an invoice still owes, in the company's currency. ERPNext keeps it
	in the party's account currency."""
	from erpnext import get_company_currency

	amount = flt(invoice.outstanding_amount)
	ours = get_company_currency(get_default_company())
	if invoice.party_account_currency and invoice.party_account_currency != ours:
		amount *= flt(invoice.conversion_rate or 1)
	return amount


def reached(chain) -> list[str]:
	"""How far an opportunity has got, as the papers it has: submitted ones
	only, then Paid once every invoice is. Pure over follow()'s rows."""
	got = ["Opportunity"]
	if any(one.docstatus == 1 for one in chain.quotations):
		got.append("Quotation")
	if any(one.docstatus == 1 for one in chain.orders):
		got.append("Sales Order")
	sent = [one for one in chain.invoices if one.docstatus == 1]
	if sent:
		got.append("Sales Invoice")
		if all(flt(one.outstanding_amount) <= 0 for one in sent):
			got.append("Paid")
	return got
