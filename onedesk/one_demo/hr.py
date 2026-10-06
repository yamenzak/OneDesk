"""The people side: what each is paid and the payroll run for the last three
months, leave given and taken and asked for, attendance and this morning's
check-ins, expense claims at every stage, and two openings being hired for."""

import frappe
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate

from onedesk.one_demo.base import COMPANY, ahead, ago, as_user, dated, make, on, save, today
from onedesk.one_demo.people import PEOPLE

HR = "mariam@one.test"
ACCOUNTS = "huda@one.test"


def run(password=None):
	with as_user(HR):
		_pay()
		_leave()
		_attendance()
		_hiring()
		_payroll()
	_claims()


def _employee(first):
	return frappe.db.get_value("Employee", {"first_name": first})


def _pay():
	for name, abbr, kind in (("Basic Salary", "BS", "Earning"), ("Housing Allowance", "HA", "Earning"), ("Transport Allowance", "TA", "Earning")):
		if not frappe.db.exists("Salary Component", name):
			make({"doctype": "Salary Component", "salary_component": name, "salary_component_abbr": abbr, "type": kind})
	structure = "Sahara Standard"
	if not frappe.db.exists("Salary Structure", structure):
		make(
			{
				"doctype": "Salary Structure",
				"name": structure,
				"__newname": structure,
				"company": COMPANY,
				"currency": "AED",
				"payroll_frequency": "Monthly",
				"is_active": "Yes",
				"earnings": [
					{"salary_component": "Basic Salary", "abbr": "BS", "amount_based_on_formula": 1, "formula": "base * 0.6"},
					{"salary_component": "Housing Allowance", "abbr": "HA", "amount_based_on_formula": 1, "formula": "base * 0.25"},
					{"salary_component": "Transport Allowance", "abbr": "TA", "amount_based_on_formula": 1, "formula": "base * 0.15"},
				],
			},
			submit=True,
		)
	for first, _last, _email, _dept, _desig, _gender, joined, pay, *_rest in PEOPLE:
		employee = _employee(first)
		if frappe.db.exists("Salary Structure Assignment", {"employee": employee, "docstatus": 1}):
			continue
		starts = max(on(1, 1), getdate(f"{joined[0]}-{joined[1]:02d}-{joined[2]:02d}"))
		make(
			{
				"doctype": "Salary Structure Assignment",
				"employee": employee,
				"salary_structure": structure,
				"company": COMPANY,
				"currency": "AED",
				"from_date": starts,
				"base": pay,
				"payroll_payable_account": _payable(),
			},
			submit=True,
		)


def _payable():
	return frappe.db.get_value("Company", COMPANY, "default_payroll_payable_account") or frappe.db.get_value(
		"Account", {"company": COMPANY, "account_name": ["like", "%Payroll Payable%"], "is_group": 0}
	)


def _payroll():
	bank = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0})
	cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")
	for back in (3, 2, 1):
		starts = get_first_day(add_months(today(), -back))
		ends = get_last_day(starts)
		if frappe.db.exists("Payroll Entry", {"start_date": starts, "docstatus": 1}):
			continue
		entry = frappe.new_doc("Payroll Entry")
		entry.update(
			{
				"company": COMPANY,
				"payroll_frequency": "Monthly",
				"start_date": starts,
				"end_date": ends,
				"posting_date": ends,
				"currency": "AED",
				"exchange_rate": 1,
				"payroll_payable_account": _payable(),
				"cost_center": cost_center,
				"payment_account": bank,
			}
		)
		entry.fill_employee_details()
		entry = save(entry, submit=True)
		entry.reload()
		entry.submit_salary_slips()


def _leave():
	year_starts, year_ends = on(1, 1), getdate(f"{today().year}-12-31")
	for first, *_rest in PEOPLE:
		employee = _employee(first)
		for kind, days in (("Privilege Leave", 30), ("Sick Leave", 15)):
			if frappe.db.exists("Leave Allocation", {"employee": employee, "leave_type": kind, "docstatus": 1}):
				continue
			make(
				{
					"doctype": "Leave Allocation",
					"employee": employee,
					"leave_type": kind,
					"from_date": year_starts,
					"to_date": year_ends,
					"new_leaves_allocated": days,
				},
				submit=True,
			)
	#: who, kind, from, days, approved
	asked = (
		("Rania", "Privilege Leave", on(4, 13), 5, True),
		("Arun", "Sick Leave", on(6, 8), 2, True),
		("Nadia", "Privilege Leave", on(8, 3), 10, True),
		("Joseph", "Privilege Leave", ago(4), 3, True),
		("Omar", "Privilege Leave", ahead(12), 6, None),
		("Yousef", "Sick Leave", ago(1), 1, None),
		("Karim", "Privilege Leave", ahead(30), 4, False),
	)
	for first, kind, starts, days, approved in asked:
		employee = _employee(first)
		if frappe.db.exists("Leave Application", {"employee": employee, "from_date": starts}):
			continue
		approver = frappe.db.get_value("Employee", frappe.db.get_value("Employee", employee, "reports_to"), "user_id") or HR
		application = frappe.get_doc(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": kind,
				"from_date": starts,
				"to_date": add_days(starts, days - 1),
				"leave_approver": approver,
				"description": "Family visit" if kind == "Privilege Leave" else "Unwell",
				"status": "Open" if approved is None else "Approved" if approved else "Rejected",
			}
		)
		application.insert()
		if approved is not None:
			application.submit()


def _attendance():
	"""The last two weeks for the workshop, and this morning's check-ins."""
	workshop = [one[0] for one in PEOPLE if one[3] == "Workshop"]
	for back in range(14, 0, -1):
		day = ago(back)
		if day.weekday() == 6:
			continue
		for i, first in enumerate(workshop):
			employee = _employee(first)
			if frappe.db.exists("Attendance", {"employee": employee, "attendance_date": day}):
				continue
			status = "Absent" if (back + i) % 17 == 0 else "Half Day" if (back + i) % 11 == 0 else "Present"
			try:
				make({"doctype": "Attendance", "employee": employee, "attendance_date": day, "status": status, "company": COMPANY}, submit=True)
			except frappe.ValidationError:
				frappe.clear_last_message()
	for first, at in (("Samir", "07:52"), ("Rania", "08:04"), ("Tariq", "07:31"), ("Arun", "07:40"), ("Ravi", "08:17")):
		employee = _employee(first)
		if not frappe.db.exists("Employee Checkin", {"employee": employee, "time": [">=", f"{today()} 00:00:00"]}):
			make({"doctype": "Employee Checkin", "employee": employee, "log_type": "IN", "time": f"{today()} {at}:00"})


def _claims():
	#: who, project, kind, amount, what, approved, days ago
	claims = (
		("Rania", "Mansour Villa Windows and Doors", "Travel", 340, "Taxis to Al Barsha for the frame installation", True, 40),
		("Tariq", "Workshop CNC Upgrade", "Others", 1180, "Power cables and isolators for the CNC bay", True, 22),
		("Samir", "Bayview Tower Curtain Wall", "Food", 260, "Lunch with the consultant after the mock-up review", None, 6),
		("Karim", None, "Calls", 95, "Roaming during the supplier visit", False, 15),
	)
	for first, project_title, kind, amount, what, approved, days in claims:
		employee = _employee(first)
		if frappe.db.exists("Expense Claim", {"employee": employee, "posting_date": ago(days)}):
			continue
		user = frappe.db.get_value("Employee", employee, "user_id")
		approver = frappe.db.get_value("Employee", frappe.db.get_value("Employee", employee, "reports_to"), "user_id")
		project = frappe.db.get_value("Project", {"project_name": project_title}) if project_title else None
		with as_user(user):
			claim = frappe.new_doc("Expense Claim")
			claim.update({"employee": employee, "company": COMPANY, "expense_approver": approver, "project": project, "payable_account": _claims_payable()})
			dated(claim, ago(days))
			claim.append("expenses", {"expense_date": ago(days + 1), "expense_type": kind, "description": what, "amount": amount, "sanctioned_amount": amount, "project": project})
			claim = save(claim)
		if approved is not None:
			from onedesk.one_hr import expense

			with as_user(approver):
				if approved:
					expense.approve(claim.name)
				else:
					expense.reject(claim.name, "Roaming is on the company phone plan already.")
			claim.reload()
		if approved and days > 30:
			# Paid back by the books with the next bank run.
			from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

			with as_user(ACCOUNTS):
				paid = get_payment_entry_for_employee("Expense Claim", claim.name)
				paid.reference_no = f"CLAIM-{claim.name[-5:]}"
				paid.reference_date = ago(days - 5)
				dated(paid, ago(days - 5))
				save(paid, submit=True)


def _claims_payable():
	return frappe.db.get_value("Company", COMPANY, "default_expense_claim_payable_account") or frappe.db.get_value(
		"Company", COMPANY, "default_payable_account"
	)


def _hiring():
	openings = (
		("Site Engineer", "Projects", 2, "Run installation sites from survey to handover, with the client's consultant."),
		("Glazier", "Workshop", 3, "Glaze, seal and finish window and door units in the workshop."),
	)
	for title, department, vacancies, said in openings:
		if frappe.db.exists("Job Opening", {"job_title": title}):
			continue
		make(
			{
				"doctype": "Job Opening",
				"job_title": title,
				"designation": title if frappe.db.exists("Designation", title) else make({"doctype": "Designation", "designation_name": title}).name,
				"company": COMPANY,
				"department": frappe.db.get_value("Department", {"department_name": department}),
				"status": "Open",
				"planned_vacancies": vacancies,
				"description": said,
			}
		)
	applicants = (
		("Hassan Jaber", "hassan.jaber@example.com", "Site Engineer", "Open"),
		("Mira Costa", "mira.costa@example.com", "Site Engineer", "Replied"),
		("Feras Odeh", "feras.odeh@example.com", "Site Engineer", "Accepted"),
		("Ramesh Iyer", "ramesh.iyer@example.com", "Glazier", "Hold"),
		("Wei Chen", "wei.chen@example.com", "Glazier", "Rejected"),
		("Paul Mensah", "paul.mensah@example.com", "Glazier", "Open"),
	)
	for name, email, title, status in applicants:
		if frappe.db.exists("Job Applicant", {"email_id": email}):
			continue
		opening = frappe.db.get_value("Job Opening", {"job_title": title})
		applicant = make({"doctype": "Job Applicant", "applicant_name": name, "email_id": email, "job_title": opening, "status": status, "source": "Website Listing"})
		if status == "Accepted":
			make(
				{
					"doctype": "Job Offer",
					"job_applicant": applicant.name,
					"applicant_name": name,
					"designation": title,
					"company": COMPANY,
					"offer_date": ago(3),
					"status": "Awaiting Response",
				}
			)
