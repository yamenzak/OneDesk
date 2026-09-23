"""What will fail the first time somebody invoices, is paid or pays.

ERPNext builds a company's chart and most of its defaults when the company is
made, and leaves a handful of things that nothing complains about until the
first document that needs them. Each is a row of the **Books Check**
(report/books_check) with what it means and, where one exists, the fix beside
it. The ones that need no decision are made without asking:

- **The bank.** The Standard chart has a *group* called Bank Accounts and no
  bank ledger, so the company's default bank account is empty and every bank
  mode of payment — Wire Transfer, Cheque, Credit Card, Bank Draft — has no
  account behind it: a payment by transfer does not know where the money went.
  **Add Bank Account** makes the bank, its ledger under that group and the
  company's Bank Account in one step, and a company bank account saved from
  anywhere fills the company default and every bank mode of payment that has
  none (`wired`).
- **Tax.** Five UAE templates ship and none is the default, so an invoice
  carries no VAT unless somebody picks it. Which is the default is the
  business's decision, so the fix asks.
- **The same bill twice.** ERPNext does not stop a supplier's invoice number
  being entered twice unless told to.
- **The year.** A date outside every fiscal year stops every document on it.
  ERPNext makes next year's three days before this one ends, when the
  scheduler runs; the check catches a site where it did not.
- **Reminding a late customer.** The Payment Reminder (one_book/paid.py) is
  shipped off, since it writes to customers; the fix turns it on.
- **The defaults ERPNext throws on** — receivable, payable, income, cost
  center, round-off, exchange gain or loss — named when any is empty.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_years, getdate, nowdate

#: Who may change what the check fixes.
FIXERS = ("Accounts Manager", "Workspace Administrator")

#: Company fields a first invoice or payment throws without, and what each is.
DEFAULTS = {
	"default_receivable_account": "Default Receivable Account",
	"default_payable_account": "Default Payable Account",
	"default_income_account": "Default Income Account",
	"cost_center": "Default Cost Center",
	"round_off_account": "Round Off Account",
	"round_off_cost_center": "Round Off Cost Center",
	"exchange_gain_loss_account": "Exchange Gain / Loss Account",
}

READY, TO_DO, SUGGESTED = "Ready", "To Do", "Suggested"


def company():
	from erpnext import get_default_company

	return frappe.get_cached_doc("Company", get_default_company())


def checks() -> list[dict]:
	"""Every check, in the order a first invoice meets them."""
	one = company()
	return [
		_year(one),
		_defaults(one),
		_bank(one),
		_bank_modes(one),
		_tax(one, "Sales Taxes and Charges Template", "sales_tax", _("Invoices carry tax")),
		_tax(one, "Purchase Taxes and Charges Template", "purchase_tax", _("Bills carry tax")),
		_bill_numbers(),
		_reminder(),
	]


def _row(key, check, state, says, fix=None) -> dict:
	return {"key": key, "check": check, "state": state, "says": says, "fix": fix if state != READY else None}


def _year(one) -> dict:
	from erpnext.accounts.utils import FiscalYearError, get_fiscal_year

	try:
		get_fiscal_year(nowdate(), company=one.name)
	except FiscalYearError:
		return _row("year", _("Today is in a fiscal year"), TO_DO, _("No fiscal year covers today, so nothing dated today can be saved."), "year")
	return _row("year", _("Today is in a fiscal year"), READY, _("Next year's is made three days before this one ends."))


def _defaults(one) -> dict:
	missing = [_(label) for field, label in DEFAULTS.items() if not one.get(field)]
	if missing:
		return _row("defaults", _("The company's default accounts are set"), TO_DO, _("Set on the company: {0}.").format(", ".join(missing)), "company")
	return _row("defaults", _("The company's default accounts are set"), READY, _("Receivable, payable, income, cost center and round-off."))


def banks(company_name: str) -> list:
	return frappe.get_all(
		"Bank Account",
		filters={"is_company_account": 1, "company": company_name, "disabled": 0, "account": ["is", "set"]},
		fields=["name", "account", "is_default"],
		order_by="is_default desc, creation asc",
	)


def _bank(one) -> dict:
	if banks(one.name):
		return _row("bank", _("A bank account is set up"), READY, _("Payments by transfer, cheque or card have somewhere to go."))
	return _row("bank", _("A bank account is set up"), TO_DO, _("There is no company bank account, so a payment by transfer does not know where the money went."), "bank")


def unwired_modes(company_name: str) -> list[str]:
	"""Enabled bank modes of payment with no account for the company."""
	modes = frappe.get_all("Mode of Payment", filters={"type": "Bank", "enabled": 1}, pluck="name")
	have = set(
		frappe.get_all(
			"Mode of Payment Account",
			filters={"parent": ["in", modes or [""]], "company": company_name, "default_account": ["is", "set"]},
			pluck="parent",
		)
	)
	return [mode for mode in modes if mode not in have]


def _bank_modes(one) -> dict:
	missing = unwired_modes(one.name)
	if not missing and one.default_bank_account:
		return _row("modes", _("Bank payments know which account"), READY, _("The company's default bank and every bank mode of payment point at a bank account."))
	says = _("Without an account: {0}.").format(", ".join(missing)) if missing else _("The company has no default bank account.")
	return _row("modes", _("Bank payments know which account"), TO_DO, says, "modes" if banks(one.name) else None)


def _tax(one, doctype: str, key: str, check: str) -> dict:
	templates = frappe.get_all(doctype, filters={"company": one.name, "disabled": 0}, fields=["name", "is_default"])
	if not templates:
		return _row(key, check, READY, _("No tax templates, so nothing is charged. Add one if you are registered for VAT."))
	default = next((template.name for template in templates if template.is_default), None)
	if default:
		return _row(key, check, READY, _("{0} is added unless somebody picks another.").format(default))
	return _row(key, check, SUGGESTED, _("No template is the default, so nothing is charged unless somebody picks one."), key)


def _bill_numbers() -> dict:
	if frappe.db.get_single_value("Accounts Settings", "check_supplier_invoice_uniqueness"):
		return _row("bills", _("A supplier's bill cannot be entered twice"), READY, _("The same supplier invoice number is refused a second time."))
	return _row("bills", _("A supplier's bill cannot be entered twice"), SUGGESTED, _("The same supplier invoice number can be entered twice and paid twice."), "bills")


def _reminder() -> dict:
	from onedesk.one_book.paid import REMINDER

	check = _("A late customer is reminded")
	if frappe.db.get_value("Notification", REMINDER, "enabled"):
		return _row("reminder", check, READY, _("A customer is mailed the invoice a week after it falls due."))
	return _row("reminder", check, SUGGESTED, _("Nobody is reminded of an unpaid invoice. The fix mails the customer a week after it falls due."), "reminder")


@frappe.whitelist(methods=["POST"])
def fix(key: str, **values) -> None:
	"""The fix beside a check."""
	frappe.only_for(FIXERS)
	one = company()
	if key == "year":
		add_year(one.name)
	elif key == "bank":
		add_bank(values.get("bank"), values.get("account_name"), values.get("iban"), values.get("bank_account_no"))
	elif key == "modes":
		found = banks(one.name)
		if found:
			wire(one.name, found[0].account)
	elif key in ("sales_tax", "purchase_tax"):
		doctype = "Sales Taxes and Charges Template" if key == "sales_tax" else "Purchase Taxes and Charges Template"
		template = frappe.get_doc(doctype, values.get("template"))
		template.is_default = 1
		template.save()
	elif key == "bills":
		frappe.db.set_single_value("Accounts Settings", "check_supplier_invoice_uniqueness", 1)
	elif key == "reminder":
		from onedesk.one_book.paid import REMINDER

		frappe.db.set_value("Notification", REMINDER, "enabled", 1)
	else:
		frappe.throw(_("Nothing to fix for {0}.").format(key))


def add_year(company_name: str) -> str:
	"""A fiscal year covering today, as long as a year and following the last."""
	last = frappe.get_all("Fiscal Year", fields=["year_end_date"], order_by="year_end_date desc", limit=1)
	starts, ends = covering(last[0].year_end_date if last else None, getdate(nowdate()))
	year = frappe.get_doc(
		{
			"doctype": "Fiscal Year",
			"year": str(starts.year) if (starts.month, starts.day) == (1, 1) else f"{starts.year}-{ends.year}",
			"year_start_date": starts,
			"year_end_date": ends,
			"companies": [{"company": company_name}],
		}
	).insert()
	return year.name


def covering(last_ends, today):
	"""The first and last day of the fiscal year after `last_ends` that holds
	`today`; the calendar year when there has been none. Pure."""
	if not last_ends:
		starts = today.replace(month=1, day=1)
	else:
		starts = add_days(getdate(last_ends), 1)
		while add_days(add_years(starts, 1), -1) < today:
			starts = add_years(starts, 1)
	return starts, add_days(add_years(starts, 1), -1)


def add_bank(bank: str, account_name: str, iban: str | None = None, number: str | None = None) -> str:
	"""The bank, its ledger under the chart's bank group, and the company's
	Bank Account, which `wired` then connects."""
	bank, account_name = (bank or "").strip(), (account_name or "").strip()
	if not bank or not account_name:
		frappe.throw(_("Name the bank and the account."))
	one = company()
	if not frappe.db.exists("Bank", bank):
		frappe.get_doc({"doctype": "Bank", "bank_name": bank}).insert()
	ledger = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": f"{bank} {account_name}",
			"parent_account": bank_group(one.name),
			"company": one.name,
			"account_type": "Bank",
			"account_currency": one.default_currency,
		}
	).insert()
	account = frappe.get_doc(
		{
			"doctype": "Bank Account",
			"account_name": account_name,
			"bank": bank,
			"account": ledger.name,
			"is_company_account": 1,
			"company": one.name,
			"is_default": 0 if banks(one.name) else 1,
			"iban": iban,
			"bank_account_no": number,
		}
	).insert()
	return account.name


def bank_group(company_name: str) -> str:
	"""Where a new bank ledger goes: the chart's bank group."""
	found = frappe.get_all(
		"Account", filters={"company": company_name, "is_group": 1, "account_type": "Bank"}, pluck="name", order_by="lft", limit=1
	) or frappe.get_all(
		"Account", filters={"company": company_name, "is_group": 1, "account_name": ["like", "Bank Accounts%"]}, pluck="name", limit=1
	)
	if not found:
		frappe.throw(_("The chart of accounts has no group for bank accounts. Add one under Current Assets with the type Bank."))
	return found[0]


def wired(doc, method=None) -> None:
	"""Bank Account on_update: a company bank account fills the company's
	default bank and every bank mode of payment that has no account."""
	if not doc.is_company_account or not doc.account or doc.disabled:
		return
	if not doc.is_default and len(banks(doc.company)) > 1:
		return
	wire(doc.company, doc.account)


def wire(company_name: str, account: str) -> None:
	if not frappe.db.get_value("Company", company_name, "default_bank_account"):
		frappe.db.set_value("Company", company_name, "default_bank_account", account)
		frappe.clear_document_cache("Company", company_name)
	for mode in unwired_modes(company_name):
		row = frappe.get_doc("Mode of Payment", mode)
		row.set("accounts", [one for one in row.accounts if one.company != company_name])
		row.append("accounts", {"company": company_name, "default_account": account})
		row.flags.ignore_permissions = True
		row.save()
