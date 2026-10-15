"""What OneAI does in OneBook: reads how the money stands, who owes and is
owed and how late, one invoice with what settled it, and the bank lines left
to match, all as the reader may see them. It changes nothing in the books;
the README's Under the hood lists each tool.
"""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import flt, getdate, nowdate

from onedesk.one_book import home, story

#: OneBook's Home (page/books).
HOME = "books"

#: What a suggestion's permission is checked on: OneBook makes none of them.
SALES, BUYING, LEDGER = "Sales Invoice", "Purchase Invoice", "GL Entry"

#: The kinds of invoice invoice_facts reads, by the party each is with.
PARTY = {SALES: "customer", BUYING: "supplier"}

_MONEY = {
	"label": _lt("How is the money doing?"),
	"ask": _lt(
		"How is the money doing? Say what is in the bank, what customers owe and how much of it is late, what we "
		"owe and what falls due this week, and how profit went this month against the months before."
	),
	"can": "read",
	"doctype": LEDGER,
	"expects": "money_now",
}

_OWED = {
	"label": _lt("Who owes us the most, and how late?"),
	"ask": _lt("Which customers owe us the most, how much of it is late and by how long?"),
	"can": "read",
	"doctype": SALES,
	"expects": "late_invoices",
}

_OVERDUE = {
	"label": _lt("Which invoices are overdue?"),
	"ask": _lt("Which sales invoices are overdue, to whom, for how much, and since when?"),
	"can": "read",
	"view": "List",
	"expects": "late_invoices",
}

_TO_PAY = {
	"label": _lt("What do we have to pay this week?"),
	"ask": _lt("Which purchase invoices fall due this week or are already late, to whom and for how much?"),
	"can": "read",
	"doctype": BUYING,
	"expects": "late_invoices",
}

_STANDS = {
	"label": _lt("Where does this invoice stand?"),
	"ask": _lt(
		"Where does this invoice stand? Say what is still owed, what is late, and which payments and credit notes settled the rest."
	),
	"can": "read",
	"view": "Form",
	"expects": "invoice_facts",
}

_REMIND = {
	"label": _lt("Draft a payment reminder"),
	"ask": _lt(
		"Draft a short, polite email to the customer asking them to pay what is still owed on this invoice, "
		"saying how much, since when it was due, and how to pay. Plain words, no threats."
	),
	"can": "read",
	"view": "Form",
	"expects": "invoice_facts",
}

_PARTY_OWES = {
	"label": _lt("What do they owe, and how late?"),
	"ask": _lt("What does this customer owe us, on which invoices, and how late is each?"),
	"can": "read",
	"view": "Form",
	"doctype": SALES,
	"expects": "late_invoices",
}

_TO_MATCH = {
	"label": _lt("Which bank lines are still to match?"),
	"ask": _lt("Which bank lines are still to be matched, in which accounts, and for how much?"),
	"can": "read",
	"expects": "bank_to_match",
}

SUGGESTIONS = {
	f"page:{HOME}": [_MONEY, _OWED, _TO_PAY],
	"Sales Invoice": [_OVERDUE, _STANDS, _REMIND],
	"Purchase Invoice": [{**_TO_PAY, "view": "List"}, _STANDS],
	"Customer": [_PARTY_OWES],
	"Bank Transaction": [_TO_MATCH],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on OneBook's Home."""
	if said.get("page") != HOME:
		return None
	return (
		"The reader is on OneBook's Home, which shows cash, what customers owe and how much is late, what is "
		"owed to suppliers and falls due this week, this month's profit, cash flow, profit and loss, the "
		"largest expenses, how old the debts are, and today's overdue invoices, bills due, bank lines to match "
		"and drafts left. money_now, late_invoices and bank_to_match read those; how each part works is in "
		"OneBook's documentation (how_to)."
	)


def money_now() -> dict:
	"""How the money stands, as OneBook's Home shows it: cash, what customers
	owe and how much is late, what is owed and falls due this week, this
	month's profit, each with its months, and how old the debts are."""
	told = story.read()
	if not told["cards"]:
		return {"error": "The reader may not see the books."}
	months = told["months"]
	return {
		"currency": told["currency"],
		"months": months,
		"figures": {
			key: {"now": one["value"], **({"by_month": one["series"]} if one.get("series") else {})}
			for key, one in told["cards"].items()
		},
		"receivable": _side(told.get("receivable")),
		"payable": _side(told.get("payable")),
		"largest_expenses": (told.get("money") or {}).get("expenses"),
	}


def _side(said: dict | None) -> dict | None:
	if not said:
		return None
	return {"by_age": said["ages"], "most_owed": said["parties"], "this_year_by_status": said["statuses"]}


def late_invoices(
	kind: Annotated[
		str, "Sales Invoice for what customers owe, Purchase Invoice for what we owe."
	] = "Sales Invoice",
	party: Annotated[str, "Only this customer's or supplier's, by name."] | None = None,
) -> dict:
	"""Every invoice with something late, or for bills also due this week, the
	oldest first: to or from whom, how much is still owed, since when and how
	late, as ERPNext's Overdue counts it from the payment schedule."""
	if kind not in PARTY:
		return {"error": "Ask for Sales Invoice or Purchase Invoice."}
	if not frappe.has_permission(kind, "read"):
		return {"error": f"The reader may not see {kind}."}
	day = getdate(nowdate())
	until = home.yesterday() if kind == "Sales Invoice" else home.this_week()
	rows = home._late(kind, PARTY[kind], until, day)
	if party:
		rows = [one for one in rows if party in (one["party"] or "")]
	return {
		"kind": kind,
		"invoices": [
			{
				"invoice": one["name"],
				"party": one["party"],
				"still_owed": one["outstanding"],
				"currency": one["currency"],
				"due": one["due_date"],
				"late_by_days": max(one["late"], 0),
			}
			for one in rows
		],
		"count": len(rows),
	}


def invoice_facts(
	invoice: Annotated[str, "The sales or purchase invoice, such as ACC-SINV-2026-00004."],
) -> dict:
	"""One invoice as its page says it: whom it is with, what it came to, what is
	still owed and when each part falls due, and the payments and credit notes
	that settled the rest."""
	kind = next((one for one in PARTY if frappe.db.exists(one, invoice)), None)
	if not kind:
		return {"error": f"There is no invoice {invoice}."}
	doc = frappe.get_doc(kind, invoice)
	if not doc.has_permission("read"):
		return {"error": f"The reader may not see {invoice}."}
	schedule = home._schedule(kind, [doc.name]).get(doc.name)
	owed = home.parts({"outstanding_amount": doc.outstanding_amount, "due_date": doc.due_date}, schedule)
	settled = frappe.get_all(
		"Payment Entry Reference",
		filters={"reference_doctype": kind, "reference_name": doc.name, "docstatus": 1},
		fields=["parent", "allocated_amount"],
	)
	returns = frappe.get_all(
		kind,
		filters={"return_against": doc.name, "docstatus": 1},
		fields=["name", "grand_total", "posting_date"],
	)
	return {
		"invoice": doc.name,
		"kind": kind,
		"party": doc.get(f"{PARTY[kind]}_name") or doc.get(PARTY[kind]),
		"status": doc.status,
		"posted": str(doc.posting_date),
		"grand_total": flt(doc.grand_total),
		"currency": doc.currency,
		"still_owed": flt(doc.outstanding_amount),
		"falls_due": [
			{"due": str(one["due_date"]), "amount": flt(one["outstanding_amount"])}
			for one in owed
			if flt(one["outstanding_amount"]) > 0
		],
		"payments": [{"payment": one.parent, "amount": flt(one.allocated_amount)} for one in settled],
		"credit_notes": [
			{"note": one.name, "amount": flt(one.grand_total), "on": str(one.posting_date)} for one in returns
		],
		"project": doc.get("project"),
	}


def bank_to_match() -> dict:
	"""The bank lines not yet matched to what is in the books, by account."""
	if not frappe.has_permission("Bank Transaction", "read"):
		return {"error": "The reader may not see bank transactions."}
	said = home._bank()
	return {"accounts": said["rows"], "lines": said["count"]}
