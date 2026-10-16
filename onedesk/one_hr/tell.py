"""What OneHR tells people, through One's hub (docs/NOTIFICATIONS.md, stage 6).

HRMS's approvals, reminders and rescheduled interviews, told here instead of
its own app and mails, and OneHR's own moments besides. More in
one_hr/README.md, Under the hood.
"""

import datetime

import frappe
from frappe import _lt
from frappe.utils import add_days, add_months, cint, cstr, formatdate, getdate, to_timedelta
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
			self.ANSWERED,
			employee,
			record=(self.doctype, self.name),
			status=_lt(status),
			note=note(self),
			**self.said(),
		)


class LeaveApplication(Approvals, HRMSLeaveApplication):
	ASKED, ANSWERED = "Leave Asked", "Leave Answered"

	def said(self) -> dict:
		return {
			"employee": self.employee_name,
			"leave_type": _lt(self.leave_type),
			"days": frappe.utils.flt(self.total_leave_days)
			and f"{frappe.utils.flt(self.total_leave_days):g}",
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
			# Several types joined: said in the asker's language, not the reader's.
			"what": ", ".join(
				frappe._(one)
				for one in dict.fromkeys(row.expense_type for row in self.expenses if row.expense_type)
			)
			or self.get("remark")
			or "",
		}


class ShiftRequest(Approvals, HRMSShiftRequest):
	ASKED, ANSWERED = "Shift Asked", "Shift Answered"

	def said(self) -> dict:
		return {
			"employee": self.employee_name,
			"shift": self.shift_type,
			"from_date": formatdate(self.from_date),
			"until": frappe._("Until {0}").format(formatdate(self.to_date))
			if self.to_date
			else _lt("With no end date"),
		}


def note(doc) -> str:
	"""Whoever answered, and what they wrote, when they wrote anything."""
	said = (doc.get("one_note") or "").strip()
	if not said:
		return ""
	by = frappe.utils.get_fullname(doc.get("one_decided_by") or frappe.session.user)
	return f"{by}: {said}"


# ------------------------------------------------------------------ attendance requests


def attendance_asked(doc, method=None) -> None:
	"""Attendance Request after_insert: HR is told a request waits."""
	employee = frappe.db.get_value("Employee", doc.employee, "user_id")
	notify.notify(
		"Attendance Request Asked",
		[one for one in _hr() if one != employee],
		record=(doc.doctype, doc.name),
		sender=employee or None,
		**_attendance(doc),
		explanation=doc.get("explanation") or "",
	)


def attendance_answered(doc, status: str) -> None:
	"""The employee hears the answer, with the note."""
	employee = frappe.db.get_value("Employee", doc.employee, "user_id")
	if not employee or employee == frappe.session.user:
		return
	notify.notify(
		"Attendance Request Answered",
		employee,
		record=(doc.doctype, doc.name),
		status=_lt(status),
		note=note(doc),
		**_attendance(doc),
	)


def _attendance(doc) -> dict:
	return {
		"employee": doc.employee_name or doc.employee,
		"reason": _lt(doc.get("one_reason") or doc.get("reason") or "Attendance"),
		"from_date": formatdate(doc.from_date),
		"to_date": formatdate(doc.to_date),
	}


def _hr() -> list[str]:
	from onedesk.one.settings import NOT_PEOPLE

	found = frappe.get_all(
		"Has Role",
		filters={"role": ["in", ["HR User", "HR Manager"]], "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	return frappe.get_all(
		"User",
		filters={"name": ["in", [one for one in found if one not in NOT_PEOPLE]], "enabled": 1},
		pluck="name",
	)


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

	def after_insert(self):
		"""Its interviewers are told they are on it, the day it is made."""
		if hasattr(super(), "after_insert"):
			super().after_insert()
		interviewers = [row.interviewer for row in self.interview_details if row.interviewer]
		people = [one for one in interviewers if one != frappe.session.user]
		if not people:
			return
		applicant = frappe.db.get_value("Job Applicant", self.job_applicant, "applicant_name")
		opening = (
			frappe.db.get_value("Job Opening", self.job_opening, "job_title")
			if self.get("job_opening")
			else None
		)
		notify.notify(
			"Interview Scheduled",
			people,
			record=("Interview", self.name),
			applicant=applicant or self.job_applicant,
			when=_when(self),
			opening=opening or self.get("designation") or _lt(self.get("interview_type") or "Interview"),
		)


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
	# HRMS filters the date as though it held the time, so every interview
	# that day matched just after midnight. The date and its start, together.
	for one in frappe.get_all(
		"Interview",
		filters=[
			["scheduled_on", "between", [now.date(), until.date()]],
			["status", "=", "Pending"],
			["reminded", "=", 0],
			["docstatus", "!=", 2],
		],
		fields=["name", "scheduled_on", "from_time"],
	):
		if not now <= _at(one.scheduled_on, one.from_time) <= until:
			continue
		interview = frappe.get_doc("Interview", one.name)
		_tell_interview(interview)
		interview.db_set("reminded", 1)


def _at(day, time) -> datetime.datetime:
	return datetime.datetime.combine(getdate(day), datetime.datetime.min.time()) + to_timedelta(
		time or "0:00"
	)


def feedback_due() -> None:
	"""Each morning: an interview held and under review, to each interviewer
	who has not given feedback. HRMS's `send_daily_feedback_reminder`, told
	in One, for every interview that has ended rather than only those ending
	before the time the job runs."""
	now = datetime.datetime.now()
	for one in frappe.get_all(
		"Interview",
		filters={"status": "Under Review", "docstatus": ["!=", 2], "scheduled_on": ["<=", getdate()]},
		fields=["name", "scheduled_on", "to_time"],
	):
		if _at(one.scheduled_on, one.to_time) > now:
			continue
		interview = frappe.get_doc("Interview", one.name)
		applicant = frappe.db.get_value("Job Applicant", interview.job_applicant, "applicant_name")
		notify.notify(
			"Interview Feedback Due",
			get_recipients(one.name, for_feedback=1),
			record=("Interview", one.name),
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
		# No record: most colleagues may not open somebody else's.
		notify.notify("Birthday", _colleagues(one.company, but=one.user_id), employee=one.employee_name)


def anniversaries() -> None:
	"""Daily: each work anniversary, to everybody else at the company."""
	for one in _today("date_of_joining"):
		notify.notify(
			"Work Anniversary",
			_colleagues(one.company, but=one.user_id),
			employee=one.employee_name,
			joined=formatdate(one.date_of_joining),
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
			link="/desk/onecalendar",
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
		kind=_lt(doc.kind),
	)


def letter_issued(doc) -> None:
	"""A letter issued, to the employee it is about, unless they issued it."""
	user = frappe.db.get_value("Employee", doc.employee, "user_id")
	if not user or user == frappe.session.user:
		return
	notify.notify(
		"Letter Issued",
		user,
		record=(doc.doctype, doc.name),
		kind=_lt(doc.kind),
		by=frappe.utils.get_fullname(frappe.session.user),
	)


def grievance_raised(doc) -> None:
	"""A grievance, to the people trusted with them, whatever OneAI made of it."""
	from onedesk.one_hr import ai_grievance

	users = [one for one in ai_grievance.trusted_users() if one != doc.owner]
	if users:
		notify.notify(
			"Grievance Raised",
			users,
			record=("Employee Grievance", doc.name),
			employee=frappe.db.get_value("Employee", doc.raised_by, "employee_name") or doc.raised_by,
		)


def documents_expiring() -> None:
	"""Each morning: a passport, visa or permit expiring in a month, or a
	week, to the employee and HR."""
	if not frappe.db.get_value("Notification Type", "Document Expiring", "enabled"):
		return
	hr = _hr()
	for days in (30, 7):
		for one in frappe.get_all(
			"Employee Document",
			filters={"parenttype": "Employee", "expires_on": add_days(getdate(), days)},
			fields=["parent", "document_type", "number", "expires_on"],
		):
			employee = frappe.db.get_value(
				"Employee", one.parent, ["employee_name", "user_id", "status"], as_dict=True
			)
			if not employee or employee.status != "Active":
				continue
			notify.notify(
				"Document Expiring",
				[*hr, employee.user_id],
				record=("Employee", one.parent),
				sender="Administrator",
				employee=employee.employee_name,
				document=_lt(one.document_type),
				date=formatdate(one.expires_on),
				number=one.number or "",
			)


def passkey_reset_asked(employee: str, registered: str, asking: str, address: str, why: str) -> None:
	"""An employee who changed phones asks HR for a reset."""
	from markupsafe import Markup, escape

	user = frappe.db.get_value("Employee", employee, "user_id")
	notify.notify(
		"Passkey Reset Asked",
		[one for one in _hr() if one != user],
		record=("Employee", employee),
		sender=user or None,
		employee=frappe.db.get_value("Employee", employee, "employee_name") or employee,
		registered=registered,
		asking=asking,
		address=address or "",
		why=Markup("<br>") + escape(why) if why else "",
	)


def passkey_reset_done(employee: str) -> None:
	"""HR reset the passkey: the employee can register the new phone."""
	user = frappe.db.get_value("Employee", employee, "user_id")
	if user and user != frappe.session.user:
		notify.notify(
			"Passkey Reset Done",
			user,
			link="/desk/settings?section=signin",
			by=frappe.utils.get_fullname(frappe.session.user),
		)


def place_proposed(doc) -> None:
	"""A network or place the clock learned and confirmed, to the HR Managers."""
	managers = frappe.get_all(
		"Has Role",
		filters={"role": "HR Manager", "parenttype": "User"},
		pluck="parent",
		distinct=True,
	)
	place = doc.get(frappe.get_meta(doc.doctype).title_field or "name") or doc.get("label") or doc.name
	notify.notify("Check-in Place Proposed", managers, record=(doc.doctype, doc.name), place=place)


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
	from markupsafe import Markup, escape

	told = Markup("<br>").join(
		Markup("• ") + escape(frappe._(rules.says(signal))) for signal in dict.fromkeys(signals)
	)
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
