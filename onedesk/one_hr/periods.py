"""The leave year and the payroll year: the company's own fiscal year, made at
setup and the next one a month before this one ends.

Nothing in HRMS makes either. Without a Leave Period, Employee Leave Balance
and the allocation tools have no year; without a Payroll Period a salary slip
cannot spread a year's tax once an Income Tax Slab exists. AGENTS.md, periods.py.
"""

import frappe
from frappe.utils import add_days, add_years, date_diff, getdate, today

#: Days before a year ends that the next one is made.
AHEAD = 30


def named(start, end) -> str:
	"""`2026` for a calendar year, `2026-2027` for one that crosses it. Pure."""
	start, end = getdate(start), getdate(end)
	return str(start.year) if start.year == end.year else f"{start.year}-{end.year}"


def year_from(start) -> tuple:
	"""The year that starts on `start`. Pure."""
	start = getdate(start)
	return start, add_days(add_years(start, 1), -1)


def in_force(company: str) -> tuple:
	"""The fiscal year today falls in, or the calendar year when there is none."""
	from erpnext.accounts.utils import get_fiscal_year

	try:
		_name, start, end = get_fiscal_year(today(), company=company)[:3]
		return getdate(start), getdate(end)
	except Exception:
		frappe.clear_last_message()
		return year_from(getdate(today()).replace(month=1, day=1))


def make(company: str, start, end) -> None:
	"""Both periods for one year, each only where none covers it yet."""
	if not frappe.db.exists(
		"Leave Period", {"company": company, "from_date": ("<=", end), "to_date": (">=", start)}
	):
		period = frappe.new_doc("Leave Period")
		period.update({"company": company, "from_date": start, "to_date": end, "is_active": 1})
		period.insert(ignore_permissions=True)
		if not frappe.db.exists("Leave Period", named(start, end)):
			frappe.rename_doc("Leave Period", period.name, named(start, end), force=True)
	if not frappe.db.exists(
		"Payroll Period", {"company": company, "start_date": ("<=", end), "end_date": (">=", start)}
	):
		period = frappe.new_doc("Payroll Period")
		period.name = named(start, end)
		period.update({"company": company, "start_date": start, "end_date": end})
		period.insert(ignore_permissions=True)


def daily() -> None:
	"""Next year's periods, once this year's end is a month away."""
	from onedesk.one_hr import holidays

	company = holidays.company()
	if not company:
		return
	last = frappe.get_all(
		"Leave Period", filters={"company": company}, fields=["to_date"], order_by="to_date desc", limit=1
	)
	if not last or date_diff(last[0].to_date, today()) > AHEAD:
		return
	start, end = year_from(add_days(last[0].to_date, 1))
	make(company, start, end)
