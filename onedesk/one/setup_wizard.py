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

	frappe.db.set_value("Company", company, "default_holiday_list", doc.name)
	return doc.name


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
