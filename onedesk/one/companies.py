"""What a company after the first needs before it pays payroll and sends an
invoice, done by setup_job.company once erpnext has built its chart and hrms
its payroll accounts: the financial year it is in, its holiday list and
leave and payroll periods, an account on every salary component, and its
letter head. The demo's Sahara Glass Saudi needed each of these by hand
(one_demo/branch.py)."""

from datetime import date

import frappe
from frappe.utils import getdate, nowdate

from onedesk.one import setup_answers

LETTER_HEADS = ("own", "first")
"""A new letter head with the company's name, or the first company's."""


def ready(company: str, said: dict, days_off: list | None = None) -> None:
	"""Everything above for a company just made. `said` is the company as the
	answers give it; `days_off`, the week's, else its country's usual."""
	from onedesk.one import setup_wizard
	from onedesk.one_hr import periods

	_year(company, said.get("year_starts"))
	off = days_off if days_off is not None else setup_wizard.weekends().get(said["country"]) or []
	setup_wizard.holiday_list(company, setup_wizard.days_off(off))
	periods.make(company, *periods.in_force(company))
	_components(company)
	_letter_head(company, said.get("letter_head") or LETTER_HEADS[0])


def join(company: str, parent: str) -> None:
	"""The company in the group of `parent`, which becomes a group company if
	it is not one yet, as erpnext's company tree keeps them. Written to the
	tree, not saved through the form: erpnext's save marks a company with a
	parent as charted from it, and each keeps its own chart. Once."""
	from frappe.utils.nestedset import rebuild_tree

	if frappe.db.get_value("Company", company, "parent_company") == parent:
		return
	if not frappe.db.get_value("Company", parent, "is_group"):
		frappe.db.set_value("Company", parent, "is_group", 1)
	frappe.db.set_value("Company", company, "parent_company", parent)
	rebuild_tree("Company")
	frappe.clear_cache(doctype="Company")


def starts_of(year_start: date | None) -> str | None:
	"""A financial year's first day as the answers say it, MM-DD. Pure."""
	return year_start.strftime("%m-%d") if year_start else None


def year_name(start: date, end: date, abbr: str, taken: set | frozenset = frozenset()) -> str:
	"""A financial year's name as erpnext's wizard gives it, `2026` or
	`2026-2027`, with the company's abbreviation after it when another year
	has that name. Pure."""
	name = str(start.year) if start.year == end.year else f"{start.year}-{end.year}"
	return name if name not in taken else f"{name} {abbr}"


def _first_start() -> str | None:
	from onedesk.one.company import workspace_company

	from erpnext.accounts.utils import get_fiscal_year

	held = get_fiscal_year(nowdate(), company=workspace_company(), raise_on_missing=False)
	return starts_of(getdate(held[1])) if held else None


def _year(company: str, starts: str | None) -> None:
	"""The financial year today is in, starting where the answers say or
	where the first company's does: the one there is, naming this company
	too when it names its companies, or a new one for this company alone."""
	start, end = setup_answers.fiscal_year(starts or _first_start(), getdate(nowdate()))
	for name in frappe.get_all("Fiscal Year", filters={"year_start_date": start, "year_end_date": end, "disabled": 0}, pluck="name"):
		year = frappe.get_doc("Fiscal Year", name)
		named = {row.company for row in year.companies}
		if named and company not in named:
			year.append("companies", {"company": company})
			year.save(ignore_permissions=True)
		return
	abbr = frappe.db.get_value("Company", company, "abbr")
	frappe.get_doc(
		{
			"doctype": "Fiscal Year",
			"year": year_name(start, end, abbr, set(frappe.get_all("Fiscal Year", pluck="name"))),
			"year_start_date": start,
			"year_end_date": end,
			"companies": [{"company": company}],
		}
	).insert(ignore_permissions=True)


def _components(company: str) -> None:
	"""Every salary component the company has no account on gets the account
	of the same name the first company's row books to, and an earning with
	neither its Salary account (one_hr/accounts.py), or a payroll run makes
	the slips and never submits them."""
	for name in frappe.get_all("Salary Component", pluck="name"):
		doc = frappe.get_doc("Salary Component", name)
		if any(row.company == company for row in doc.accounts):
			continue
		account = next(filter(None, (_same(row.account, company) for row in doc.accounts)), None)
		if account:
			doc.append("accounts", {"company": company, "account": account})
		elif doc.type != "Earning":
			continue
		doc.save(ignore_permissions=True)


def _same(account: str | None, company: str) -> str | None:
	named = account and frappe.db.get_value("Account", account, "account_name")
	return named and frappe.db.get_value("Account", {"company": company, "account_name": named, "is_group": 0})


def _letter_head(company: str, chosen: str) -> None:
	"""The company's default letter head: the first company's when asked and
	there is one, else a new one drawn with this company's name. A drawn top
	follows the workspace's company (one_studio/letter_heads.redraw), so this
	one is kept as plain HTML."""
	from onedesk.one.company import workspace_company
	from onedesk.one_studio import letter_heads

	head = None
	if chosen == "first":
		first = workspace_company()
		head = (first and first != company and frappe.db.get_value("Company", first, "default_letter_head")) or frappe.db.get_value(
			"Letter Head", {"is_default": 1, "disabled": 0}
		)
	if not head:
		name = frappe.db.get_value("Company", company, "company_name")
		head = name
		if not frappe.db.exists("Letter Head", name):
			frappe.get_doc(
				{
					"doctype": "Letter Head",
					"letter_head_name": name,
					"source": "HTML",
					"content": letter_heads.draw(None, {"name": name, "colour": letter_heads.INK}),
				}
			).insert(ignore_permissions=True)
	frappe.db.set_value("Company", company, "default_letter_head", head)
