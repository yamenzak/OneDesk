import frappe
from frappe.utils import add_days, get_time, getdate, now_datetime, nowdate, time_diff_in_hours

#: What the wizard's Appearance field offers, against `User.desk_theme`.
THEMES = {"Automatic": "Automatic", "Light": "Light", "Dark": "Dark"}

#: The shift a site starts with. One shift is what most workspaces have, and a
#: second one is a thing somebody adds rather than a thing everybody configures.
SHIFT = "Day"


def get_setup_stages(args=None):
	return [
		{
			"status": frappe._("Setting up One"),
			"fail_msg": frappe._("Failed to set up One"),
			"tasks": [
				{
					"fn": set_appearance,
					"args": args,
					"fail_msg": frappe._("Failed to set the appearance"),
				},
				{
					"fn": set_the_working_day,
					"args": args,
					"fail_msg": frappe._("Failed to set the working day"),
				},
			],
		}
	]


def set_appearance(args):
	chosen = THEMES.get((args or {}).get("onedesk_theme", ""))
	if not chosen:
		return
	frappe.db.set_value("User", frappe.session.user, "desk_theme", chosen)


def set_the_working_day(args):
	"""The hours, the week's day off, the public holidays, and a shift that reads.

	All four are the same answer asked once. Without the holiday list a Sunday
	counts as absent; without the hours every hour of a shiftless day is
	overtime; and without the three settings on the shift no check-in ever
	becomes attendance. Asking at setup is the difference between a clock that
	works on the first morning and one somebody has to be told about.
	"""
	args = args or {}
	starts = args.get("onedesk_day_starts")
	ends = args.get("onedesk_day_ends")
	if not (starts and ends):
		return

	company = args.get("company_name") or frappe.db.get_value("Company", {}, "name")
	holidays = _holiday_list(company, args.get("onedesk_weekly_off"))

	hours = time_diff_in_hours(f"{nowdate()} {get_time(ends)}", f"{nowdate()} {get_time(starts)}")
	frappe.db.set_single_value("HR Settings", "standard_working_hours", abs(hours))

	_shift(starts, ends, holidays)
	_leave_period(company, holidays)
	_payroll_period(company)


def _leave_period(company: str | None, holidays: str | None) -> None:
	"""This calendar year, so leave has a year to be counted against.

	Nothing in HRMS creates one and four things need it. `Employee Leave Balance`
	asks `get_leave_period` for the dates to run between, gets `None`, and its
	`onload` dies on `data.message[0]` — so both mandatory date filters stay
	empty and the report shows nothing at all, with no hint why. Leave Policy
	Assignment and the two allocation tools want one too.

	The calendar year rather than a financial one: a leave year that is not the
	calendar year is a decision a workspace makes deliberately, and this is the
	answer for everybody who has not made it.
	"""
	if not company or frappe.db.exists("Leave Period", {"company": company, "is_active": 1}):
		return

	year = getdate().year
	period = frappe.new_doc("Leave Period")
	period.company = company
	period.from_date = f"{year}-01-01"
	period.to_date = f"{year}-12-31"
	period.is_active = 1
	period.optional_holiday_list = holidays
	period.insert(ignore_permissions=True)

	# Named for its year rather than left as HR-LPR-2026-00001. Leave Period is
	# a Link on Leave Policy Assignment, Leave Encashment and three report
	# filters, and none of them has a title field to read instead, so the serial
	# is what a person sees in all five places.
	frappe.rename_doc("Leave Period", period.name, str(year), force=True)


def _payroll_period(company: str | None) -> None:
	"""The same calendar year again, for the other half of the framework.

	Nothing in HRMS creates a Payroll Period either, and a salary slip asks for
	one the moment a workspace has an Income Tax Slab: `Salary Slip.payroll_period`
	is `get_payroll_period(start, end, company)`, and without one there is no
	period to spread a year's tax across. Its autoname is `Prompt`, so unlike the
	leave period this one is named at birth rather than renamed after.
	"""
	if not company:
		return
	year = getdate().year
	if frappe.db.exists("Payroll Period", {"company": company, "start_date": f"{year}-01-01"}):
		return

	period = frappe.new_doc("Payroll Period")
	period.name = str(year)
	period.company = company
	period.start_date = f"{year}-01-01"
	period.end_date = f"{year}-12-31"
	period.insert(ignore_permissions=True)


def _holiday_list(company: str | None, weekly_off: str | None) -> str | None:
	"""This year's list: the week's day off, plus the country's public holidays.

	The public holidays come from erpnext's own `get_local_holidays`, which
	reads the `holidays` package by country code. A country it does not know
	leaves the list with the weekly off alone, which is still better than a
	workspace where every Sunday is an absence.
	"""
	if not (company and weekly_off):
		return None

	year = getdate(nowdate()).year
	name = f"{company} {year}"
	if frappe.db.exists("Holiday List", name):
		return name

	doc = frappe.new_doc("Holiday List")
	doc.holiday_list_name = name
	doc.from_date = f"{year}-01-01"
	doc.to_date = f"{year}-12-31"
	doc.weekly_off = weekly_off
	doc.country = _country_code(company)
	doc.get_weekly_off_dates()
	if doc.country:
		try:
			doc.get_local_holidays()
		except Exception:
			frappe.clear_last_message()
	doc.insert(ignore_permissions=True)

	_assign(doc.name, company, f"{year}-01-01")
	return doc.name


def _assign(holidays: str, company: str, from_date: str) -> None:
	"""Tell hrms about the list, which is not the same as telling erpnext.

	`hrms.utils.holiday_list.get_holiday_list_for_employee` replaces erpnext's
	lookup through the `employee_holiday_list` hook, and reads neither
	`Employee.holiday_list` nor `Company.default_holiday_list`: only a
	submitted `Holiday List Assignment`. Without one, every question about
	whether a date is a holiday throws — leave, attendance requests, and the
	shift's own processing. `Company.default_holiday_list` is set as well,
	because erpnext's own reports still read it.
	"""
	frappe.db.set_value("Company", company, "default_holiday_list", holidays)

	if frappe.db.exists("Holiday List Assignment", {"assigned_to": company, "docstatus": 1}):
		return

	doc = frappe.new_doc("Holiday List Assignment")
	doc.holiday_list = holidays
	doc.applicable_for = "Company"
	doc.assigned_to = company
	doc.from_date = from_date
	doc.insert(ignore_permissions=True)
	doc.submit()


def _country_code(company: str) -> str | None:
	country = frappe.db.get_value("Company", company, "country")
	code = frappe.db.get_value("Country", country, "code") if country else None
	return code.upper() if code else None


def _shift(starts, ends, holidays: str | None) -> None:
	"""A shift that reads its check-ins. See `one_hr/setup.py` for why."""
	existing = frappe.db.exists("Shift Type", SHIFT)
	doc = frappe.get_doc("Shift Type", SHIFT) if existing else frappe.new_doc("Shift Type")

	# `Shift Type` is named by prompt, so a new one is named here.
	doc.name = SHIFT
	doc.start_time = starts
	doc.end_time = ends
	doc.holiday_list = holidays or doc.holiday_list
	doc.enable_auto_attendance = 1
	doc.auto_update_last_sync = 1
	doc.process_attendance_after = add_days(nowdate(), -1)
	doc.last_sync_of_checkin = now_datetime()

	if existing:
		doc.save(ignore_permissions=True)
	else:
		doc.insert(ignore_permissions=True)
