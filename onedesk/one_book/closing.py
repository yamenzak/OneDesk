"""Closing: locking the books up to a date, and the year-end close.
"""

import frappe
from frappe import _
from frappe.utils import add_days, add_years, getdate, nowdate


def _company() -> str:
	from erpnext import get_default_company

	return get_default_company()


def year_began(day=None, company: str | None = None):
	"""The first day of the fiscal year `day` (today) is in; the day after the
	same day last year when the books have no year for it."""
	from erpnext.accounts.utils import get_fiscal_year

	day = getdate(day or nowdate())
	found = get_fiscal_year(day, company=company or _company(), raise_on_missing=False)
	return getdate(found[1]) if found else add_days(add_years(day, -1), 1)


def locked(company: str | None = None):
	return frappe.get_cached_value("Company", company or _company(), "accounts_frozen_till_date")


@frappe.whitelist(methods=["POST"])
def lock(until: str | None = None) -> str | None:
	"""Lock the books up to and including `until`; unlock with none."""
	if not locks():
		raise frappe.PermissionError
	_lock(_company(), getdate(until) if until else None)
	return until


def _lock(company: str, until) -> None:
	"""Through the Company's own save, so ERPNext's check of pending reposts
	and `kept_to_today` run as on the form."""
	doc = frappe.get_doc("Company", company)
	doc.accounts_frozen_till_date = until
	doc.flags.ignore_permissions = True
	doc.save()


def kept_to_today(doc, method=None) -> None:
	"""Company validate: the books lock up to today at the latest, however
	the date is set (the form, a bulk edit, an import)."""
	if doc.accounts_frozen_till_date and getdate(doc.accounts_frozen_till_date) > getdate(nowdate()):
		frappe.throw(_("The books can only be locked up to today."))


def year_closed(doc, method=None) -> None:
	"""Period Closing Voucher on_submit: a closed year is a locked one, however
	the closing was made."""
	held = locked(doc.company)
	if not held or getdate(held) < getdate(doc.period_end_date):
		_lock(doc.company, doc.period_end_date)


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
	return voucher.name


def locks(user: str | None = None) -> bool:
	"""Whether somebody may lock the books: OneBook's Lock the Books
	(abilities.py)."""
	from onedesk.one import rights

	return rights.held("Accounts Settings", "books_lock", user)
