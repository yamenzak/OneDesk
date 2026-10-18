"""What will fail the first time somebody invoices, is paid or pays: each is a
row of the Books Check, with the fix beside it.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_years, flt, getdate, nowdate

FIXERS = ("Accounts Manager", "Workspace Administrator")

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
		_template_taxes(),
		_bill_numbers(),
		_reminder(),
		*_uae(one),
		_opening(one),
		_closed(one),
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
	if default and ruled(one.name, doctype, default):
		return _row(key, check, READY, _("{0} is added unless somebody picks another.").format(default))
	if default:
		return _row(key, check, SUGGESTED, _("{0} is added in a form, but not to one made by One, OneAI or an import.").format(default), key)
	return _row(key, check, SUGGESTED, _("No template is the default, so nothing is charged unless somebody picks one."), key)


SIDES = {
	"Sales Taxes and Charges Template": ("Sales", "sales_tax_template"),
	"Purchase Taxes and Charges Template": ("Purchase", "purchase_tax_template"),
}


def ruled(company: str, doctype: str, template: str) -> bool:
	"""Whether a Tax Rule names the template."""
	side, field = SIDES[doctype]
	return bool(frappe.db.exists("Tax Rule", {"company": company, "tax_type": side, field: template}))


def charge(company: str, doctype: str, template: str) -> None:
	"""The template on every new invoice or bill, however it is made. A form
	takes the default template, but one made on the server, by Invoice Time,
	OneAI, Intake or an import, takes only what a Tax Rule names
	(erpnext/accounts/party.py `set_taxes`). So the default gets a rule with
	no conditions too, which any rule for a country or a group outranks."""
	doc = frappe.get_doc(doctype, template)
	if not doc.is_default:
		doc.is_default = 1
		doc.save()
	if ruled(company, doctype, template):
		return
	side, field = SIDES[doctype]
	frappe.get_doc({"doctype": "Tax Rule", "company": company, "tax_type": side, field: template, "priority": 1}).insert()


def _template_taxes() -> dict:
	check = _("A tax template brings its taxes")
	if frappe.db.get_single_value("Accounts Settings", "add_taxes_from_taxes_and_charges_template"):
		return _row("template_taxes", check, READY, _("An invoice or bill that names a tax template gets its taxes, however it was made."))
	return _row("template_taxes", check, SUGGESTED, _("An invoice or bill made by an import or by OneAI names its tax template and charges no tax."), "template_taxes")


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


def _uae(one) -> list[dict]:
	"""What the UAE VAT return and a UAE tax invoice need. Only in the UAE."""
	from onedesk.one_book import vat

	if not vat.in_uae(one.name):
		return []
	rows = []
	check = _("The VAT return knows the VAT accounts")
	if vat.settled_accounts(one.name):
		rows.append(_row("uae_vat", check, READY, _("UAE VAT Settings name the accounts VAT is charged and paid to.")))
	else:
		rows.append(_row("uae_vat", check, TO_DO, _("UAE VAT Settings are empty, so the return's reverse-charge boxes read nought."), "uae_vat"))
	check = _("Invoices carry the company's TRN")
	if one.tax_id:
		rows.append(_row("trn", check, READY, _("A UAE tax invoice must show the supplier's TRN.")))
	else:
		rows.append(_row("trn", check, TO_DO, _("The company has no TRN, and a UAE tax invoice must show it."), "trn"))
	check = _("The company's emirate is known")
	address = vat.company_address(one.name)
	if address and frappe.db.get_value("Address", address, "emirate"):
		rows.append(_row("emirate", check, READY, _("Sales are reported under the company's emirate.")))
	else:
		rows.append(_row("emirate", check, TO_DO, _("The company has no address with an emirate, so the return cannot say where sales were made."), "emirate"))
	return rows


def temporary(company_name: str) -> tuple[str, float] | None:
	"""Temporary Opening and what it still holds, debit less credit, when it
	holds anything. Pure but for reading the ledger."""
	account = frappe.db.get_value(
		"Account", {"company": company_name, "account_type": "Temporary", "is_group": 0}, "name"
	)
	if not account:
		return None
	held = frappe.db.sql(
		"""select sum(debit) - sum(credit) from `tabGL Entry`
		where account = %s and is_cancelled = 0""",
		account,
	)
	balance = flt(held[0][0]) if held else 0
	return (account, balance) if abs(balance) >= 0.005 else None


def _opening(one) -> dict:
	"""ERPNext posts opening invoices and opening stock against Temporary
	Opening, and an accountant moves what it holds to capital once every
	opening balance is in. Until then the Balance Sheet carries it."""
	check = _("Opening balances are finished")
	held = temporary(one.name)
	if not held:
		return _row("opening", check, READY, _("Temporary Opening is at nought."))
	amount = frappe.format_value(abs(held[1]), {"fieldtype": "Currency", "options": "currency"}, currency=one.default_currency)
	return _row(
		"opening",
		check,
		TO_DO,
		_("Temporary Opening still holds {0}: post the other side of the opening balances to capital with a Journal Entry.").format(amount),
	)


def _closed(one) -> dict:
	from onedesk.one_book import closing

	check = _("Every year that has ended is closed")
	open_ = closing.unclosed(one.name)
	if open_:
		return _row("close", check, TO_DO, _("{0} has ended and its profit is not yet moved to Retained Earnings.").format(open_[0].name), "close")
	until = closing.locked(one.name)
	if until:
		return _row("close", check, READY, _("The books are locked up to {0}.").format(frappe.format_value(until, {"fieldtype": "Date"})))
	return _row("close", check, READY, _("No year has ended with entries left open."))


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
		charge(one.name, doctype, values.get("template"))
	elif key == "bills":
		frappe.db.set_single_value("Accounts Settings", "check_supplier_invoice_uniqueness", 1)
	elif key == "template_taxes":
		frappe.db.set_single_value("Accounts Settings", "add_taxes_from_taxes_and_charges_template", 1)
	elif key == "uae_vat":
		from onedesk.one_book import vat

		vat.uae_accounts(one.name)
	elif key == "trn":
		trn = (values.get("trn") or "").strip()
		if not trn:
			frappe.throw(_("Enter the TRN."))
		doc = frappe.get_doc("Company", one.name)
		doc.tax_id = trn
		doc.flags.ignore_permissions = True
		doc.save()
	elif key == "emirate":
		from onedesk.one_book import vat

		address = vat.company_address(one.name)
		if address:
			doc = frappe.get_doc("Address", address)
			doc.emirate = values.get("emirate")
			doc.flags.ignore_permissions = True
			doc.save()
		else:
			vat.add_address(one.name, values.get("emirate"), values.get("address_line1"), values.get("city"))
	elif key == "close":
		from onedesk.one_book import closing

		open_ = closing.unclosed(one.name)
		if open_:
			closing.close_year(one.name, open_[0])
	elif key == "reminder":
		from onedesk.one_book.paid import REMINDER

		doc = frappe.get_doc("Notification Type", REMINDER)
		doc.enabled = 1
		doc.flags.ignore_permissions = True
		doc.save()
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
