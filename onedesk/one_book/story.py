"""OneBook's Home, told as a story (page/books, frontend/src/books): the
headline figures with their months, then cash and profit, what customers owe
and what is owed to suppliers. Frappe Books' dashboard (Cashflow, Profit and
Loss, Top expenses) over ERPNext's ledger, for the reader's company, in its
currency, as the reader may see it. How it works is in the module's AGENTS.md.
"""

import calendar
from collections import defaultdict
from datetime import date

import frappe
from frappe.utils import add_months, date_diff, flt, getdate, today

from onedesk.one_book import home

MONTHS = 12

TOP = 5

PARTIES = 8

RANGES = (30, 60, 90, 120)


def _may(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def _months() -> list[date]:
	start = getdate(today()).replace(day=1)
	return [getdate(add_months(start, -back)) for back in range(MONTHS - 1, -1, -1)]


def _month(day) -> str:
	return getdate(day).replace(day=1).isoformat()


def _end(month: date) -> date:
	return month.replace(day=calendar.monthrange(month.year, month.month)[1])


@frappe.whitelist()
@frappe.read_only()
def read() -> dict:
	"""Everything Home's story draws, each part None when the reader may not
	see it or there is nothing to draw."""
	import erpnext

	company = home._company()
	months = _months()
	ledger = _may("GL Entry") and company
	sales = _unpaid("Sales Invoice")
	bills = _unpaid("Purchase Invoice")
	sales_all = _unpaid("Sales Invoice", credits=True)
	bills_all = _unpaid("Purchase Invoice", credits=True)
	cash = _cash(company, months) if ledger else None
	profit = _profit(company, months) if ledger else None
	return {
		"currency": erpnext.get_company_currency(company) if company else None,
		"months": [one.isoformat() for one in months],
		"cards": _cards(months, cash, profit, sales, bills, sales_all, bills_all),
		"money": {
			"flow": cash["flow"],
			"profit": profit["months"],
			"expenses": _expenses(company, months[0]),
		}
		if ledger
		else None,
		"receivable": _owed("Sales Invoice", "customer", sales_all, months[0]),
		"payable": _owed("Purchase Invoice", "supplier", bills_all, months[0]),
	}


def _unpaid(doctype: str, credits: bool = False) -> list | None:
	if not _may(doctype):
		return None
	return home._due(doctype, fields=["customer" if doctype == "Sales Invoice" else "supplier"], credits=credits)


def _leaves(company: str, **filters) -> list[str]:
	return frappe.get_all("Account", filters={"company": company, "is_group": 0, **filters}, pluck="name")


def _entries(company: str, accounts: list, since=None, before=None) -> list:
	"""The ledger on these accounts, a row a day and account."""
	if not accounts:
		return []
	filters = {"company": company, "is_cancelled": 0, "account": ["in", accounts]}
	if since:
		filters["posting_date"] = [">=", since]
	if before:
		filters["posting_date"] = ["<", before]
	return frappe.get_list(
		"GL Entry",
		filters={**filters, "voucher_type": ["!=", "Period Closing Voucher"]},
		fields=[
			"posting_date",
			"account",
			{"SUM": "debit", "as": "debit"},
			{"SUM": "credit", "as": "credit"},
		],
		group_by="posting_date, account",
		limit_page_length=0,
	)


def _cash(company: str, months: list[date]) -> dict:
	"""What came into and went out of the bank and cash accounts each month,
	and what they held at each month's end."""
	accounts = _leaves(company, account_type=["in", ("Bank", "Cash")])
	before = sum(flt(row.debit) - flt(row.credit) for row in _entries(company, accounts, before=months[0]))
	inflow, outflow = defaultdict(float), defaultdict(float)
	for row in _entries(company, accounts, since=months[0]):
		inflow[_month(row.posting_date)] += flt(row.debit)
		outflow[_month(row.posting_date)] += flt(row.credit)
	held, balances, flow = before, [], []
	for month in months:
		key = month.isoformat()
		held += inflow[key] - outflow[key]
		balances.append(held)
		flow.append({"month": key, "inflow": inflow[key], "outflow": -outflow[key]})
	return {"balances": balances, "flow": flow}


def _profit(company: str, months: list[date]) -> dict:
	"""Income less expenses each month, closing entries left out."""
	income = set(_leaves(company, root_type="Income"))
	expense = _leaves(company, root_type="Expense")
	made = defaultdict(float)
	for row in _entries(company, [*income, *expense], since=months[0]):
		made[_month(row.posting_date)] += flt(row.credit) - flt(row.debit)
	rows = []
	for month in months:
		value = made[month.isoformat()]
		rows.append({"month": month.isoformat(), "profit": max(value, 0), "loss": min(value, 0)})
	return {"values": [made[one.isoformat()] for one in months], "months": rows}


def _expenses(company: str, since: date) -> list[dict]:
	"""The largest expense accounts over the months, and the rest as Others."""
	spent = defaultdict(float)
	for row in _entries(company, _leaves(company, root_type="Expense"), since=since):
		spent[row.account] += flt(row.debit) - flt(row.credit)
	ranked = sorted(((value, account) for account, value in spent.items() if value > 0), reverse=True)
	names = dict(
		frappe.get_all(
			"Account",
			filters={"name": ["in", [a for _, a in ranked[:TOP]] or [""]]},
			fields=["name", "account_name"],
			as_list=True,
		)
	)
	rows = [
		{"name": names.get(account, account), "account": account, "spent": value}
		for value, account in ranked[:TOP]
	]
	rest = sum(value for value, _ in ranked[TOP:])
	if rest:
		rows.append({"name": frappe._("All Other Accounts"), "account": None, "spent": rest})
	return rows


def _billed(doctype: str, months: list[date]) -> list[float]:
	"""What was invoiced each month, credit and debit notes left out."""
	by = defaultdict(float)
	for row in frappe.get_list(
		doctype,
		filters={
			"docstatus": 1,
			"is_return": 0,
			"company": home._company(),
			"posting_date": [">=", months[0]],
		},
		fields=["posting_date", "base_grand_total"],
		limit_page_length=0,
	):
		by[_month(row.posting_date)] += flt(row.base_grand_total)
	return [by[one.isoformat()] for one in months]


def _cards(months, cash, profit, sales, bills, sales_all=None, bills_all=None) -> dict:
	"""The headline figures, each with its months where it has them."""
	cards = {}
	if cash:
		cards["cash"] = {"value": cash["balances"][-1], "series": cash["balances"]}
	if sales is not None:
		cards["receivable"] = {"value": home.outstanding(sales if sales_all is None else sales_all), "series": _billed("Sales Invoice", months)}
		cards["overdue"] = {"value": home.outstanding(sales, until=home.yesterday()), "series": fell_due(sales, months)}
	if bills is not None:
		cards["payable"] = {"value": home.outstanding(bills if bills_all is None else bills_all), "series": _billed("Purchase Invoice", months)}
		cards["due_this_week"] = {"value": home.outstanding(bills, until=home.this_week()), "series": falls_due(bills), "until": str(home.this_week())}
	if profit:
		cards["profit"] = {"value": profit["values"][-1], "series": profit["values"]}
	return cards


def fell_due(rows: list, months: list[date], day=None) -> list[float]:
	"""What is late, by the month it fell due; anything older in the first.
	Pure over rows of outstanding_amount and due_date."""
	day = getdate(day or today())
	by = [0.0] * len(months)
	for row in rows:
		due = row.get("due_date") and getdate(row.get("due_date"))
		if not due or due >= day:
			continue
		at = next((i for i in range(len(months) - 1, -1, -1) if due >= months[i]), 0)
		by[at] += flt(row.get("outstanding_amount"))
	return by


def falls_due(rows: list, day=None) -> list[float]:
	"""What falls due each day of the coming week; anything late on the first.
	Pure over rows of outstanding_amount and due_date."""
	day = getdate(day or today())
	by = [0.0] * home.WEEK
	for row in rows:
		due = row.get("due_date") and getdate(row.get("due_date"))
		if not due:
			continue
		ahead = max(date_diff(due, day), 0)
		if ahead < home.WEEK:
			by[ahead] += flt(row.get("outstanding_amount"))
	return by


def ageing(rows: list, day=None) -> list[dict]:
	"""What is still owed, by how long past due, in ERPNext's ranges: not yet
	due, then 0-30, 31-60, 61-90, 91-120 and 121-Above. Pure over rows of
	outstanding_amount and due_date."""
	day = getdate(day or today())
	bands = [
		"not_due",
		*[f"{low + 1 if low else 0}-{high}" for low, high in zip((0, *RANGES), RANGES, strict=False)],
		f"{RANGES[-1] + 1}-Above",
	]
	owed = dict.fromkeys(bands, 0.0)
	for row in rows:
		late = date_diff(day, row.get("due_date")) if row.get("due_date") else 0
		if late <= 0:
			band = "not_due"
		else:
			band = next((b for b, high in zip(bands[1:], RANGES, strict=False) if late <= high), bands[-1])
		owed[band] += flt(row.get("outstanding_amount"))
	return [{"band": band, "owed": value} for band, value in owed.items()]


def _owed(doctype: str, party: str, rows: list | None, since: date) -> dict | None:
	"""Who owes the most or is owed the most, how late it is, and where the
	year's invoices stand by ERPNext's status."""
	if rows is None:
		return None
	by = defaultdict(float)
	for row in rows:
		by[row.get(party)] += flt(row.get("outstanding_amount"))
	parties = sorted(
		({"name": name, "owed": value} for name, value in by.items() if value > 0),
		key=lambda one: -one["owed"],
	)
	statuses = frappe.get_list(
		doctype,
		filters={"docstatus": 1, "is_return": 0, "company": home._company(), "posting_date": [">=", since]},
		fields=["status", {"SUM": "base_grand_total", "as": "billed"}, {"COUNT": "*", "as": "invoices"}],
		group_by="status",
		order_by="billed desc",
		limit_page_length=0,
	)
	return {
		"ages": ageing(rows),
		"parties": parties[:PARTIES],
		"statuses": [
			{"status": one.status, "billed": flt(one.billed), "invoices": one.invoices} for one in statuses
		],
	}
