"""The books around the work: the bank account, the money the year opened
with, the rent and the rest paid each month by journal entry, and chasing
what customers owe."""

import frappe

from onedesk.one_demo.base import COMPANY, as_user, dated, make, on, save, tag, today

ACCOUNTS = "huda@one.test"


def run(password=None):
	from onedesk.one_book import ready

	with as_user(ACCOUNTS):
		ready.fix("template_taxes")
		_repeating()
		bank = _bank()
		_collecting()
		_rules(bank)
		if frappe.db.exists("Journal Entry", {"voucher_type": "Opening Entry", "docstatus": 1}):
			return
		_entry(on(1, 1), "Opening Entry", "Opening balances", ((bank, 1250000, 0), (_equity(), 0, 1250000)))
		rent = _expense("Rent Expense")
		for month in range(1, today().month + 1):
			date = on(month, 1)
			_entry(date, "Journal Entry", f"Workshop and office rent, {date.strftime('%B')}", ((rent, 38000, 0), (bank, 0, 38000)))
		utilities = _expense("Utility Expenses")
		for month in range(1, today().month):
			date = on(month, 20)
			_entry(date, "Journal Entry", f"DEWA, {date.strftime('%B')}", ((utilities, 6200 + month * 140, 0), (bank, 0, 6200 + month * 140)))


def _repeating():
	"""Gulf Office Supplies bills the same every month, so its last bill is
	made again each month from the next one on (one_book/repeat.py)."""
	from frappe.utils import add_months

	last = frappe.get_all(
		"Purchase Invoice",
		filters={"supplier": "Gulf Office Supplies", "docstatus": 1, "is_return": 0},
		fields=["name", "posting_date"],
		order_by="posting_date desc",
		limit=1,
	)
	if not last or frappe.db.exists("Auto Repeat", {"reference_doctype": "Purchase Invoice"}):
		return
	make(
		{
			"doctype": "Auto Repeat",
			"reference_doctype": "Purchase Invoice",
			"reference_document": last[0].name,
			"frequency": "Monthly",
			"start_date": add_months(last[0].posting_date, 1),
		}
	)


def _bank():
	from onedesk.one_book.ready import add_bank

	found = frappe.db.get_value("Bank Account", {"company": COMPANY, "is_company_account": 1}, "account")
	if found:
		return found
	made = add_bank("Emirates NBD", "Operating Account", iban="AE070331234567890123456")
	return frappe.db.get_value("Bank Account", made, "account")


def _equity():
	return frappe.db.get_value("Account", {"company": COMPANY, "root_type": "Equity", "is_group": 0, "account_name": ["like", "%Capital%"]}) or frappe.db.get_value(
		"Account", {"company": COMPANY, "root_type": "Equity", "is_group": 0}
	)


def _expense(name):
	found = frappe.db.get_value("Account", {"company": COMPANY, "account_name": name, "is_group": 0})
	if found:
		return found
	parent = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Indirect Expenses", "is_group": 1})
	return make({"doctype": "Account", "account_name": name, "parent_account": parent, "company": COMPANY, "account_type": "Expense Account"}).name


def _entry(date, kind, remark, lines):
	entry = frappe.new_doc("Journal Entry")
	entry.voucher_type = kind
	entry.company = COMPANY
	dated(entry, date)
	entry.user_remark = remark
	entry.cheque_no = remark[:20]
	entry.cheque_date = date
	for ledger, debit, credit in lines:
		entry.append("accounts", {"account": ledger, "debit_in_account_currency": debit, "credit_in_account_currency": credit})
	save(entry, submit=True)


def _collecting():
	"""Chasing what is owed: a payment reminder to the customer longest late,
	a payment request for another, and their statements each month."""
	from erpnext.accounts.doctype.payment_request.payment_request import make_payment_request
	from erpnext.accounts.doctype.sales_invoice.mapper import create_dunning

	from onedesk.one_book import home

	late = home._late("Sales Invoice", "customer", home.yesterday(), today())
	if not late:
		return
	if not frappe.db.exists("Dunning Type", {"company": COMPANY}):
		make(
			{
				"doctype": "Dunning Type",
				"dunning_type": "First Reminder",
				"company": COMPANY,
				"is_default": 1,
				"dunning_letter_text": [
					{
						"language": "en",
						"is_default_language": 1,
						"body_text": "<p>Dear {{ customer_name }},</p><p>Our records show the invoices below are past their due date. If you have already paid, thank you, and please ignore this reminder.</p>",
						"closing_text": "<p>With kind regards,<br>Accounts, {{ company }}</p>",
					}
				],
			}
		)
	first = late[0]["name"]
	if not frappe.db.exists("Overdue Payment", {"sales_invoice": first, "docstatus": 1}):
		save(create_dunning(first), submit=True)
	second = late[1]["name"] if len(late) > 1 else first
	if not frappe.db.exists("Payment Request", {"reference_name": second}):
		tag(make_payment_request(dt="Sales Invoice", dn=second, mute_email=1, submit_doc=1, return_doc=1))
	customers = sorted({one["party"] for one in late})
	if not frappe.db.exists("Process Statement Of Accounts", "Monthly Statements"):
		make(
			{
				"doctype": "Process Statement Of Accounts",
				"__newname": "Monthly Statements",
				"company": COMPANY,
				"report": "Accounts Receivable",
				"frequency": "Monthly",
				"include_ageing": 1,
				"enable_auto_email": 0,
				"posting_date": today(),
				"customers": [
					{"customer": frappe.db.get_value("Customer", {"customer_name": name}) or name} for name in customers
				],
			}
		)


def _rules(bank):
	"""The bank's own lines matched without asking: DEWA's direct debits are
	utilities."""
	if frappe.db.exists("Bank Transaction Rule", {"company": COMPANY}):
		return
	make(
		{
			"doctype": "Bank Transaction Rule",
			"rule_name": "DEWA direct debit",
			"company": COMPANY,
			"transaction_type": "Withdrawal",
			"description_rules": [{"check": "Contains", "value": "DEWA"}],
			"classify_as": "Bank Entry",
			"account": _expense("Utility Expenses"),
			"priority": 1,
		}
	)
	if not frappe.db.exists("Tax Category", "Export"):
		make({"doctype": "Tax Category", "title": "Export"})


TRANSPORT = "Transport Expenses"


def matched():
	"""Huda matches the statement's transport debit the way the bank
	reconciliation tool does it: a bank entry made from the line, to
	transport, and reconciled in the same step. The Marina Hotels deposit is
	left for OneAI's draft payment."""
	from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import (
		create_journal_entry_bts,
	)

	with as_user(ACCOUNTS):
		lines = frappe.get_all(
			"Bank Transaction",
			filters={"docstatus": 1, "status": "Unreconciled", "withdrawal": [">", 0], "description": ["like", "%transport%"]},
			fields=["name", "reference_number", "date"],
		)
		for line in lines:
			create_journal_entry_bts(
				line.name,
				reference_number=line.reference_number,
				reference_date=line.date,
				posting_date=line.date,
				entry_type="Bank Entry",
				second_account=_expense(TRANSPORT),
			)

