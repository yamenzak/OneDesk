import frappe
from frappe.utils import add_days, get_time, getdate, now_datetime, nowdate, time_diff_in_hours

from onedesk.one import registry

THEMES = {"Automatic": "Automatic", "Light": "Light", "Dark": "Dark"}

SHIFT = "Day"


def get_setup_stages(args=None):
	return [
		{
			"status": frappe._("Setting up {0}").format(registry.name("one")),
			"fail_msg": frappe._("Failed to set up {0}").format(registry.name("one")),
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
				{
					"fn": settle,
					"args": args,
					"fail_msg": frappe._("Failed to set up {0}").format(registry.name("one")),
				},
				{
					"fn": module_steps,
					"args": args,
					"fail_msg": frappe._("Failed to set up {0}").format(registry.name("one")),
				},
			],
		}
	]


@frappe.whitelist()
def setup_complete(args):
	"""frappe's own, for the workspace's administrator. Its stages save System
	Settings and the rest as whoever is signed in, and nobody on a workspace
	holds the role frappe's pages ask for (one/roles.py), so they run as
	Administrator: only while setup is unfinished, and only for somebody who
	administers it."""
	from frappe.desk.page.setup_wizard import setup_wizard as frappes

	from onedesk.one import roles

	user = frappe.session.user
	if frappe.is_setup_complete() or not roles.administers():
		return frappes.setup_complete(args)
	said = frappe.parse_json(args) if isinstance(args, str) else dict(args or {})
	said["onedesk_owner"] = user
	frappe.set_user("Administrator")
	try:
		return frappes.setup_complete(said)
	finally:
		frappe.set_user(user)


def settle(args=None):
	"""Everything an install sets up, again once the wizard has made the
	company. Much of it is about the company (its accounts, its fiscal year,
	its letter head), and a new site has none until now, so without this a
	workspace waits for its first migrate. Each is safe to run twice, and one
	that fails is logged and left to the next migrate rather than undoing the
	whole setup."""
	for method in frappe.get_hooks("after_sync", app_name="onedesk"):
		frappe.db.savepoint("one_settle")
		try:
			frappe.get_attr(method)()
		except Exception:
			frappe.db.rollback(save_point="one_settle")
			frappe.log_error(f"setup: {method}")


def module_steps(args=None):
	"""Each module's steps given in the wizard (one/setup_steps.py)."""
	from onedesk.one import setup_steps

	setup_steps.apply(args)


def set_appearance(args):
	chosen = THEMES.get((args or {}).get("onedesk_theme", ""))
	if not chosen:
		return
	frappe.db.set_value("User", args.get("onedesk_owner") or frappe.session.user, "desk_theme", chosen)


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
	holidays = _holiday_list(company, days_off(args.get("onedesk_weekly_off")))

	hours = time_diff_in_hours(f"{nowdate()} {get_time(ends)}", f"{nowdate()} {get_time(starts)}")
	frappe.db.set_single_value("HR Settings", "standard_working_hours", abs(hours))
	# Nobody answers their own leave or claim; hrms writes these off at install.
	for switch in ("prevent_self_leave_approval", "prevent_self_expense_approval"):
		frappe.db.set_single_value("HR Settings", switch, 1)

	_shift(starts, ends, holidays)
	if company:
		from onedesk.one_hr import periods

		start, end = (
			periods.year_from(args["fy_start_date"]) if args.get("fy_start_date") else periods.in_force(company)
		)
		periods.make(company, start, end)


def days_off(said) -> list[str]:
	"""The week's days off as the slide sends them: a list of day names, or
	one name as an older wizard did. Pure."""
	if isinstance(said, str):
		said = frappe.parse_json(said) if said.startswith("[") else [said]
	return [one for one in (said or []) if one in WEEK]


WEEK = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def weekends() -> dict:
	"""Each country's usual days off, by the name the wizard's country field
	holds, from the `holidays` package; the slide ticks them. Cached, since it
	reads every country."""
	return frappe.cache.get_value("one_weekends", generator=_weekends)


def _weekends() -> dict:
	from holidays import country_holidays

	out = {}
	for name, code in frappe.get_all("Country", fields=["name", "code"], as_list=True):
		try:
			out[name] = [WEEK[one] for one in sorted(country_holidays((code or "").upper()).weekend)]
		except Exception:
			continue
	return out


def _holiday_list(company: str | None, weekly_offs: list[str]) -> str | None:
	"""The company's first list, put in force. HRMS's own setup stage, which
	runs first, makes it for the company's first financial year with the
	country's usual days off; here it takes the days off chosen on the
	working-day slide, and its public holidays named in the reader's language
	(one_hr/holidays.py, `local`). Without HRMS's, this year's is made."""
	if not company:
		return None
	from onedesk.one_hr import holidays

	name = frappe.db.get_value("Company", company, "default_holiday_list")
	if not name:
		name = holidays.make(company, getdate(nowdate()).year, weekly_offs, _country_code(company))
	else:
		doc = frappe.get_doc("Holiday List", name)
		country = doc.country or _country_code(company)
		if country:
			try:
				named = holidays.local(country, doc.subdivision, doc.from_date, doc.to_date)
				doc.set("holidays", [one for one in doc.holidays if one.weekly_off])
				for one in named:
					doc.append("holidays", {**one, "weekly_off": 0})
			except Exception:
				frappe.log_error(f"public holidays for {country}")
		holidays.set_days_off(doc, weekly_offs)
		doc.flags.ignore_permissions = True
		doc.save()
	holidays.assign(name, company)
	return name


def _country_code(company: str) -> str | None:
	country = frappe.db.get_value("Company", company, "country")
	code = frappe.db.get_value("Country", country, "code") if country else None
	return code.upper() if code else None


def _shift(starts, ends, holidays: str | None) -> None:
	"""A shift that reads its check-ins. See `one_hr/shift_setup.py` for why."""
	existing = frappe.db.exists("Shift Type", SHIFT)
	doc = frappe.get_doc("Shift Type", SHIFT) if existing else frappe.new_doc("Shift Type")

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
