"""The demo company kept living on a dev site: each working morning its
people's check-outs of the day before and check-ins of the day are written,
so Home, attendance and its reports read as a working week, not the day the
demo was built. frappe's shift turns them into attendance as it would a
clock's. Nothing runs where the demo company is not."""

import random
from datetime import datetime, timedelta

import frappe
from frappe.utils import add_days, getdate, today

from onedesk.one import dev
from onedesk.one_demo.base import COMPANY

SHIFT = "Day"
WORKSHOP = (25.1379, 55.228)
WEEK = 7


def day() -> None:
	"""Daily: every working day of the last week not yet decided and with no
	leave or a day's attendance asked for, its check-in and, for a day already gone, its check-out."""
	if not dev.site() or not frappe.db.exists("Company", COMPANY) or not frappe.db.exists("Shift Type", SHIFT):
		return
	start, end = frappe.db.get_value("Shift Type", SHIFT, ["start_time", "end_time"])
	for back in range(WEEK, -1, -1):
		_day(getdate(add_days(today(), -back)), start, end, out=back > 0)
	frappe.db.commit()


def _day(when, start, end, out: bool) -> None:
	from erpnext.setup.doctype.employee.employee import is_holiday

	from onedesk.one_demo.hr import ON_SITE, SITE

	for one in frappe.get_all(
		"Employee",
		filters={"company": COMPANY, "status": "Active", "default_shift": SHIFT, "date_of_joining": ["<=", when]},
		fields=["name", "first_name"],
	):
		if is_holiday(one.name, when, raise_exception=False):
			continue
		if frappe.db.exists("Attendance", {"employee": one.name, "attendance_date": when, "docstatus": ["<", 2]}):
			continue
		if frappe.db.exists(
			"Leave Application",
			{"employee": one.name, "status": ["in", ["Approved", "Open"]], "docstatus": ["<", 2], "from_date": ["<=", when], "to_date": [">=", when]},
		):
			continue
		if frappe.db.exists(
			"Attendance Request",
			{"employee": one.name, "docstatus": ["<", 2], "from_date": ["<=", when], "to_date": [">=", when]},
		):
			continue
		pick = random.Random(f"{one.name}{when}")
		place = (SITE[1], SITE[2]) if one.first_name in ON_SITE else WORKSHOP
		_log(one.name, _at(when, start, -pick.randint(-12, 20)), "IN", place)
		if out:
			_log(one.name, _at(when, end, pick.randint(0, 25)), "OUT", place)


def _at(when, clock, minutes: int) -> datetime:
	return datetime.combine(when, datetime.min.time()) + clock + timedelta(minutes=minutes)


def _log(employee: str, at: datetime, kind: str, place: tuple) -> None:
	if frappe.db.exists("Employee Checkin", {"employee": employee, "log_type": kind, "time": ["between", [f"{at.date()} 00:00:00", f"{at.date()} 23:59:59"]]}):
		return
	frappe.get_doc(
		{"doctype": "Employee Checkin", "employee": employee, "log_type": kind, "time": at, "latitude": place[0], "longitude": place[1]}
	).insert(ignore_permissions=True)
