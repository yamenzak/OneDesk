"""Late arrivals that count as an absent day: HR Settings says how many
(0 is off), and a payslip takes a day off for every so many lates in its
period, after HRMS has counted its payment days."""

import frappe
from frappe.utils import cint, flt

from onedesk.one_hr import policy


def days_off(lates: int, per_absence: int) -> int:
	"""Whole days off for so many lates. Pure."""
	return cint(lates) // cint(per_absence) if cint(per_absence) > 0 else 0


def counted(doc, method=None) -> None:
	"""Salary Slip validate, after the controller has set payment days: take
	off the days the lates come to, and work the pay out again. HRMS counts
	the days afresh on every save, so this never takes them twice."""
	per = cint(policy.get("one_lates_per_absence"))
	doc.one_late_days = 0
	if per <= 0 or not doc.get("employee") or doc.get("salary_slip_based_on_timesheet"):
		return
	lates = frappe.db.count(
		"Attendance",
		{
			"employee": doc.employee,
			"docstatus": 1,
			"late_entry": 1,
			"status": ["in", ("Present", "Work From Home")],
			"attendance_date": ["between", [doc.start_date, doc.end_date]],
		},
	)
	off = min(days_off(lates, per), max(flt(doc.payment_days), 0))
	if not off:
		return
	doc.one_late_days = off
	doc.absent_days = flt(doc.absent_days) + off
	doc.payment_days = flt(doc.payment_days) - off
	doc.calculate_net_pay()
	doc.compute_year_to_date()
	doc.compute_month_to_date()
	doc.compute_component_wise_year_to_date()
