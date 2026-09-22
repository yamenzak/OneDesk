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

`fiscal_year` below is the third of the same kind: erpnext creates the Fiscal
Year and nothing ever makes it the site's default, so a report whose filter
reads `frappe.defaults.get_user_default("fiscal_year")` gets nothing.
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


def year(*_args) -> None:
	"""Point the site's default fiscal year at the one we are in.

	`Vehicle Expenses` defaults its `fiscal_year` filter to
	`frappe.defaults.get_user_default("fiscal_year")` and then throws **Start
	Year and End Year are mandatory** in a red modal, before the page has drawn,
	on a site where nothing ever set that default. erpnext creates the Fiscal
	Year; it just never nominates one.

	Re-pointed on every migrate rather than written once, because a default that
	is right in January and wrong the following January is worse than none.
	"""
	today = frappe.utils.getdate()
	now = frappe.get_all(
		"Fiscal Year",
		filters={"year_start_date": ("<=", today), "year_end_date": (">=", today), "disabled": 0},
		pluck="name",
		limit=1,
	)
	if not now:
		return
	if frappe.db.get_default("fiscal_year") != now[0]:
		frappe.db.set_default("fiscal_year", now[0])
