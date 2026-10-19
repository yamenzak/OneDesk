"""The old roll-call, one JSON a day, as one Attendance per person per day:
present (late when it said so), absent, or on leave. A day an approved
leave already covers keeps the leave. A working day the roll-call never
took is left unmarked, and each run of them is listed: the old app had
weeks with nobody marked at all."""

import json

import frappe
from frappe.utils import add_days, getdate

from rua.importer.people import ANNUAL, EMPLOYEE

ROLL = "RUA Attendance"
BATCH = 500


def run(run_):
	people = {}
	for old in run_.docs(EMPLOYEE):
		made = run_.made(EMPLOYEE, old["name"], "Employee")
		if made:
			people[old["name"]] = (made, getdate(frappe.db.get_value("Employee", made, "date_of_joining")))
	marked = {
		(row.employee, getdate(row.attendance_date))
		for row in frappe.get_all(
			"Attendance", filters={"docstatus": 1}, fields=["employee", "attendance_date"], limit=0
		)
	}
	days = sorted(run_.docs(ROLL), key=lambda one: one.get("date") or "")
	count = 0
	for day in days:
		when = getdate(day.get("date"))
		log = day.get("attendance_log")
		log = json.loads(log) if isinstance(log, str) else (log or {})
		for old, said in log.items():
			if old not in people or not isinstance(said, dict):
				continue
			employee, joined = people[old]
			status = state(said)
			if not status or when < joined or (employee, when) in marked:
				continue
			mark(run_, employee, when, status, said)
			marked.add((employee, when))
			count += 1
			if count % BATCH == 0:
				frappe.db.commit()
	gaps(run_, days)


def state(said) -> str | None:
	"""What one person's line on the roll-call says. Pure."""
	if said.get("status") == "leave":
		return "On Leave"
	if said.get("present") or said.get("late"):
		return "Present"
	if said.get("absent"):
		return "Absent"
	return None


def mark(run_, employee, when, status, said):
	doc = frappe.get_doc(
		{
			"doctype": "Attendance",
			"employee": employee,
			"attendance_date": when,
			"status": status,
			"company": run_.company,
			"late_entry": 1 if said.get("late") else 0,
			"leave_type": ANNUAL if status == "On Leave" else None,
			"docstatus": 1,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()


def gaps(run_, days):
	"""Each run of working days between the first roll-call and the last that
	has none, as one note."""
	taken = {getdate(one.get("date")) for one in days if one.get("date")}
	if not taken:
		return
	off = {
		getdate(one.holiday_date)
		for one in frappe.get_all(
			"Holiday", filters={"parent": "Rua Holidays"}, fields=["holiday_date"], limit=0
		)
	}
	day, last, start = min(taken), max(taken), None
	while day <= last:
		missing = day not in taken and day not in off
		if missing and not start:
			start = day
		if not missing and start:
			run_.note(
				"Attendance Not Marked",
				None,
				None,
				"No roll-call "
				+ (f"on {start}" if start == add_days(day, -1) else f"from {start} to {add_days(day, -1)}")
				+ ": nobody is marked",
			)
			start = None
		day = add_days(day, 1)
