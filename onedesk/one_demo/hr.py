"""The people side: what each is paid and the payroll run for the last three
months, leave given and taken and asked for, attendance and this morning's
check-ins, expense claims at every stage, and two openings being hired for."""

import frappe
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate

from onedesk.one_demo.base import COMPANY, ago, ahead, as_user, dated, make, on, save, today
from onedesk.one_demo.people import PEOPLE

HR = "mariam@one.test"
ACCOUNTS = "huda@one.test"


def run(password=None):
	_site()
	with as_user(HR):
		_pay()
		_leave()
		_attendance()
		_hiring()
		_onboarding()
		_payroll()
		_by_the_hour()
		_leaving()
	_claims()
	with as_user(HR):
		_interview()
		_shifts()
		_requests()
		_overtime()
		_appraisal()
		_profiles()


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
	if not frappe.db.exists("Salary Component", HOURS):
		make({"doctype": "Salary Component", "salary_component": HOURS, "salary_component_abbr": "HW", "type": "Earning"})
	if not frappe.db.exists("Salary Structure", HOURLY):
		make(
			{
				"doctype": "Salary Structure",
				"name": HOURLY,
				"__newname": HOURLY,
				"company": COMPANY,
				"currency": "AED",
				"payroll_frequency": "Monthly",
				"is_active": "Yes",
				"salary_slip_based_on_timesheet": 1,
				"salary_component": HOURS,
				"hour_rate": HOUR_RATE,
				"earnings": [{"salary_component": "Transport Allowance", "abbr": "TA", "amount": 300}],
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
				"salary_structure": HOURLY if first == PAID_BY_THE_HOUR else structure,
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
		if frappe.db.exists("Payroll Entry", {"start_date": starts, "docstatus": 1, "salary_slip_based_on_timesheet": 0}):
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


PAID_BY_THE_HOUR = "Imran"
HOURLY = "Sahara Hourly"
HOURS = "Hours Worked"
HOUR_RATE = 30


def _by_the_hour():
	"""Imran's pay each month, worked out from his submitted timesheets by a
	payroll of its own, as ERPNext pays anybody on a timesheet structure."""
	bank = frappe.db.get_value("Account", {"company": COMPANY, "account_type": "Bank", "is_group": 0})
	cost_center = frappe.db.get_value("Company", COMPANY, "cost_center")
	for back in (3, 2, 1):
		starts = get_first_day(add_months(today(), -back))
		if frappe.db.exists("Payroll Entry", {"start_date": starts, "docstatus": 1, "salary_slip_based_on_timesheet": 1}):
			continue
		entry = frappe.new_doc("Payroll Entry")
		entry.update(
			{
				"company": COMPANY,
				"salary_slip_based_on_timesheet": 1,
				"payroll_frequency": "Monthly",
				"start_date": starts,
				"end_date": get_last_day(starts),
				"posting_date": get_last_day(starts),
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


LEAVER = "Joseph"
RESIGNED = "Rule Under Unlimited Contract on resignation (UAE)"


def _leaving():
	"""Joseph resigns after four years in the workshop and works to the end
	of last month, paid for it in its payroll. His end of service is the UAE
	rule on resignation: 14 days of basic pay for each year between three and
	five. HRMS ships the rule counting no pay at all, so the people officer
	first says basic pay counts. The books keep the account it is spent from,
	and pay him."""
	from hrms.overrides.employee_payment_entry import get_payment_entry_for_employee

	employee = _employee(LEAVER)
	if frappe.db.exists("Gratuity", {"employee": employee, "docstatus": 1}):
		return
	for rule in frappe.get_all("Gratuity Rule", filters={"name": ["like", "%(UAE)"]}, pluck="name"):
		doc = frappe.get_doc("Gratuity Rule", rule)
		if not doc.applicable_earnings_component:
			doc.append("applicable_earnings_component", {"salary_component": "Basic Salary"})
			doc.save()
	last = get_last_day(add_months(today(), -1))
	worker = frappe.get_doc("Employee", employee)
	worker.resignation_letter_date = add_days(last, -30)
	worker.relieving_date = last
	worker.reason_for_leaving = "Moving back home"
	worker.save()
	with as_user(ACCOUNTS):
		parent = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Indirect Expenses", "is_group": 1})
		expense = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "End of Service Benefits"}) or make(
			{"doctype": "Account", "account_name": "End of Service Benefits", "parent_account": parent, "company": COMPANY, "account_type": "Expense Account"}
		).name
	gratuity = frappe.new_doc("Gratuity")
	gratuity.update(
		{
			"employee": employee,
			"company": COMPANY,
			"gratuity_rule": RESIGNED,
			"expense_account": expense,
			"payable_account": _payable(),
			"cost_center": frappe.db.get_value("Company", COMPANY, "cost_center"),
			"pay_via_salary_slip": 0,
		}
	)
	dated(gratuity, last)
	gratuity = save(gratuity, submit=True)
	with as_user(ACCOUNTS):
		paid = get_payment_entry_for_employee("Gratuity", gratuity.name)
		on_day = min(add_days(last, 5), today())
		paid.reference_no = f"EOSB-{gratuity.name[-5:]}"
		paid.reference_date = on_day
		dated(paid, on_day)
		save(paid, submit=True)


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
	asked = (
		("Rania", "Privilege Leave", on(4, 13), 5, True),
		("Arun", "Sick Leave", on(6, 8), 2, True),
		("Nadia", "Privilege Leave", on(8, 3), 10, True),
		("Sanjay", "Privilege Leave", ago(4), 3, True),
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


SITE = ("Bayview Tower site", 25.0805, 55.1403, 200)
ON_SITE = ("Bilal", "Imran")


def _site():
	"""The tower counts its time by attendance on its site."""
	from onedesk.one_project import hours

	name, latitude, longitude, radius = SITE
	if not frappe.db.exists("Shift Location", name):
		make({"doctype": "Shift Location", "location_name": name, "latitude": latitude, "longitude": longitude, "checkin_radius": radius})
	tower = frappe.get_doc("Project", {"project_name": "Bayview Tower Curtain Wall"})
	if tower.one_time != hours.ATTENDANCE:
		tower.update({"one_time": hours.ATTENDANCE, "one_site": name})
		tower.save(ignore_permissions=True)


def _logged(employee: str, day) -> bool:
	return bool(
		frappe.db.sql(
			"""select 1 from `tabTimesheet Detail` log join `tabTimesheet` sheet on sheet.name = log.parent
			where sheet.employee = %s and sheet.docstatus < 2 and date(log.from_time) = %s limit 1""",
			(employee, day),
		)
	)


def _attendance():
	"""The last two weeks for the workshop, and this morning's check-ins. The
	installers on the tower clock in at its site, so their days are the
	tower's time."""
	workshop = [one[0] for one in PEOPLE if one[3] == "Workshop"]
	for back in range(14, 0, -1):
		day = ago(back)
		if day.weekday() == 6:
			continue
		for i, first in enumerate(workshop):
			employee = _employee(first)
			if frappe.db.exists("Attendance", {"employee": employee, "attendance_date": day}):
				continue
			if first == LEAVER and getdate(day) > get_last_day(add_months(today(), -1)):
				continue
			if frappe.db.exists("Leave Application", {"employee": employee, "from_date": ["<=", day], "to_date": [">=", day], "docstatus": ["<", 2]}):
				continue
			status = "Absent" if (back + i) % 17 == 0 else "Half Day" if (back + i) % 11 == 0 else "Present"
			if first in ON_SITE and status != "Absent" and not _logged(employee, day):
				make({"doctype": "Employee Checkin", "employee": employee, "log_type": "IN", "time": f"{day} 07:30:00", "latitude": SITE[1], "longitude": SITE[2]})
			try:
				make({"doctype": "Attendance", "employee": employee, "attendance_date": day, "status": status, "company": COMPANY, "shift": frappe.db.get_value("Employee", employee, "default_shift")}, submit=True)
			except frappe.ValidationError:
				frappe.clear_last_message()
	for first, at in (("Samir", "07:52"), ("Rania", "08:04"), ("Tariq", "07:31"), ("Arun", "07:40"), ("Ravi", "08:17")):
		employee = _employee(first)
		if not frappe.db.exists("Employee Checkin", {"employee": employee, "time": [">=", f"{today()} 00:00:00"]}):
			make({"doctype": "Employee Checkin", "employee": employee, "log_type": "IN", "time": f"{today()} {at}:00"})


def _claims():
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
					"status": "Accepted",
					"offer_terms": [{"offer_term": _term(term), "value": value} for term, value in OFFER],
					"terms": "<p>This offer stands for fourteen days. It starts once your visa and labour card are issued, and is subject to references and a medical check.</p>",
				},
				submit=True,
			)
			make(
				{
					"doctype": "Appointment Letter",
					"job_applicant": applicant.name,
					"applicant_name": name,
					"company": COMPANY,
					"appointment_date": ahead(30),
					"appointment_letter_template": _appointment(),
				}
			)


JOINING = (
	("Prepare the employment contract and visa", HR, 0, 5),
	("Issue the laptop and site PPE", "karim@one.test", 20, 3),
	("Plan the first week on site", "samir@one.test", 22, 5),
)


def _onboarding():
	"""Feras accepted the Site Engineer offer, so his onboarding is under way:
	HRMS makes a checklist project and gives each step to its person."""
	offer = frappe.db.get_value("Job Offer", {"applicant_name": "Feras Odeh", "docstatus": 1}, ["name", "job_applicant", "designation"], as_dict=True)
	if not offer or frappe.db.exists("Employee Onboarding", {"job_offer": offer.name}):
		return
	make(
		{
			"doctype": "Employee Onboarding",
			"job_applicant": offer.job_applicant,
			"job_offer": offer.name,
			"employee_name": "Feras Odeh",
			"designation": offer.designation,
			"company": COMPANY,
			"department": frappe.db.get_value("Department", {"department_name": "Projects"}),
			"date_of_joining": ahead(30),
			"boarding_begins_on": ahead(2),
			"activities": [
				{"activity_name": what, "user": who, "begin_on": begins, "duration": takes}
				for what, who, begins, takes in JOINING
			],
		},
		submit=True,
	)


OFFER = (
	("Monthly Salary", "AED 16,000"),
	("Housing Allowance", "AED 4,000 a month"),
	("Annual Leave", "30 days a year"),
	("Probation", "Six months"),
	("Working Hours", "Monday to Saturday, 8:00 to 17:00"),
)


APPOINTED = (
	("Reporting To", "Samir Aoun, Projects Manager"),
	("Place of Work", "Our site projects across Dubai, and the workshop in Dubai Investments Park"),
	("Pay", "As in your offer, paid on the last working day of each month"),
	("Notice", "One month on either side once probation ends"),
)


def _appointment():
	"""The template the demo's letters are written from, as the people officer keeps it."""
	name = "Site Staff"
	if not frappe.db.exists("Appointment Letter Template", name):
		make(
			{
				"doctype": "Appointment Letter Template",
				"template_name": name,
				"introduction": f"We are glad to appoint you at {COMPANY}, on the terms of the offer you accepted.",
				"terms": [{"title": term, "description": value} for term, value in APPOINTED],
				"closing_notes": "Please sign a copy of this letter and bring it on your first day. We look forward to working with you.",
			}
		)
	return name


def _term(name):
	if not frappe.db.exists("Offer Term", name):
		make({"doctype": "Offer Term", "offer_term": name})
	return name


def _interview():
	"""Mira Costa's technical interview for Site Engineer, with Samir, done
	two days ago and waiting for his feedback."""
	kind = "Site Engineer Technical"
	if not frappe.db.exists("Interview Type", kind):
		for skill in ("Site Management", "Reading Drawings"):
			if not frappe.db.exists("Skill", skill):
				make({"doctype": "Skill", "skill_name": skill})
		make(
			{
				"doctype": "Interview Type",
				"interview_type_name": kind,
				"designation": "Site Engineer",
				"expected_skill_set": [{"skill": "Site Management"}, {"skill": "Reading Drawings"}],
				"description": "An hour with the projects manager on a real site's drawings.",
			}
		)
	applicant = frappe.db.get_value("Job Applicant", {"email_id": "mira.costa@example.com"})
	if applicant and not frappe.db.exists("Interview", {"job_applicant": applicant}):
		make(
			{
				"doctype": "Interview",
				"job_applicant": applicant,
				"interview_type": kind,
				"scheduled_on": ago(2),
				"from_time": "10:00:00",
				"to_time": "11:00:00",
				"status": "Pending",
				"interview_details": [{"interviewer": "samir@one.test"}],
			}
		)


SHIFT = ("Workshop Day", "07:00:00", "16:00:00")


def _shifts():
	"""The workshop's day shift, and two of the crew asking for it: one waiting
	for Mariam, one she already turned down."""
	name, starts, ends = SHIFT
	if not frappe.db.exists("Shift Type", name):
		make({"doctype": "Shift Type", "name": name, "__newname": name, "start_time": starts, "end_time": ends})
	for first, days, state in (("Ravi", 3, None), ("Bilal", 10, "Rejected")):
		employee = _employee(first)
		if frappe.db.exists("Shift Request", {"employee": employee, "shift_type": name}):
			continue
		frappe.db.set_value("Employee", employee, "shift_request_approver", HR)
		request = make(
			{
				"doctype": "Shift Request",
				"shift_type": name,
				"employee": employee,
				"company": COMPANY,
				"from_date": ahead(days),
				"to_date": ahead(days + 13),
				"approver": HR,
				"status": "Draft",
			}
		)
		if state:
			from onedesk.one_hr import shift

			shift.reject(request.name, "The workshop has enough people on days that fortnight.")


def _requests():
	"""Nadia at the customer's showroom all day yesterday, asking for the day
	to count."""
	employee = _employee("Nadia")
	if not frappe.db.exists("Attendance Request", {"employee": employee}):
		make(
			{
				"doctype": "Attendance Request",
				"employee": employee,
				"company": COMPANY,
				"from_date": ago(1),
				"to_date": ago(1),
				"reason": "On Duty",
				"one_reason": "Customer Site",
				"explanation": "At the Nordlicht showroom all day for the design workshop.",
			}
		)


def _overtime():
	"""Overtime in the workshop, AED 45 an hour, one and a quarter times on
	ordinary days."""
	name = "Workshop Overtime"
	if frappe.db.exists("Overtime Type", name):
		return
	component = "Overtime"
	if not frappe.db.exists("Salary Component", component):
		make({"doctype": "Salary Component", "salary_component": component, "salary_component_abbr": "OT", "type": "Earning"})
	make(
		{
			"doctype": "Overtime Type",
			"name": name,
			"__newname": name,
			"overtime_salary_component": component,
			"overtime_calculation_method": "Fixed Hourly Rate",
			"hourly_rate": 45,
			"standard_multiplier": 1.25,
			"applicable_for_weekend": 0,
			"maximum_overtime_hours_allowed": 4,
		}
	)


def _appraisal():
	"""This year's mid-year review: Rania's appraisal, which Samir writes."""
	cycle = f"Mid-Year {today().year}"
	if frappe.db.exists("Appraisal Cycle", {"cycle_name": cycle}):
		return
	for title in ("Delivery on Time", "Site Safety"):
		if not frappe.db.exists("KRA", title):
			make({"doctype": "KRA", "title": title})
	template = "Project Coordinator"
	if not frappe.db.exists("Appraisal Template", template):
		make({"doctype": "Appraisal Template", "template_title": template, "goals": [{"key_result_area": "Delivery on Time", "per_weightage": 60}, {"key_result_area": "Site Safety", "per_weightage": 40}]})
	made = make({"doctype": "Appraisal Cycle", "cycle_name": cycle, "company": COMPANY, "start_date": on(1, 1), "end_date": on(6, 30)})
	make({"doctype": "Appraisal", "employee": _employee("Rania"), "company": COMPANY, "appraisal_cycle": made.name, "appraisal_template": template})


# What three people's profiles carry beyond their job: the documents HR
# keeps, where they studied and where they worked before
# (AccountCenter's Profile).
PROFILES = {
	"Layla": {
		"documents": (("Emirates ID", "784-1991-4410392-1", 400), ("Passport", "N4471932", 20)),
		"education": (("MBA", "INSEAD", "Post Graduate", 2016), ("BEng Civil Engineering", "American University of Sharjah", "Graduate", 2012)),
		"work": (("Al Futtaim Glass", "Projects Manager", "5 years"),),
	},
	"Mariam": {
		"documents": (("Emirates ID", "784-1988-2093114-7", 700), ("Residence Permit", "201/2019/7731942", -12)),
		"education": (("BA Human Resource Management", "University of Jordan", "Graduate", 2010),),
		"work": (("Emaar Hospitality", "HR Officer", "4 years"),),
	},
	"Nadia": {
		"documents": (("Emirates ID", "784-1995-6630218-3", 500), ("Work Permit", "WP-88123", 90)),
		"education": (("BArch", "Lebanese American University", "Graduate", 2017),),
		"work": (),
	},
}


def _profiles():
	for first, said in PROFILES.items():
		name = _employee(first)
		if not name:
			continue
		employee = frappe.get_doc("Employee", name)
		if employee.get("one_documents") or employee.get("education"):
			continue
		for kind, number, days in said["documents"]:
			if frappe.db.exists("Identification Document Type", kind):
				employee.append("one_documents", {"document_type": kind, "number": number, "expires_on": add_days(today(), days)})
		for qualification, school, level, year in said["education"]:
			employee.append("education", {"qualification": qualification, "school_univ": school, "level": level, "year_of_passing": year})
		for company, title, years in said["work"]:
			employee.append("external_work_history", {"company_name": company, "designation": title, "total_experience": years})
		employee.save()
