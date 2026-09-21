"""A payroll run can be made on a site nobody has edited the chart of accounts on.

ERPNext's standard chart of accounts creates **Payroll Payable** under Accounts
Payable with an `account_category` and no `account_type`, and sets it as the
company's `default_payroll_payable_account`. HRMS's Payroll Entry then refuses:

    Account type should be set Payable for payroll payable account
    Payroll Payable - ONE, please set and try again

So out of the box the company has a payroll payable account, the payroll entry
is pointed at it by default, and the run cannot be made — until somebody who
knows what `account_type` is opens the chart of accounts and sets it. Nothing on
the payroll screen says that is where to go.

The account is already named "Payroll Payable" by erpnext and already nominated
by erpnext; saying it is Payable is not a decision, it is the missing half of a
sentence erpnext started. Only an account with no type at all is touched, so a
workspace that set it to something deliberately keeps it.
"""

import frappe

PAYABLE = "Payable"


def ready(*_args) -> None:
	"""Give every company's payroll payable account the type payroll needs."""
	for company, account in frappe.get_all(
		"Company",
		filters={"default_payroll_payable_account": ("is", "set")},
		fields=["name", "default_payroll_payable_account"],
		as_list=True,
	):
		if not frappe.db.exists("Account", account):
			continue
		if frappe.db.get_value("Account", account, "account_type"):
			continue
		frappe.db.set_value("Account", account, "account_type", PAYABLE)
