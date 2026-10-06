"""The accounts erpnext nominates carry the type hrms demands of them."""

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


def component(doc, method=None) -> None:
	"""An earning with no account for a company books to its Salary account.
	HRMS needs one per company on every component a payroll pays, and without
	it the run makes the slips and never submits them."""
	if doc.type != "Earning":
		return
	held = {row.company for row in doc.accounts}
	for company in frappe.get_all("Company", pluck="name"):
		account = company not in held and _salary(company)
		if account:
			doc.append("accounts", {"company": company, "account": account})


def _salary(company: str) -> str | None:
	"""The Salary expense account erpnext's chart makes for every company."""
	return frappe.db.get_value(
		"Account", {"company": company, "account_name": "Salary", "root_type": "Expense", "is_group": 0}
	)


def components(*_args) -> None:
	"""The earnings made before this, given their account."""
	for name in frappe.get_all("Salary Component", filters={"type": "Earning"}, pluck="name"):
		doc = frappe.get_doc("Salary Component", name)
		before = len(doc.accounts)
		component(doc)
		if len(doc.accounts) > before:
			doc.save(ignore_permissions=True)


def year(*_args) -> None:
	"""Point the site's default fiscal year at the one we are in."""
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
