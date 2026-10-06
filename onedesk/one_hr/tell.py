"""What OneHR tells people, through One's hub (docs/NOTIFICATIONS.md, stage 6).

HRMS's approvals, reminders and rescheduled interviews, told here instead of
its own app and mails, and OneHR's own moments besides. More in
one_hr/README.md, Under the hood.
"""

import datetime

import frappe
from frappe import _lt
from frappe.utils import add_days, add_months, cint, cstr, formatdate, getdate, nowtime
from hrms.hr.doctype.expense_claim.expense_claim import ExpenseClaim as HRMSExpenseClaim
from hrms.hr.doctype.interview.interview import Interview as HRMSInterview
from hrms.hr.doctype.interview.interview import get_recipients
from hrms.hr.doctype.leave_application.leave_application import LeaveApplication as HRMSLeaveApplication
from hrms.hr.doctype.shift_request.shift_request import ShiftRequest as HRMSShiftRequest

from onedesk.one import notify

# ------------------------------------------------------------------ approvals


class Approvals:
	"""HRMS's two approval moments, told through the hub. `ASKED` and
	`ANSWERED` name the types; `said` fills their slots."""

	ASKED = ""
	ANSWERED = ""

	def notify_approver(self):
		approver, employee = self._get_doc_approver(), self._get_employee_user()
		if not approver or approver == employee:
			return
		notify.notify(
			self.ASKED, approver, record=(self.doctype, self.name), sender=employee or None, **self.said()
		)

	def notify_approval_status(self):
		field = self._get_doc_status_field()
		status = self.get(field)
		if self.has_value_changed(field) and status in ("Approved", "Rejected"):
			self.answered(status)

	def answered(self, status: str) -> None:
		employee = self._get_employee_user()
		if not employee or employee == frappe.session.user:
			return
		notify.notify(
			self.ANSWERED, employee, record=(self.doctype, self.name), status=_lt(status), **self.said()
		)


class LeaveApplication(Approvals, HRMSLeaveApplication):
	ASKED, ANSWERED = "Leave Asked", "Leave Answered"

	def said(self) -> dict:
		return {
			"employee": self.employee_name,
			"leave_type": _lt(self.leave_type),
			"days": self.total_leave_days,
			"from_date": formatdate(self.from_date),
			"to_date": formatdate(self.to_date),
		}

	def notify_leave_approver(self):
		"""HRMS's mail to the approver. `notify_approver` tells them."""

	def notify_employee(self):
		"""HRMS's mail to the employee. `notify_approval_status` tells them."""

	def on_cancel(self):
		super().on_cancel()
		self.answered("Cancelled")


class ExpenseClaim(Approvals, HRMSExpenseClaim):
	ASKED, ANSWERED = "Expense Claim Asked", "Expense Claim Answered"

	def said(self) -> dict:
		return {
			"employee": self.employee_name,
			"amount": frappe.utils.fmt_money(self.total_claimed_amount, currency=self.currency),
		}


class ShiftRequest(Approvals, HRMSShiftRequest):
	ASKED, ANSWERED = "Shift Asked", "Shift Answered"

	def said(self) -> dict:
		return {
			"employee": self.employee_name,
			"shift": self.shift_type,
			"from_date": formatdate(self.from_date),
			"to_date": formatdate(self.to_date or self.from_date),
		}


# ------------------------------------------------------------------ interviews


class Interview(HRMSInterview):
	@frappe.whitelist(methods=["POST"])
	def reschedule_interview(
		self, scheduled_on: datetime.date, from_time: datetime.time, to_time: datetime.time
	) -> None:
		"""HRMS's, with the telling moved onto two types. Derived from
		hrms/hr/doctype/interview/interview.py (GPL-3.0, Frappe Technologies)."""
		if (
			getdate(scheduled_on) == getdate(self.scheduled_on)
			and cstr(from_time) == cstr(self.from_time)
			and cstr(to_time) == cstr(self.to_time)
		):
			frappe.msgprint(
				frappe._("No changes found in timings."),
				indicator="orange",
				title=frappe._("Interview Not Rescheduled"),
			)
			return
		was = _when(self)
		self.db_set({"scheduled_on": scheduled_on, "from_time": from_time, "to_time": to_time})
		self.notify_update()
		_tell_interview(self, moved=True, was=was)


def _when(interview) -> str:
	return (
		f"{formatdate(interview.scheduled_on)} {cstr(interview.from_time)[:5]}–{cstr(interview.to_time)[:5]}"
	)


def _tell_interview(interview, moved: bool = False, **context) -> None:
	"""Its interviewers told in One; the applicant mailed, in the type of the
	same name "to the Applicant"."""
	applicant, email = frappe.db.get_value(
		"Job Applicant", interview.job_applicant, ["applicant_name", "email_id"]
	) or (interview.job_applicant, None)
	values = {"applicant": applicant, "when": _when(interview), **context}
	interviewers = [row.interviewer for row in interview.interview_details if row.interviewer]
	notify.notify(
		"Interview Moved" if moved else "Interview Soon",
		interviewers,
		record=("Interview", interview.name),
		**values,
	)
	if email:
		notify.mail(
			"Interview Moved, to the Applicant" if moved else "Interview Soon, to the Applicant",
			email,
			sender=frappe.db.get_single_value("HR Settings", "hiring_sender_email") or None,
			reference_doctype="Interview",
			reference_name=interview.name,
			**values,
		)


def interviews_soon() -> None:
	"""Every few minutes: an interview starting within HR Settings' Remind
	Before, once. HRMS's `send_interview_reminder`, told in One."""
	if not frappe.db.get_value("Notification Type", "Interview Soon", "enabled"):
		return
	before = cstr(frappe.db.get_single_value("HR Settings", "remind_before")) or "01:00:00"
	before = datetime.datetime.strptime(before, "%H:%M:%S")
	now = datetime.datetime.now()
	until = now + datetime.timedelta(hours=before.hour, minutes=before.minute, seconds=before.second)
	for name in frappe.get_all(
		"Interview",
		filters=[
			["scheduled_on", "between", [now, until]],
			["status", "=", "Pending"],
			["reminded", "=", 0],
			["docstatus", "!=", 2],
		],
		pluck="name",
	):
		interview = frappe.get_doc("Interview", name)
		_tell_interview(interview)
		interview.db_set("reminded", 1)


def feedback_due() -> None:
	"""Daily: an interview held and under review, to each interviewer who has
	not given feedback. HRMS's `send_daily_feedback_reminder`, told in One."""
	for name in frappe.get_all(
		"Interview",
		filters={
			"status": "Under Review",
			"docstatus": ["!=", 2],
			"scheduled_on": ["<=", getdate()],
			"to_time": ["<=", nowtime()],
		},
		pluck="name",
	):
		interview = frappe.get_doc("Interview", name)
		applicant = frappe.db.get_value("Job Applicant", interview.job_applicant, "applicant_name")
		notify.notify(
			"Interview Feedback Due",
			get_recipients(name, for_feedback=1),
			record=("Interview", name),
			applicant=applicant or interview.job_applicant,
			when=_when(interview),
		)


# ------------------------------------------------------------------ reminders


def _colleagues(company: str, but: str | None = None) -> list[str]:
	"""The users of a company's active employees, but one."""
	return [
		user
		for user in frappe.get_all(
			"Employee",
			filters={"status": "Active", "company": company, "user_id": ["is", "set"]},
			pluck="user_id",
		)
		if user != but
	]


def _today(field: str) -> list[dict]:
	"""Active employees whose `field` falls on today's day and month, in an
	earlier year."""
	today = getdate()
	return [
		one
		for one in frappe.get_all(
			"Employee",
			filters={"status": "Active", field: ["is", "set"]},
			fields=["name", "employee_name", "company", "user_id", field],
		)
		if (one[field].month, one[field].day) == (today.month, today.day) and one[field].year < today.year
	]


def birthdays() -> None:
	"""Daily: each birthday, to everybody else at the company."""
	for one in _today("date_of_birth"):
		notify.notify(
			"Birthday",
			_colleagues(one.company, but=one.user_id),
			record=("Employee", one.name),
			employee=one.employee_name,
		)


def anniversaries() -> None:
	"""Daily: each work anniversary, to everybody else at the company."""
	for one in _today("date_of_joining"):
		notify.notify(
			"Work Anniversary",
			_colleagues(one.company, but=one.user_id),
			record=("Employee", one.name),
			employee=one.employee_name,
			joined=formatdate(one.date_of_joining),
			years=getdate().year - one.date_of_joining.year,
		)


def holidays_weekly() -> None:
	_holidays("Weekly")


def holidays_monthly() -> None:
	_holidays("Monthly")


def _holidays(frequency: str) -> None:
	"""Each employee's holidays in the coming week or month, as often as HR
	Settings says."""
	from hrms.hr.utils import get_holidays_for_employee

	if (frappe.db.get_single_value("HR Settings", "frequency") or "Weekly") != frequency:
		return
	start = getdate()
	end = add_days(start, 7) if frequency == "Weekly" else add_months(start, 1)
	for one in frappe.get_all(
		"Employee", filters={"status": "Active", "user_id": ["is", "set"]}, fields=["name", "user_id"]
	):
		days = get_holidays_for_employee(one.name, start, end, only_non_weekly=True, raise_exception=False)
		if not days:
			continue
		notify.notify(
			"Holidays Coming Up",
			one.user_id,
			holidays="; ".join(
				f"{formatdate(day.holiday_date)}: {frappe.utils.strip_html(cstr(day.description))}"
				for day in days
			),
			count=cint(len(days)),
		)


# ------------------------------------------------------------------ OneHR's own


def grievance_flagged(doc, sensitive: bool) -> None:
	"""A grievance OneAI read as sensitive or urgent, to the HR Managers."""
	from onedesk.one_hr import ai_grievance, hiring

	users = ai_grievance.trusted_users()
	if not users:
		return
	notify.notify(
		"Sensitive Grievance" if sensitive else "Urgent Grievance",
		users,
		record=("Employee Grievance", doc.name),
		sender=hiring.AUTHOR,
	)


def day_closed(employee: str, checkin: str) -> None:
	"""A day nobody clocked out of, closed at the shift's end, to the employee."""
	user = frappe.db.get_value("Employee", employee, "user_id")
	if not user:
		return
	notify.notify("Check-in Closed for You", user, record=("Employee Checkin", checkin))


def letter_requested(doc) -> None:
	"""An employee asked for a letter, to the HR Managers."""
	managers = frappe.get_all(
		"Has Role",
		filters={
			"role": "HR Manager",
			"parenttype": "User",
			"parent": ["not in", ["Administrator", "Guest"]],
		},
		pluck="parent",
	)
	enabled = frappe.get_all("User", filters={"name": ["in", managers], "enabled": 1}, pluck="name")
	if not enabled:
		return
	notify.notify(
		"Letter Requested",
		enabled,
		record=(doc.doctype, doc.name),
		employee=doc.employee_name,
		kind=frappe._(doc.kind).lower(),
	)


def place_proposed(doc) -> None:
	"""A network or place the clock learned and confirmed, to the HR Managers."""
	managers = frappe.get_all(
		"Has Role",
		filters={"role": "HR Manager", "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	notify.notify("Check-in Place Proposed", managers, record=(doc.doctype, doc.name))


def could_not_mark_left(employee: str, why: str) -> None:
	"""Somebody past their last day who could not be set to Left, to HR."""
	name = frappe.db.get_value("Employee", employee, "employee_name") or employee
	hr = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["HR User", "HR Manager"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	notify.notify(
		"Could Not Mark Left",
		hr,
		record=("Employee", employee),
		employee=name,
		why=frappe.utils.strip_html(why),
	)


def check_in_flagged(attempt: str, employee: str, signals: list[str]) -> None:
	"""A check-in flagged for review, to everybody who can settle it."""
	from onedesk.one_hr import review, rules

	name = frappe.db.get_value("Employee", employee, "employee_name") or employee
	told = "\n".join(f"• {frappe._(rules.says(signal))}" for signal in dict.fromkeys(signals))
	reviewers = frappe.get_all(
		"Has Role",
		filters={"role": ["in", list(review.REVIEWERS)], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	notify.notify(
		"Check-in Flagged", reviewers, record=("Clock Attempt", attempt), employee=name, reasons=told
	)


def shift_not_reading(shift: str) -> None:
	"""A shift whose check-ins never become attendance, to the HR Managers."""
	people = frappe.get_all(
		"Has Role",
		filters={"role": "HR Manager", "parenttype": "User"},
		pluck="parent",
		ignore_permissions=True,
	)
	notify.notify("Shift Not Reading Check-ins", people, record=("Shift Type", shift), shift=shift)
