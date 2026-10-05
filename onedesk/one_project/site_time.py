"""Attendance on site: each day somebody's attendance has them at a
project's site is a day on the project (hours.py, Attendance on Site).

HRMS's attendance says who worked and for how long, for payroll; it has no
project. ERPNext's project costing reads only timesheets. So a day on site is
written as the timesheet ERPNext expects, made from the attendance, and HR
keeps attendance as it is:

- **Attendance submitted** (`attended`): when the day was at the site of an
  open project counted by attendance (`project_at`), a Timesheet for that
  person is made and submitted. It has one row on the project, the
  attendance's working hours (or HR Settings' standard day, half of it for a
  Half Day), at Projects Settings' **Activity for Days on Site**, billable
  when the project bills hours (`hours.bills_hours`). Its cost is the person's
  Activity Cost, as any timesheet's.
- **Where they were**: one of their check-ins that day inside the site (its
  own circle, or any clock place drawn on it). With no position on any
  check-in, a shift assignment that day naming the site.
- **Attendance cancelled** (`cancelled`): its timesheet is cancelled too,
  unless it's already invoiced, which ERPNext refuses.
- A timesheet made here names its attendance (`one_attendance`), so neither
  is made twice.

A day that can't be written (a timesheet already covering those hours, say)
doesn't stop the attendance. It's logged in the Error Log for HR to see.
"""

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, getdate

from onedesk.one_project import hours

#: Attendance that puts somebody at work, and what share of a day it is.
WORKED = {"Present": 1.0, "Half Day": 0.5}

#: Where a day starts when the attendance has no check-in time.
DAY_STARTS = time(8, 0)

#: The activity made for days on site when the workspace has none set.
SITE_WORK = "Site Work"


def attended(doc, method=None) -> None:
	"""Attendance on_submit: a day at a project's site, on the project."""
	if doc.status not in WORKED or frappe.db.exists(
		"Timesheet", {"one_attendance": doc.name, "docstatus": 1}
	):
		return
	project = project_at(doc.employee, getdate(doc.attendance_date), doc.name)
	if not project:
		return
	try:
		_write(doc, project)
	except Exception:
		frappe.log_error(
			title=_("A day on site wasn't written for {0}").format(doc.employee_name or doc.employee),
			reference_doctype="Attendance",
			reference_name=doc.name,
		)


def cancelled(doc, method=None) -> None:
	"""Attendance on_cancel: its day on site is cancelled with it."""
	for name in frappe.get_all(
		"Timesheet", filters={"one_attendance": doc.name, "docstatus": 1}, pluck="name"
	):
		sheet = frappe.get_doc("Timesheet", name)
		if any(row.sales_invoice for row in sheet.time_logs):
			continue
		sheet.flags.ignore_permissions = True
		sheet.cancel()


def sites() -> dict[str, str]:
	"""Each site an open project counts time at, and the project."""
	return dict(
		frappe.get_all(
			"Project",
			filters={"status": "Open", "one_time": hours.ATTENDANCE, "one_site": ["is", "set"]},
			fields=["one_site", "name"],
			as_list=True,
		)
	)


def project_at(employee: str, day, attendance: str | None = None) -> str | None:
	"""The project whose site somebody was at that day, or None."""
	at = sites()
	if not at:
		return None
	seen = [
		(one.latitude, one.longitude)
		for one in frappe.get_all(
			"Employee Checkin",
			filters={"employee": employee, "time": ["between", [str(day), f"{day} 23:59:59"]]},
			fields=["latitude", "longitude"],
		)
		if one.latitude or one.longitude
	]
	if seen:
		from onedesk.one_hr import rules

		for site, project in at.items():
			zones = zones_of(site)
			if any(rules.within(lat, lon, zones) for lat, lon in seen):
				return project
		return None
	# No position on any check-in: the site their shift that day names.
	assigned = frappe.get_all(
		"Shift Assignment",
		filters={
			"employee": employee,
			"docstatus": 1,
			"status": "Active",
			"start_date": ["<=", day],
			"shift_location": ["in", list(at)],
		},
		or_filters=[["end_date", ">=", day], ["end_date", "is", "not set"]],
		pluck="shift_location",
	)
	return at.get(assigned[0]) if assigned else None


def zones_of(site: str) -> list[dict]:
	"""The circles that are the site: its own, and any clock place drawn on it
	(one_hr/gates.py reads the same for check-in)."""
	zones = [
		{"latitude": one.latitude, "longitude": one.longitude, "radius": one.checkin_radius}
		for one in frappe.get_all(
			"Shift Location",
			filters={"name": site},
			fields=["latitude", "longitude", "checkin_radius"],
		)
		if one.checkin_radius and (one.latitude or one.longitude)
	]
	zones += frappe.get_all(
		"Clock Place",
		filters={"shift_location": site, "status": ["in", ["Declared", "Confirmed"]]},
		fields=["latitude", "longitude", "radius"],
	)
	return zones


def worked(working_hours: float, status: str, standard: float) -> float:
	"""The hours a day on site counts: what attendance measured, or the
	standard day, half of it for a Half Day. Pure."""
	if flt(working_hours) > 0:
		return round(flt(working_hours), 2)
	return round(flt(standard or 8) * WORKED.get(status, 0), 2)


def activity() -> str:
	"""The activity days on site are logged as: Projects Settings' choice, or
	Site Work, made once."""
	found = frappe.db.get_single_value("Projects Settings", "one_site_activity")
	if found:
		return found
	if not frappe.db.exists("Activity Type", SITE_WORK):
		frappe.get_doc({"doctype": "Activity Type", "activity_type": SITE_WORK}).insert(
			ignore_permissions=True
		)
	frappe.db.set_single_value("Projects Settings", "one_site_activity", SITE_WORK)
	return SITE_WORK


def _write(doc, project: str) -> str | None:
	"""The day as a submitted timesheet on the project."""
	spent = worked(
		doc.working_hours,
		doc.status,
		flt(frappe.db.get_single_value("HR Settings", "standard_working_hours")),
	)
	if spent <= 0:
		return None
	starts = (
		get_datetime(doc.in_time)
		if doc.get("in_time")
		else datetime.combine(getdate(doc.attendance_date), DAY_STARTS)
	)
	sheet = frappe.new_doc("Timesheet")
	sheet.update(
		{
			"employee": doc.employee,
			"company": doc.company,
			"parent_project": project,
			"one_attendance": doc.name,
		}
	)
	sheet.append(
		"time_logs",
		{
			"project": project,
			"activity_type": activity(),
			"from_time": starts,
			"to_time": starts + timedelta(hours=spent),
			"hours": spent,
			"completed": 1,
			"is_billable": 1 if hours.bills_hours(project) else 0,
		},
	)
	sheet.flags.ignore_permissions = True
	sheet.insert()
	sheet.submit()
	return sheet.name
