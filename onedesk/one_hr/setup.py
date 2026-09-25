"""What a shift needs before a check-in ever becomes a day.

hrms turns `Employee Checkin` pairs into `Attendance` from one scheduled job,
and `ShiftType.has_incorrect_shift_config` makes that job return without a word
unless the shift has three things: auto attendance on, a date to process after,
and a last sync. A workspace missing one gets an empty Attendance list, empty
charts, an empty Overtime Slip and no error anywhere — the clock keeps taking
check-ins and nothing reads them.

So the three are set by the setup wizard, checked nightly against the shifts
that actually have check-ins, and offered as one button on the Shift Type form.

`auto_update_last_sync` is the fourth. Without it `last_sync_of_checkin` stays
where it was set and attendance quietly stops being processed past that moment;
with it hrms moves it forward every hour.
"""

import frappe
from frappe.utils import add_days, now_datetime, nowdate

#: How far back a shift has to have been used before its silence is worth a word.
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
			_tell(shift.name)


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


def _tell(shift: str) -> None:
	from onedesk.one import notify

	notify.notify(
		"Shift Not Reading Check-ins", _people_who_can_fix(), record=("Shift Type", shift), shift=shift
	)


def _people_who_can_fix() -> list[str]:
	return frappe.get_all(
		"Has Role",
		filters={"role": "HR Manager", "parenttype": "User"},
		pluck="parent",
		ignore_permissions=True,
	)
