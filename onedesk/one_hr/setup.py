"""What a shift needs before a check-in ever becomes a day."""

import frappe
from frappe.utils import add_days, now_datetime, nowdate

from onedesk.one_hr import tell

WINDOW_DAYS = 7


def reads_checkins(shift: dict) -> bool:
	"""The same three `has_incorrect_shift_config` asks for."""
	return bool(
		shift.get("enable_auto_attendance")
		and shift.get("process_attendance_after")
		and shift.get("last_sync_of_checkin")
	)


def deaf_shifts() -> list[frappe._dict]:
	"""Shifts with recent check-ins that the attendance job will not read."""
	used = frappe.get_all(
		"Employee Checkin",
		filters={"time": [">=", add_days(nowdate(), -WINDOW_DAYS)], "shift": ["is", "set"]},
		pluck="shift",
		ignore_permissions=True,
	)
	if not used:
		return []

	shifts = frappe.get_all(
		"Shift Type",
		filters={"name": ["in", list(set(used))]},
		fields=["name", "enable_auto_attendance", "process_attendance_after", "last_sync_of_checkin"],
		ignore_permissions=True,
	)
	return [shift for shift in shifts if not reads_checkins(shift)]


@frappe.whitelist(methods=["POST"])
def start_reading(shift: str) -> None:
	"""Set the three, and let hrms keep the sync moving."""
	frappe.has_permission("Shift Type", "write", doc=shift, throw=True)

	doc = frappe.get_doc("Shift Type", shift)
	doc.enable_auto_attendance = 1
	doc.auto_update_last_sync = 1
	doc.process_attendance_after = doc.process_attendance_after or nowdate()
	doc.last_sync_of_checkin = doc.last_sync_of_checkin or now_datetime()
	doc.save()


def nightly() -> None:
	"""One notification per silent shift, to whoever can fix it.

	Once a week rather than every night: a broken setting is worth saying and
	not worth saying seven times before anybody reads it.
	"""
	for shift in deaf_shifts():
		if not _told_recently(shift.name):
			tell.shift_not_reading(shift.name)


def _told_recently(shift: str) -> bool:
	return bool(
		frappe.db.exists(
			"Notification Log",
			{
				"document_type": "Shift Type",
				"document_name": shift,
				"creation": [">=", add_days(nowdate(), -WINDOW_DAYS)],
			},
		)
	)
