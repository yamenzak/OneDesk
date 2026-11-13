"""OneHR's Home, told as a story (page/onehr, frontend/src/hr): the headline
figures with their months, then the people, their time and their pay, and
hiring. For HR only: everybody else's Home is their own day (home.py), since
how many people the company has and what they cost are not theirs to read.
In the company's currency, as the reader may see each part.
"""

from collections import Counter, defaultdict
from datetime import date

import frappe
from frappe.utils import add_days, add_months, flt, get_first_day, get_last_day, getdate, today

from onedesk.one.company import company_currency, reader_company
from onedesk.one.rights import can
from onedesk.one.story import month_of, story_months
from onedesk.one_book import closing
from onedesk.one_hr.home import is_hr

MONTHS = 12

DAYS = 30

FEW = 8

FUNNEL = ("Job Applicant", "Interview", "Job Offer", "Accepted", "Joined")


@frappe.whitelist()
@frappe.read_only()
def read() -> dict | None:
	"""Everything Home's story draws, each part None when the reader may not
	see it; None for anybody but HR."""
	if not is_hr():
		return None
	company = reader_company()
	months = story_months()
	people = _people(company) if can("Employee") else []
	return {
		"currency": company_currency(company),
		"months": [one.isoformat() for one in months],
		"cards": _cards(company, months, people),
		"people": {"departments": _departments(people), "moves": _moves(months, people)} if people else None,
		"time": {"attendance": _attendance(company), "leave": _leave(company)}
		if can("Attendance")
		else None,
		"pay": {"payroll": _payroll(company, months), "expenses": _expenses(company)}
		if can("Salary Slip")
		else None,
		"hiring": {"funnel": _funnel(company)} if can("Job Applicant") else None,
	}


def _people(company) -> list:
	return frappe.get_list(
		"Employee",
		filters={"company": company},
		fields=["name", "department", "date_of_joining", "relieving_date", "status"],
		limit_page_length=0,
	)


def _here(people, day) -> int:
	"""How many worked here on a day: joined by then and not yet gone."""
	day = getdate(day)
	return sum(
		1
		for one in people
		if one.date_of_joining
		and getdate(one.date_of_joining) <= day
		and (not one.relieving_date or getdate(one.relieving_date) >= day)
	)


def _cards(company, months, people) -> dict:
	day = getdate(today())
	out = {}
	if people:
		out["headcount"] = {
			"value": _here(people, day),
			"series": [_here(people, min(get_last_day(one), day)) for one in months],
		}
		joined = Counter(month_of(one.date_of_joining) for one in people if one.date_of_joining)
		out["joined"] = {
			"value": joined.get(months[-1].isoformat(), 0),
			"series": [joined.get(one.isoformat(), 0) for one in months],
		}
	if can("Attendance"):
		marked = Counter(
			frappe.get_list(
				"Attendance",
				filters={"company": company, "attendance_date": day, "docstatus": 1},
				pluck="status",
				limit_page_length=0,
			)
		)
		out["present"] = {
			"value": marked.get("Present", 0) + marked.get("Work From Home", 0) + marked.get("Half Day", 0)
		}
	if can("Leave Application"):
		out["away"] = {
			"value": len(
				frappe.get_list(
					"Leave Application",
					filters={
						"company": company,
						"status": "Approved",
						"docstatus": 1,
						"from_date": ["<=", day],
						"to_date": [">=", day],
					},
					pluck="employee",
					limit_page_length=0,
				)
			)
		}
	if can("Salary Slip"):
		paid = _payroll(company, months)
		while paid and not paid[-1]["net"]:
			paid = paid[:-1]
		out["payroll"] = {"value": paid[-1]["net"] if paid else 0, "series": [one["net"] for one in paid]}
	if can("Job Opening"):
		out["openings"] = {
			"value": len(
				frappe.get_list(
					"Job Opening",
					filters={"company": company, "status": "Open"},
					pluck="name",
					limit_page_length=0,
				)
			)
		}
	return out


def _departments(people) -> list[dict]:
	"""Who works where now, the largest department first."""
	here = Counter(one.department or "" for one in people if one.status == "Active")
	return [
		{
			"department": name,
			"label": frappe.db.get_value("Department", name, "department_name") or name,
			"count": n,
		}
		for name, n in here.most_common(FEW)
	]


def _moves(months, people) -> list[dict]:
	"""Who joined and who left, month by month."""
	joined = Counter(month_of(one.date_of_joining) for one in people if one.date_of_joining)
	left = Counter(month_of(one.relieving_date) for one in people if one.relieving_date)
	return [
		{
			"month": one.isoformat(),
			"joined": joined.get(one.isoformat(), 0),
			"left": left.get(one.isoformat(), 0),
		}
		for one in months
	]


STATUSES = ("Present", "Work From Home", "Half Day", "On Leave", "Absent")


def _attendance(company) -> list[dict]:
	"""Each of the last thirty days, how many were marked each way."""
	day = getdate(today())
	since = add_days(day, -(DAYS - 1))
	by = defaultdict(Counter)
	for one in frappe.get_list(
		"Attendance",
		filters={"company": company, "docstatus": 1, "attendance_date": ["between", [since, day]]},
		fields=["attendance_date", "status"],
		limit_page_length=0,
	):
		by[str(one.attendance_date)][one.status] += 1
	return [
		{
			"day": str(add_days(since, step)),
			**{status: by[str(add_days(since, step))].get(status, 0) for status in STATUSES},
		}
		for step in range(DAYS)
	]


def _leave_year(company) -> date:
	"""The first day of the leave period today is in: the active Leave Period,
	or the fiscal year where there is none."""
	found = frappe.get_all(
		"Leave Period",
		filters={"company": company, "is_active": 1, "from_date": ["<=", today()], "to_date": [">=", today()]},
		pluck="from_date",
		order_by="from_date desc",
		limit=1,
	)
	return getdate(found[0]) if found else closing.year_began(company=company)


def _leave(company) -> list[dict]:
	"""This leave period's approved leave, in days, kind by kind."""
	if not can("Leave Application"):
		return []
	taken = Counter()
	for one in frappe.get_list(
		"Leave Application",
		filters={
			"company": company,
			"status": "Approved",
			"docstatus": 1,
			"from_date": [">=", _leave_year(company)],
		},
		fields=["leave_type", "total_leave_days"],
		limit_page_length=0,
	):
		taken[one.leave_type] += flt(one.total_leave_days)
	return [{"leave_type": name, "days": days} for name, days in taken.most_common(FEW)]


def _payroll(company, months) -> list[dict]:
	"""Each month's submitted slips: what they came to before and after
	deductions."""
	by = defaultdict(lambda: {"gross": 0.0, "net": 0.0})
	for one in frappe.get_list(
		"Salary Slip",
		filters={"company": company, "docstatus": 1, "start_date": [">=", months[0]]},
		fields=["start_date", "base_gross_pay", "base_net_pay"],
		limit_page_length=0,
	):
		month = by[month_of(one.start_date)]
		month["gross"] += flt(one.base_gross_pay)
		month["net"] += flt(one.base_net_pay)
	return [{"month": one.isoformat(), **by[one.isoformat()]} for one in months]


def _expenses(company) -> list[dict]:
	"""This fiscal year's claims, by what they were for."""
	if not can("Expense Claim"):
		return []
	spent = Counter()
	claims = frappe.get_list(
		"Expense Claim",
		filters={
			"company": company,
			"docstatus": 1,
			"posting_date": [">=", closing.year_began(company=company)],
		},
		pluck="name",
		limit_page_length=0,
	)
	for one in frappe.get_all(
		"Expense Claim Detail",
		filters={"parent": ["in", claims or [""]]},
		fields=["expense_type", "sanctioned_amount"],
	):
		spent[one.expense_type] += flt(one.sanctioned_amount)
	return [{"expense_type": name, "amount": amount} for name, amount in spent.most_common(FEW)]


def _funnel(company) -> list[dict]:
	"""The last twelve months' applicants, how many were interviewed, offered,
	accepted and joined."""
	since = add_months(get_first_day(today()), -(MONTHS - 1))
	applicants = frappe.get_list(
		"Job Applicant", filters={"creation": [">=", since]}, pluck="name", limit_page_length=0
	)
	if not applicants:
		return []
	interviewed = set(
		frappe.get_all(
			"Interview",
			filters={"job_applicant": ["in", applicants], "docstatus": ["<", 2]},
			pluck="job_applicant",
		)
	)
	offers = frappe.get_all(
		"Job Offer",
		filters={"job_applicant": ["in", applicants], "docstatus": ["<", 2]},
		fields=["job_applicant", "status"],
	)
	joined = set(
		frappe.get_all("Employee", filters={"job_applicant": ["in", applicants]}, pluck="job_applicant")
	)
	return [
		{"step": "Job Applicant", "count": len(applicants)},
		{"step": "Interview", "count": len(interviewed)},
		{"step": "Job Offer", "count": len({one.job_applicant for one in offers})},
		{"step": "Accepted", "count": len({one.job_applicant for one in offers if one.status == "Accepted"})},
		{"step": "Joined", "count": len(joined)},
	]
