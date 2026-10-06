"""The books around the work: the bank account, the money the year opened
with, the rent and the rest paid each month by journal entry."""

import frappe

from onedesk.one_demo.base import COMPANY, as_user, dated, make, on, save, today

ACCOUNTS = "huda@one.test"


def run(password=None):
	with as_user(ACCOUNTS):
		bank = _bank()
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
