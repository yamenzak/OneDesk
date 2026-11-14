"""Facts every trigger may test, whatever its module: whether it is now
outside the workspace's working day, and whether today is a day off."""

import frappe
from frappe.utils import get_time, now_datetime, today


def holiday_today() -> bool:
	"""Whether today is a day off on the company's holiday list, weekly days
	off included."""
	from onedesk.one_hr import holidays

	held = holidays.in_force()
	return bool(held and frappe.db.exists("Holiday", {"parent": held, "holiday_date": today()}))


def after_hours() -> bool:
	"""Whether it is now outside the workspace's working day, the hours of its
	shift (one/setup_wizard.py SHIFT)."""
	from onedesk.one.setup_wizard import SHIFT

	hours = frappe.db.get_value("Shift Type", SHIFT, ["start_time", "end_time"])
	if not hours or not all(hours):
		return False
	return outside(now_datetime().time(), get_time(hours[0]), get_time(hours[1]))


def outside(now, start, end) -> bool:
	"""Whether a time is outside a working day from start to end, one that
	runs past midnight too. Pure."""
	return not (start <= now < end) if start < end else end <= now < start
