"""OneHR's Home (page/onehr): what needs the reader today, and everything in
OneHR with what it is for. The story beside it is story.py.

OneHR's Home is where everybody starts their day, not only HR: so Today is
the reader's own requests still waiting and the leave they have left, then
what waits on them as an approver, then, for HR, the check-ins flagged, the
papers and contracts running out, and today's interviews.
"""

import frappe
from frappe import _lt
from frappe.utils import add_days, flt, getdate, nowdate

from onedesk.one.needs_you import kept

MONTH = 30

HR = ("HR User", "HR Manager")

GROUPS = (
	("people", _lt("Employee")),
	("time", _lt("Time")),
	("leave", _lt("Leave")),
	("pay", _lt("Pay")),
	("benefits", _lt("Tax & Benefits")),
	("expenses", _lt("Expenses")),
	("hiring", _lt("Hiring")),
	("growth", _lt("Growth")),
	("lifecycle", _lt("Joining & Leaving")),
	("reports", _lt("Reports")),
	("setup", _lt("Setup")),
)
REPORT_SECTIONS = (
	("time", _lt("Time")),
	("leave", _lt("Leave")),
	("pay", _lt("Pay")),
	("people", _lt("Employee")),
)
SETUP_SECTIONS = (
	("settings", _lt("Settings")),
	("time", _lt("Time")),
	("leave", _lt("Leave")),
	("pay", _lt("Pay")),
	("lists", _lt("Lists")),
)

EVERYTHING = (
	(
		"people",
		_lt("Employee"),
		"DocType",
		"Employee",
		_lt("Everybody who works here, with their contract, pay and papers."),
	),
	("people", _lt("Org Chart"), "Page", "organizational-chart", _lt("Who reports to whom.")),
	(
		"people",
		_lt("Employee Letter"),
		"DocType",
		"Employee Letter",
		_lt("A salary certificate or an experience letter asked of HR."),
	),
	(
		"people",
		_lt("Employee Grievance"),
		"DocType",
		"Employee Grievance",
		_lt("A complaint raised, looked into and resolved."),
	),
	(
		"time",
		_lt("Attendance"),
		"DocType",
		"Attendance",
		_lt("Who was present, absent or on leave each day."),
	),
	(
		"time",
		_lt("Mark Attendance"),
		"DocType",
		"Employee Attendance Tool",
		_lt("Mark a day for many people at once."),
	),
	("time", _lt("Employee Checkin"), "DocType", "Employee Checkin", _lt("Each clock-in and clock-out.")),
	(
		"time",
		_lt("Clock Attempt"),
		"DocType",
		"Clock Attempt",
		_lt("A clock-in the clock was not sure of, waiting for HR."),
	),
	(
		"time",
		_lt("Attendance Request"),
		"DocType",
		"Attendance Request",
		_lt("A day somebody worked but did not clock, asked for."),
	),
	("time", _lt("Shift Request"), "DocType", "Shift Request", _lt("A shift somebody asked to work.")),
	(
		"time",
		_lt("Shift Assignment Tool"),
		"DocType",
		"Shift Assignment Tool",
		_lt("Put many people on a shift at once."),
	),
	(
		"time",
		_lt("Overtime Slip"),
		"DocType",
		"Overtime Slip",
		_lt("The overtime a month's attendance adds to pay."),
	),
	("time", _lt("Timesheet"), "DocType", "Timesheet", _lt("Hours worked, on what.")),
	(
		"leave",
		_lt("Leave Application"),
		"DocType",
		"Leave Application",
		_lt("Leave asked for, and its answer."),
	),
	(
		"leave",
		_lt("Leave Allocation"),
		"DocType",
		"Leave Allocation",
		_lt("The days of each kind of leave somebody is given."),
	),
	("leave", _lt("Leave Encashment"), "DocType", "Leave Encashment", _lt("Untaken days paid out.")),
	(
		"leave",
		_lt("Leave Policy Assignment"),
		"DocType",
		"Leave Policy Assignment",
		_lt("Which leave policy somebody is on."),
	),
	(
		"leave",
		_lt("Leave Control Panel"),
		"DocType",
		"Leave Control Panel",
		_lt("Allocate leave to many people at once."),
	),
	("pay", _lt("Salary Slip"), "DocType", "Salary Slip", _lt("A month's pay, earning by earning.")),
	("pay", _lt("Payroll Entry"), "DocType", "Payroll Entry", _lt("A month's payroll run, and its slips.")),
	(
		"pay",
		_lt("Salary Structure Assignment"),
		"DocType",
		"Salary Structure Assignment",
		_lt("What somebody is paid, and from when."),
	),
	(
		"pay",
		_lt("Additional Salary"),
		"DocType",
		"Additional Salary",
		_lt("A one-off earning or deduction in a month's pay."),
	),
	(
		"pay",
		_lt("Employee Incentive"),
		"DocType",
		"Employee Incentive",
		_lt("An incentive paid with the next payroll."),
	),
	(
		"pay",
		_lt("Retention Bonus"),
		"DocType",
		"Retention Bonus",
		_lt("A bonus paid for staying until a date."),
	),
	("pay", _lt("Arrear"), "DocType", "Arrear", _lt("Back pay for a raise dated in the past.")),
	(
		"pay",
		_lt("Salary Withholding"),
		"DocType",
		"Salary Withholding",
		_lt("Pay held back for some cycles, and why."),
	),
	(
		"benefits",
		_lt("Employee Benefit Application"),
		"DocType",
		"Employee Benefit Application",
		_lt("The flexible benefits somebody chose."),
	),
	(
		"benefits",
		_lt("Employee Benefit Claim"),
		"DocType",
		"Employee Benefit Claim",
		_lt("A benefit claimed against its receipts."),
	),
	(
		"benefits",
		_lt("Employee Tax Exemption Declaration"),
		"DocType",
		"Employee Tax Exemption Declaration",
		_lt("What somebody declares to pay less tax."),
	),
	(
		"expenses",
		_lt("Expense Claim"),
		"DocType",
		"Expense Claim",
		_lt("Money somebody spent for work, paid back."),
	),
	(
		"expenses",
		_lt("Employee Advance"),
		"DocType",
		"Employee Advance",
		_lt("Money given before it is spent."),
	),
	(
		"expenses",
		_lt("Travel Request"),
		"DocType",
		"Travel Request",
		_lt("A trip asked for, with what it will cost."),
	),
	(
		"expenses",
		_lt("Vehicle Log"),
		"DocType",
		"Vehicle Log",
		_lt("A company vehicle's fuel and servicing."),
	),
	(
		"hiring",
		_lt("Job Opening"),
		"DocType",
		"Job Opening",
		_lt("A role being hired for, and its applicants."),
	),
	("hiring", _lt("Job Applicant"), "DocType", "Job Applicant", _lt("Somebody who applied.")),
	(
		"hiring",
		_lt("Interview"),
		"DocType",
		"Interview",
		_lt("An interview, its interviewers and their feedback."),
	),
	("hiring", _lt("Job Offer"), "DocType", "Job Offer", _lt("An offer made, and its answer.")),
	(
		"hiring",
		_lt("Appointment Letter"),
		"DocType",
		"Appointment Letter",
		_lt("The letter a new joiner signs."),
	),
	(
		"hiring",
		_lt("Job Requisition"),
		"DocType",
		"Job Requisition",
		_lt("A role somebody asked to hire for."),
	),
	(
		"hiring",
		_lt("Staffing Plan"),
		"DocType",
		"Staffing Plan",
		_lt("How many people each role needs this year."),
	),
	(
		"hiring",
		_lt("Employee Referral"),
		"DocType",
		"Employee Referral",
		_lt("Somebody an employee put forward."),
	),
	("growth", _lt("Goal"), "DocType", "Goal", _lt("What somebody means to achieve this cycle.")),
	(
		"growth",
		_lt("Appraisal Cycle"),
		"DocType",
		"Appraisal Cycle",
		_lt("A round of appraisals, and who is in it."),
	),
	(
		"growth",
		_lt("Appraisal"),
		"DocType",
		"Appraisal",
		_lt("How somebody did, scored on goals and feedback."),
	),
	(
		"growth",
		_lt("Employee Performance Feedback"),
		"DocType",
		"Employee Performance Feedback",
		_lt("Feedback given on somebody's work."),
	),
	(
		"growth",
		_lt("Employee Promotion"),
		"DocType",
		"Employee Promotion",
		_lt("A new role or grade, and what it pays."),
	),
	(
		"growth",
		_lt("Employee Transfer"),
		"DocType",
		"Employee Transfer",
		_lt("A move to another department or branch."),
	),
	(
		"growth",
		_lt("Training Event"),
		"DocType",
		"Training Event",
		_lt("A course given, who came and how they did."),
	),
	(
		"lifecycle",
		_lt("Employee Onboarding"),
		"DocType",
		"Employee Onboarding",
		_lt("What a new joiner is taken through."),
	),
	(
		"lifecycle",
		_lt("Employee Separation"),
		"DocType",
		"Employee Separation",
		_lt("What is done when somebody leaves."),
	),
	(
		"lifecycle",
		_lt("Exit Interview"),
		"DocType",
		"Exit Interview",
		_lt("Why somebody is leaving, asked before they go."),
	),
	("lifecycle", _lt("Gratuity"), "DocType", "Gratuity", _lt("A leaver's end of service benefit.")),
	(
		"lifecycle",
		_lt("Full and Final Statement"),
		"DocType",
		"Full and Final Statement",
		_lt("What a leaver and the company still owe each other."),
	),
	(
		"reports",
		_lt("Monthly Attendance"),
		"Report",
		"Monthly Attendance",
		_lt("Each person's month, day by day."),
		"time",
	),
	(
		"reports",
		_lt("Attendance by Shift"),
		"Report",
		"Attendance by Shift",
		_lt("Who came on each shift, late or early."),
		"time",
	),
	(
		"reports",
		_lt("Hours Utilization"),
		"Report",
		"Hours Utilization",
		_lt("How much of each person's time was billed."),
		"time",
	),
	(
		"reports",
		_lt("Leave Balance"),
		"Report",
		"Employee Leave Balance",
		_lt("The leave each person has left, kind by kind."),
		"leave",
	),
	(
		"reports",
		_lt("Leave Balance Summary"),
		"Report",
		"Employee Leave Balance Summary",
		_lt("Leave given, taken and left, for everybody."),
		"leave",
	),
	(
		"reports",
		_lt("Leave Ledger"),
		"Report",
		"Leave Ledger",
		_lt("Every day of leave given, taken, encashed or lapsed."),
		"leave",
	),
	(
		"reports",
		_lt("Working on a Holiday"),
		"Report",
		"Employees working on a holiday",
		_lt("Who worked a holiday, and may take a day back."),
		"leave",
	),
	(
		"reports",
		_lt("Salary Register"),
		"Report",
		"Salary Register",
		_lt("A payroll run's slips, earning by earning."),
		"pay",
	),
	(
		"reports",
		_lt("CTC Break-up"),
		"Report",
		"Employee CTC Break-up",
		_lt("What each person costs, part by part."),
		"pay",
	),
	(
		"reports",
		_lt("Unpaid Expense Claim"),
		"Report",
		"Unpaid Expense Claim",
		_lt("Claims approved and not yet paid back."),
		"pay",
	),
	(
		"reports",
		_lt("Vehicle Expenses"),
		"Report",
		"Vehicle Expenses",
		_lt("What each vehicle cost to run."),
		"pay",
	),
	(
		"reports",
		_lt("Employee Analytics"),
		"Report",
		"Employee Analytics",
		_lt("Headcount by department, branch or grade."),
		"people",
	),
	(
		"reports",
		_lt("Employee Information"),
		"Report",
		"Employee Information",
		_lt("Everybody's details in one table."),
		"people",
	),
	(
		"reports",
		_lt("Employee Birthday"),
		"Report",
		"Employee Birthday",
		_lt("Whose birthday is this month."),
		"people",
	),
	("reports", _lt("Employee Exits"), "Report", "Employee Exits", _lt("Who left, when and why."), "people"),
	(
		"reports",
		_lt("Appraisal Overview"),
		"Report",
		"Appraisal Overview",
		_lt("Each appraisal's scores, cycle by cycle."),
		"people",
	),
	(
		"setup",
		_lt("HR Settings"),
		"DocType",
		"HR Settings",
		_lt("How leave, attendance, hiring and reminders work."),
		"settings",
	),
	(
		"setup",
		_lt("Payroll Settings"),
		"DocType",
		"Payroll Settings",
		_lt("How pay is worked out and slips are sent."),
		"settings",
	),
	(
		"setup",
		_lt("Shift Type"),
		"DocType",
		"Shift Type",
		_lt("The hours a shift runs, and how attendance is marked from it."),
		"time",
	),
	("setup", _lt("Holiday List"), "DocType", "Holiday List", _lt("The days off a year has."), "time"),
	("setup", _lt("Overtime Type"), "DocType", "Overtime Type", _lt("How overtime is paid."), "time"),
	("setup", _lt("Leave Type"), "DocType", "Leave Type", _lt("Each kind of leave, and its rules."), "leave"),
	(
		"setup",
		_lt("Leave Policy"),
		"DocType",
		"Leave Policy",
		_lt("How many days of each kind a year gives."),
		"leave",
	),
	(
		"setup",
		_lt("Leave Block List"),
		"DocType",
		"Leave Block List",
		_lt("Days leave may not be taken."),
		"leave",
	),
	(
		"setup",
		_lt("Salary Component"),
		"DocType",
		"Salary Component",
		_lt("Each earning and deduction a slip can carry."),
		"pay",
	),
	(
		"setup",
		_lt("Salary Structure"),
		"DocType",
		"Salary Structure",
		_lt("How a salary is made up of its components."),
		"pay",
	),
	(
		"setup",
		_lt("Gratuity Rule"),
		"DocType",
		"Gratuity Rule",
		_lt("How an end of service benefit is worked out."),
		"pay",
	),
	(
		"setup",
		_lt("Expense Claim Type"),
		"DocType",
		"Expense Claim Type",
		_lt("The kinds of expense somebody may claim."),
		"pay",
	),
	("setup", _lt("Department"), "List", "Department", _lt("The company's departments."), "lists"),
	("setup", _lt("Designation"), "List", "Designation", _lt("The roles people hold."), "lists"),
	("setup", _lt("Branch"), "List", "Branch", _lt("Where people work."), "lists"),
	(
		"setup",
		_lt("Employee Grade"),
		"DocType",
		"Employee Grade",
		_lt("Pay grades, with their usual pay."),
		"lists",
	),
	(
		"setup",
		_lt("Interview Type"),
		"DocType",
		"Interview Type",
		_lt("Each kind of interview, its skills and interviewers."),
		"lists",
	),
	(
		"setup",
		_lt("Appraisal Template"),
		"DocType",
		"Appraisal Template",
		_lt("What an appraisal scores somebody on."),
		"lists",
	),
)


@frappe.whitelist()
def read() -> dict:
	"""What needs the reader, and the directory, as the reader may see them."""
	return {
		"needs": needs_you(),
		"hr": is_hr(),
		"groups": [{"key": key, "label": str(label)} for key, label in GROUPS],
		"sections": {
			"reports": [{"key": key, "label": str(label)} for key, label in REPORT_SECTIONS],
			"setup": [{"key": key, "label": str(label)} for key, label in SETUP_SECTIONS],
		},
		"everything": directory(),
	}


def is_hr() -> bool:
	return bool(set(HR) & set(frappe.get_roles()))


def company() -> str | None:
	return frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("company")


def me() -> str | None:
	"""The reader's employee record, in the default company."""
	return frappe.db.get_value(
		"Employee", {"user_id": frappe.session.user, "status": "Active", "company": company()}
	)


def needs_you() -> dict:
	"""The reader's own requests waiting and leave left; what waits on them
	as an approver; and, for HR, the flags, the papers and contracts running
	out and today's interviews."""
	hr = is_hr()
	return {
		"mine": kept(_mine()),
		"leave": _leave_left(),
		"approve": kept(_to_approve(hr)),
		"flagged": kept(_flagged() if hr else []),
		"expiring": kept(_expiring() if hr else []),
		"ending": kept(_ending() if hr else []),
		"interviews": kept(_interviews()),
	}


REQUESTS = (
	("Leave Application", "status", ("Open",), "leave_approver", "leave_type"),
	("Expense Claim", "approval_status", ("Draft",), "expense_approver", "total_claimed_amount"),
	("Shift Request", "status", ("Draft",), "approver", "shift_type"),
	("Attendance Request", "docstatus", (0,), None, "one_reason"),
)


def _about(doctype: str, one) -> str:
	if doctype == "Expense Claim":
		return frappe.utils.fmt_money(one.total_claimed_amount, currency=one.get("currency"))
	if doctype == "Attendance Request":
		return str(_lt(one.get("one_reason") or "Attendance"))
	return str(_lt(one.get(REQUESTS[[r[0] for r in REQUESTS].index(doctype)][4]) or ""))


def _requests(doctype, field, waiting, about, filters) -> list[dict]:
	if not frappe.has_permission(doctype, "read"):
		return []
	fields = ["name", "employee", "employee_name", "creation", about]
	if doctype == "Expense Claim":
		fields.append("currency")
	if doctype in ("Leave Application", "Attendance Request", "Shift Request"):
		fields += ["from_date", "to_date"]
	rows = frappe.get_list(
		doctype,
		filters=[[field, "in", list(waiting)], ["docstatus", "<", 2], *filters],
		fields=fields,
		order_by="creation asc",
		limit_page_length=0,
	)
	return [
		{
			"doctype": doctype,
			"name": one.name,
			"employee": one.employee,
			"who": one.employee_name,
			"about": _about(doctype, one),
			"from": str(one.from_date) if one.get("from_date") else None,
			"to": str(one.to_date) if one.get("to_date") else None,
			"since": str(one.creation),
		}
		for one in rows
	]


def _mine() -> list[dict]:
	"""The reader's own requests still waiting for an answer."""
	employee = me()
	if not employee:
		return []
	out = []
	for doctype, field, waiting, _approver, about in REQUESTS:
		out += _requests(doctype, field, waiting, about, [["employee", "=", employee]])
	return out


def _to_approve(hr: bool) -> list[dict]:
	"""Requests waiting on the reader: theirs to approve, or, for HR, those
	with no approver named, which HR answers (one_hr/tell.py). Never their
	own."""
	out = []
	for doctype, field, waiting, approver, about in REQUESTS:
		if approver:
			out += _requests(doctype, field, waiting, about, [[approver, "=", frappe.session.user]])
			if hr:
				out += _requests(doctype, field, waiting, about, [[approver, "is", "not set"]])
		elif hr:
			out += _requests(doctype, field, waiting, about, [])
	employee = me()
	return [one for one in out if one["employee"] != employee]


def _leave_left() -> list[dict]:
	"""The leave the reader has left this year, kind by kind."""
	from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on

	employee = me()
	if not employee:
		return []
	day = getdate(nowdate())
	out = []
	for one in frappe.get_all(
		"Leave Allocation",
		filters={
			"employee": employee,
			"company": company(),
			"docstatus": 1,
			"from_date": ["<=", day],
			"to_date": [">=", day],
		},
		fields=["leave_type", "total_leaves_allocated", "to_date"],
	):
		out.append(
			{
				"leave_type": one.leave_type,
				"label": str(_lt(one.leave_type)),
				"left": flt(get_leave_balance_on(employee, one.leave_type, day, one.to_date)),
				"given": flt(one.total_leaves_allocated),
			}
		)
	return out


def _flagged() -> list[dict]:
	"""Check-ins the clock flagged and nobody has settled."""
	if not frappe.has_permission("Clock Attempt", "read"):
		return []
	from onedesk.one_hr.heads import attempt_seen

	return [
		{
			"doctype": "Clock Attempt",
			"name": one.name,
			"who": one.employee_name,
			"about": attempt_seen(frappe.get_doc("Clock Attempt", one.name)),
			"since": str(one.creation),
		}
		for one in frappe.get_list(
			"Clock Attempt",
			filters={"outcome": "Flagged", "verdict": ["is", "not set"]},
			fields=["name", "employee_name", "creation"],
			order_by="creation desc",
			limit_page_length=0,
		)
	]


def _expiring() -> list[dict]:
	"""A passport, visa or permit expiring within a month, the soonest first."""
	if not frappe.has_permission("Employee", "read"):
		return []
	day = getdate(nowdate())
	rows = frappe.get_all(
		"Employee Document",
		filters={"parenttype": "Employee", "expires_on": ["between", [day, add_days(day, MONTH)]]},
		fields=["parent", "document_type", "expires_on"],
		order_by="expires_on asc",
	)
	people = dict(
		frappe.get_list(
			"Employee",
			filters={
				"name": ["in", [one.parent for one in rows] or [""]],
				"status": "Active",
				"company": company(),
			},
			fields=["name", "employee_name"],
			as_list=True,
		)
	)
	return [
		{
			"doctype": "Employee",
			"name": one.parent,
			"who": people[one.parent],
			"about": str(_lt(one.document_type)),
			"on": str(one.expires_on),
			"days": (getdate(one.expires_on) - day).days,
		}
		for one in rows
		if one.parent in people
	]


def _ending() -> list[dict]:
	"""A contract or a probation ending within a month, the soonest first."""
	if not frappe.has_permission("Employee", "read"):
		return []
	day = getdate(nowdate())
	out = []
	for field, said in (
		("contract_end_date", _lt("Contract Ending")),
		("scheduled_confirmation_date", _lt("Probation Ending")),
	):
		for one in frappe.get_list(
			"Employee",
			filters={
				"status": "Active",
				"company": company(),
				field: ["between", [day, add_days(day, MONTH)]],
			},
			fields=["name", "employee_name", field],
		):
			out.append(
				{
					"doctype": "Employee",
					"name": one.name,
					"who": one.employee_name,
					"about": str(said),
					"on": str(one[field]),
					"days": (getdate(one[field]) - day).days,
				}
			)
	return sorted(out, key=lambda one: one["days"])


def _interviews() -> list[dict]:
	"""Interviews today the reader sits on, or, for HR, every one today."""
	if not frappe.has_permission("Interview", "read"):
		return []
	day = getdate(nowdate())
	filters = {"scheduled_on": day, "docstatus": ["<", 2]}
	names = None
	if not is_hr():
		names = frappe.get_all(
			"Interview Detail",
			filters={"interviewer": frappe.session.user, "parenttype": "Interview"},
			pluck="parent",
		)
		if not names:
			return []
		filters["name"] = ["in", names]
	return [
		{
			"doctype": "Interview",
			"name": one.name,
			"who": frappe.db.get_value("Job Applicant", one.job_applicant, "applicant_name")
			or one.job_applicant,
			"about": str(_lt(one.interview_type or "Interview")),
			"at": str(one.from_time)[:5],
		}
		for one in frappe.get_list(
			"Interview",
			filters=filters,
			fields=["name", "job_applicant", "interview_type", "from_time"],
			order_by="from_time asc",
		)
	]


def _may(kind: str, target: str) -> bool:
	"""Only what the reader can open: a report one/declutter.py turned off, or
	one over records they may not read, is not offered."""
	if kind in ("DocType", "List"):
		return bool(frappe.has_permission(target, "read"))
	if not frappe.db.exists(kind, target):
		return False
	if kind == "Report":
		from frappe.desk.desk_views import DeskViews

		doc = frappe.get_cached_doc(kind, target)
		return (
			target in DeskViews.get_allowed_report_names(cache=True)
			and not doc.disabled
			and (not doc.ref_doctype or bool(frappe.has_permission(doc.ref_doctype, "report")))
		)
	return bool(frappe.get_cached_doc(kind, target).is_permitted())


def directory() -> list[dict]:
	"""Everything in OneHR the reader may open, with what it is for, less a
	country's own where no company is in it (one/countries.py), as the rail."""
	from onedesk.one import countries

	here = countries.ours()
	return [
		{
			"group": group,
			"label": str(label),
			"kind": kind,
			"target": target,
			"filters": None,
			"about": str(about),
			"topic": topic[0] if topic else None,
		}
		for group, label, kind, target, about, *topic in EVERYTHING
		if countries.shown(target, here) and _may(kind, target)
	]
