"""The accounts erpnext nominates carry the type hrms demands of them.

Twice now the same shape has stopped a screen working on a site nobody had
touched: erpnext's standard chart of accounts creates an account, names the
company's default after it, and gives it a type hrms then refuses.

**Payroll Payable** is created under Accounts Payable with an `account_category`
and *no* `account_type`, and `default_payroll_payable_account` is set to it.
Payroll Entry answers *"Account type should be set Payable for payroll payable
account Payroll Payable - ONE, please set and try again"* and a payroll run
cannot be made at all.

**Employee Advances** is worse, because erpnext contradicts itself in adjacent
lines — `{"account_type": "Payable", "account_category": "Other Receivables"}` —
on an account whose root type is Asset. An advance is money the employee owes
back, so Receivable is right, and `Employee Advance.validate` says so: *"Employee
advance account Employee Advances - ONE should be of type Receivable."* No
advance can be made either.

Neither is a decision this product is making. erpnext named both accounts and
nominated both; this is the missing or mistaken half of a sentence erpnext
started, and it is corrected only where the value is still exactly what erpnext
shipped — a workspace that chose its own keeps it.
"""

import frappe

#: (the Company field that nominates the account, the type hrms needs, the
#: values this is allowed to overrule — empty string meaning "never written").
WANTED = (
	("default_payroll_payable_account", "Payable", ("",)),
	("default_employee_advance_account", "Receivable", ("", "Payable")),
)


def ready(*_args) -> None:
	"""Give every company's nominated account the type its screen needs."""
	for field, wanted, replaces in WANTED:
		for company, account in frappe.get_all(
			"Company",
			filters={field: ("is", "set")},
			fields=["name", field],
			as_list=True,
		):
			if not frappe.db.exists("Account", account):
				continue
			has = frappe.db.get_value("Account", account, "account_type") or ""
			if has == wanted or has not in replaces:
				continue
			frappe.db.set_value("Account", account, "account_type", wanted)
