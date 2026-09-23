"""Closing: locking the books up to a date, and the year-end close.

**The lock** is ERPNext's own — nothing is posted, edited or cancelled on or
before `Company.accounts_frozen_till_date` (accounts/services/gl_validator.py
`check_freezing_date`) — but it sits on a tab of the Company form beside a
role that may post anyway, and nothing leads there. **Lock Books** on the VAT
Return sets it to the end of the period just filed, since a period that has
been filed is not to change; the Books Check says where it stands. Locking leaves the role
empty, so locked means locked for everybody, the Administrator too; to
correct a locked period, unlock it, correct, and lock again.

**The year-end close** is ERPNext's Period Closing Voucher, which moves the
year's profit to an equity account and asks which. OneBook answers: the
chart's Retained Earnings. The Books Check notices a year that has ended with
entries in it and no closing, and **Close the Year** makes and submits the
voucher, then locks the books to the year's last day. ERPNext posts it in the
background.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate

#: Who may lock, unlock and close.
CLOSERS = ("Accounts Manager", "Workspace Administrator")


def _company() -> str:
	from erpnext import get_default_company

	return get_default_company()


def locked(company: str | None = None):
	return frappe.get_cached_value("Company", company or _company(), "accounts_frozen_till_date")


@frappe.whitelist(methods=["POST"])
def lock(until: str | None = None) -> str | None:
	"""Lock the books up to and including `until`; unlock with none."""
	frappe.only_for(CLOSERS)
	company = _company()
	if until and getdate(until) > getdate(nowdate()):
		frappe.throw(_("The books can only be locked up to today."))
	frappe.db.set_value("Company", company, "accounts_frozen_till_date", getdate(until) if until else None)
	frappe.clear_document_cache("Company", company)
	return until


def retained_earnings(company: str) -> str:
	found = frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "root_type": "Equity", "account_name": ["like", "Retained Earnings%"]},
		pluck="name",
		limit=1,
	) or frappe.get_all(
		"Account", filters={"company": company, "is_group": 0, "root_type": "Equity", "account_type": "Equity"}, pluck="name", limit=1
	)
	if not found:
		frappe.throw(_("The chart of accounts has no equity account to close the year into."))
	return found[0]


def unclosed(company: str) -> list[dict]:
	"""Years that have ended, have entries, and have no submitted closing,
	oldest first."""
	years = frappe.get_all(
		"Fiscal Year",
		filters={"year_end_date": ["<", nowdate()], "disabled": 0},
		fields=["name", "year_start_date", "year_end_date"],
		order_by="year_start_date asc",
	)
	return [
		year
		for year in years
		if not frappe.db.exists("Period Closing Voucher", {"fiscal_year": year.name, "company": company, "docstatus": 1})
		and frappe.db.exists(
			"GL Entry",
			{"company": company, "is_cancelled": 0, "posting_date": ["between", [year.year_start_date, year.year_end_date]]},
		)
	]


def close_year(company: str, year: dict) -> str:
	"""ERPNext's Period Closing Voucher for the year, into Retained Earnings,
	then the books locked to its last day."""
	start = year.year_start_date
	earlier = frappe.get_all(
		"Period Closing Voucher",
		filters={"fiscal_year": year.name, "company": company, "docstatus": 1},
		fields=["period_end_date"],
		order_by="period_end_date desc",
		limit=1,
	)
	if earlier:
		start = add_days(earlier[0].period_end_date, 1)
	voucher = frappe.get_doc(
		{
			"doctype": "Period Closing Voucher",
			"company": company,
			"fiscal_year": year.name,
			"transaction_date": year.year_end_date,
			"period_start_date": start,
			"period_end_date": year.year_end_date,
			"closing_account_head": retained_earnings(company),
			"remarks": _("Year-end close of {0}").format(year.name),
		}
	)
	voucher.insert()
	voucher.submit()
	if not locked(company) or getdate(locked(company)) < getdate(year.year_end_date):
		frappe.db.set_value("Company", company, "accounts_frozen_till_date", year.year_end_date)
		frappe.clear_document_cache("Company", company)
	return voucher.name
