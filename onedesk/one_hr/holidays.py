"""The workspace's holidays: which list is in force, next year's, and who hears.

Choosing a list both assigns it for hrms and sets the company's default for
erpnext (`use`), so the two never disagree.
"""

from collections import Counter

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, today

from onedesk.one import roles, tell
from onedesk.one.company import workspace_company

WARN = (60, 30, 7)


def assignments(held: str | None = None) -> list:
	"""The company's own assignments, oldest first: which list, from when."""
	held = held or workspace_company()
	if not held:
		return []
	return frappe.get_all(
		"Holiday List Assignment",
		filters={"applicable_for": "Company", "assigned_to": held, "docstatus": 1},
		fields=["name", "holiday_list", "from_date"],
		order_by="from_date asc",
	)


def assigned(day=None, held: str | None = None) -> str | None:
	"""The list hrms holds the company to on a day: the last assignment started
	by then, else the first one (hrms's resolve_holiday_list_assignment)."""
	held = held or workspace_company()
	day = getdate(day or today())
	found = assignments(held)
	started = [one for one in found if getdate(one.from_date) <= day]
	if started:
		return started[-1].holiday_list
	return found[0].holiday_list if found else None


def in_force(day=None, held: str | None = None) -> str | None:
	"""The list shown as in force on a day: the one assigned, else the
	company's field, until an assignment is made."""
	held = held or workspace_company()
	found = assigned(day, held)
	if found:
		return found
	return frappe.db.get_value("Company", held, "default_holiday_list") if held else None


def after(holiday_list: str, held: str | None = None) -> str | None:
	"""The list assigned to start after this one ends, if any."""
	end = frappe.db.get_value("Holiday List", holiday_list, "to_date")
	later = [one for one in assignments(held) if end and getdate(one.from_date) > getdate(end)]
	return later[0].holiday_list if later else None


def covering(day, held: str | None = None) -> str | None:
	"""The company's list whose dates hold a day, if any."""
	day = getdate(day)
	for name in lists(held):
		start, end = frappe.db.get_value("Holiday List", name, ["from_date", "to_date"])
		if getdate(start) <= day <= getdate(end):
			return name
	return None


def lists(held: str | None = None) -> list[str]:
	"""Every list the company has been given, and its field's."""
	held = held or workspace_company()
	named = [one.holiday_list for one in assignments(held)]
	own = frappe.db.get_value("Company", held, "default_holiday_list") if held else None
	return list(dict.fromkeys([*named, *([own] if own else [])]))


def all_dates(held: str | None = None) -> set:
	"""Every day off on any of the company's lists."""
	named = lists(held)
	return (
		set(frappe.get_all("Holiday", filters={"parent": ["in", named]}, pluck="holiday_date"))
		if named
		else set()
	)


def public(start, end, held: str | None = None) -> list:
	"""The public holidays between two days, each from the list in force on
	it, without the week's days off."""
	named = lists(held)
	if not named:
		return []
	rows = frappe.get_all(
		"Holiday",
		filters=[
			["parent", "in", named],
			["weekly_off", "=", 0],
			["holiday_date", "between", [getdate(start), getdate(end)]],
		],
		fields=["name", "parent", "holiday_date", "description"],
		order_by="holiday_date asc",
	)
	return [one for one in rows if in_force(one.holiday_date, held) == one.parent]


WEEK = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def days_off(doc) -> list[str]:
	"""The week's days off, as the rows say them: every weekday most of whose
	dates in the list are days off. erpnext keeps one `weekly_off` and writes
	its rows; a weekend of two is two runs of it (`set_days_off`)."""
	counted = Counter(getdate(one.holiday_date).strftime("%A") for one in doc.holidays if one.weekly_off)
	start, end = getdate(doc.from_date), getdate(doc.to_date)
	weeks = max(1, ((end - start).days + 1) // 7)
	found = [day for day in WEEK if counted.get(day, 0) * 2 >= weeks]
	return found or ([doc.weekly_off] if doc.weekly_off else [])


def set_days_off(doc, days: list[str]) -> None:
	"""The week's days off made again: every weekly row goes, and each day's
	dates are written by erpnext's own `get_weekly_off_dates`, which leaves a
	date that is already a holiday as it is."""
	doc.set("holidays", [one for one in doc.holidays if not one.weekly_off])
	for day in [one for one in WEEK if one in (days or [])]:
		doc.weekly_off = day
		doc.get_weekly_off_dates()


def assign(holiday_list: str, held: str | None = None) -> bool:
	"""Put a list in force for the company, as hrms reads it: from today when
	the list covers today, else from its first day. False when it already is."""
	held = held or workspace_company()
	start, end = frappe.db.get_value("Holiday List", holiday_list, ["from_date", "to_date"])
	day = getdate(today()) if getdate(start) <= getdate(today()) <= getdate(end) else getdate(start)
	if assigned(day, held) == holiday_list:
		_follow(held)
		return False
	same_day = frappe.db.get_value(
		"Holiday List Assignment",
		{"applicable_for": "Company", "assigned_to": held, "from_date": day, "docstatus": 1},
	)
	if same_day:
		frappe.get_doc("Holiday List Assignment", same_day).cancel()
	doc = frappe.new_doc("Holiday List Assignment")
	doc.update(
		{"holiday_list": holiday_list, "applicable_for": "Company", "assigned_to": held, "from_date": day}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	doc.submit()
	_follow(held)
	return True


def _follow(held: str) -> None:
	"""erpnext's field follows the list in force today."""
	now = in_force(held=held)
	if now and frappe.db.get_value("Company", held, "default_holiday_list") != now:
		frappe.db.set_value("Company", held, "default_holiday_list", now)


def make(
	held: str, year: int, weekly_offs: list[str], country: str | None, subdivision: str | None = None
) -> str:
	"""A year's list: the days off, and the country's public holidays in the
	reader's language (`local`). A country the `holidays` package does not
	know gets the days off alone."""
	name = f"{held} {year}"
	if frappe.db.exists("Holiday List", name):
		return name
	doc = frappe.new_doc("Holiday List")
	doc.update(
		{
			"holiday_list_name": name,
			"from_date": f"{year}-01-01",
			"to_date": f"{year}-12-31",
			"country": country,
			"subdivision": subdivision,
		}
	)
	if country:
		try:
			for one in local(country, subdivision, doc.from_date, doc.to_date):
				doc.append("holidays", {**one, "weekly_off": 0})
		except Exception:
			frappe.log_error(f"public holidays for {country}")
	set_days_off(doc, weekly_offs)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


@frappe.whitelist(methods=["POST"])
def next_year() -> str:
	"""Next year's list, made from the one in force and put in force from its
	first day; or the one already there."""
	roles.require()
	held = workspace_company()
	now = in_force(held=held)
	if not now:
		frappe.throw(_("There is no holiday list to start from."))
	doc = frappe.get_doc("Holiday List", now)
	waiting = after(now, held)
	if waiting:
		return waiting
	name = make(held, getdate(doc.to_date).year + 1, days_off(doc), doc.country, doc.subdivision)
	assign(name, held)
	tell.holidays_changed(_("made next year's list, {0}").format(name), name)
	return name


@frappe.whitelist(methods=["POST"])
def use(holiday_list: str) -> str:
	"""Another list for the whole workspace, from today or from its first day."""
	roles.require()
	if not frappe.db.exists("Holiday List", holiday_list):
		frappe.throw(_("There is no holiday list {0}.").format(holiday_list))
	if assign(holiday_list):
		tell.holidays_changed(_("made {0} the holiday list for everyone").format(holiday_list), holiday_list)
	return holiday_list


@frappe.whitelist()
def country_holidays(
	country: str, from_date: str, to_date: str, subdivision: str | None = None
) -> list[dict]:
	"""The country's public holidays between two days, in the reader's
	language, for the page to add to its table. Nothing is saved."""
	roles.require()
	return local(country, subdivision, from_date, to_date)


def local(country: str, subdivision: str | None, from_date, to_date) -> list[dict]:
	"""The country's public holidays between two days, named in the reader's
	language where the `holidays` package has it.

	Ours rather than erpnext's `get_local_holidays`, which passes frappe's
	language code as it is: the package knows English as `en_US`, so `en`
	fell back to the country's own language and an English reader in the
	Emirates got every holiday in Arabic."""
	from holidays import country_holidays as named

	start, end = getdate(from_date), getdate(to_date)
	offered = named(country, subdiv=subdivision or None, years=start.year).supported_languages or ()
	lang = (frappe.local.lang or "en").replace("-", "_")
	language = next((one for one in offered if one == lang), None) or next(
		(one for one in offered if one.split("_")[0] == lang.split("_")[0]), None
	)
	found = named(
		country, subdiv=subdivision or None, years=list(range(start.year, end.year + 1)), language=language
	)
	return [
		{"holiday_date": str(day), "description": name}
		for day, name in sorted(found.items())
		if start <= day <= end
	]


@frappe.whitelist()
def subdivisions(country: str) -> list[str]:
	from holidays.utils import list_supported_countries

	return list(list_supported_countries().get(country) or [])


def countries() -> list[dict]:
	"""Every country the `holidays` package knows, by its name."""
	from erpnext.setup.doctype.holiday_list.holiday_list import local_country_name
	from holidays.utils import list_supported_countries

	return sorted(
		({"value": code, "label": local_country_name(code)} for code in list_supported_countries()),
		key=lambda one: one["label"],
	)


def elsewhere(held: str | None = None) -> int:
	"""People on a list of their own rather than the company's."""
	return len(
		set(
			frappe.get_all(
				"Holiday List Assignment",
				filters={"applicable_for": "Employee", "docstatus": 1},
				pluck="assigned_to",
			)
		)
	)


def daily() -> None:
	"""The company's field follows the list in force, and a list about to end
	with nothing after it is told."""
	held = workspace_company()
	if not held:
		return
	_follow(held)
	now = in_force(held=held)
	if not now or after(now, held):
		return
	end = frappe.db.get_value("Holiday List", now, "to_date")
	left = date_diff(end, today())
	if left in WARN:
		tell.holidays_run_out_soon(now, end, left)
