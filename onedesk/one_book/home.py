"""The figures on OneBook's Home: cash, what customers owe and how much of it
is late, what the company owes and what falls due this week, and this month's
profit.

ERPNext ships accounting number cards, and none answers these: they total
every invoice ever submitted, count a credit note as a negative invoice, and
say nothing about what is still unpaid. Each figure here is worked out from
the ledger or from what is outstanding, for the one company, and opens the
report it came from.
"""

import frappe
from frappe.utils import add_days, flt, get_first_day, getdate, nowdate

#: How far ahead Due This Week looks, today included.
WEEK = 7


def _card(amount, route: list, options: dict | None = None) -> dict:
	card = {"value": amount, "fieldtype": "Currency", "route": route}
	if options:
		card["route_options"] = options
	return card


def _company() -> str:
	from erpnext import get_default_company

	return get_default_company()


def _ledger(sql: str, **values) -> float:
	frappe.has_permission("GL Entry", "read", throw=True)
	found = frappe.db.sql(sql, {"company": _company(), **values})
	return flt(found[0][0]) if found else 0.0


@frappe.whitelist()
@frappe.read_only()
def cash(filters: str | None = None) -> dict:
	"""What is in the bank and cash accounts, by the ledger."""
	amount = _ledger(
		"""select sum(entry.debit - entry.credit) from `tabGL Entry` entry
		join `tabAccount` account on account.name = entry.account
		where entry.company = %(company)s and entry.is_cancelled = 0
		and account.account_type in ('Bank', 'Cash')"""
	)
	return _card(amount, ["query-report", "Cash Flow"])


@frappe.whitelist()
@frappe.read_only()
def profit_this_month(filters: str | None = None) -> dict:
	"""Income less expenses since the first of the month. The entries a period
	closing makes are left out, since they move the profit, not make it."""
	amount = _ledger(
		"""select sum(entry.credit - entry.debit) from `tabGL Entry` entry
		join `tabAccount` account on account.name = entry.account
		where entry.company = %(company)s and entry.is_cancelled = 0
		and account.root_type in ('Income', 'Expense')
		and entry.voucher_type != 'Period Closing Voucher'
		and entry.posting_date between %(start)s and %(today)s""",
		start=get_first_day(nowdate()),
		today=nowdate(),
	)
	return _card(amount, ["query-report", "Profit and Loss Statement"])


def _unpaid(doctype: str) -> list:
	return frappe.get_list(
		doctype,
		filters={"docstatus": 1, "outstanding_amount": [">", 0], "company": _company()},
		fields=["outstanding_amount", "due_date"],
		limit=0,
	)


def outstanding(rows: list, until=None) -> float:
	"""What the rows still owe; only what falls due by `until` when given.
	Pure over rows of outstanding_amount and due_date."""
	return sum(
		flt(row.get("outstanding_amount"))
		for row in rows
		if until is None or (row.get("due_date") and getdate(row.get("due_date")) <= getdate(until))
	)


@frappe.whitelist()
@frappe.read_only()
def owed_to_us(filters: str | None = None) -> dict:
	"""What customers still owe on invoices."""
	return _card(outstanding(_unpaid("Sales Invoice")), ["query-report", "Accounts Receivable"])


@frappe.whitelist()
@frappe.read_only()
def overdue(filters: str | None = None) -> dict:
	"""What customers owe on invoices past their due date."""
	amount = outstanding(_unpaid("Sales Invoice"), until=add_days(nowdate(), -1))
	return _card(amount, ["List", "Sales Invoice"], {"status": "Overdue"})


@frappe.whitelist()
@frappe.read_only()
def we_owe(filters: str | None = None) -> dict:
	"""What the company still owes on bills."""
	return _card(outstanding(_unpaid("Purchase Invoice")), ["query-report", "Accounts Payable"])


@frappe.whitelist()
@frappe.read_only()
def due_this_week(filters: str | None = None) -> dict:
	"""What falls due on bills in the next seven days, and any already late."""
	amount = outstanding(_unpaid("Purchase Invoice"), until=add_days(nowdate(), WEEK - 1))
	return _card(amount, ["List", "Purchase Invoice"], {"status": ["in", ["Unpaid", "Overdue", "Partly Paid"]]})
