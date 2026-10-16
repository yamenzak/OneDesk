"""The rest of the people side, after the year `hr` ran: what each person may
take and when, the shifts they are put on, what they are trained in and how
they are rated, a transfer and a promotion, travel and an advance, pay
corrected and pay held, and Joseph's leaving told to the end. Each record a
OneHR screen lists, so none of them opens empty."""

import frappe
from frappe.utils import add_days, add_months, get_first_day, get_last_day

from onedesk.one_demo.base import COMPANY, ago, ahead, as_user, make, on, once, save, today
from onedesk.one_demo.hr import ACCOUNTS, HR, LEAVER, _employee, _payable

#: Each part, in order; `run` makes the ones not made yet.
PARTS = (
	"_grades",
	"_leave_rules",
	"_shifts",
	"_training",
	"_growth",
	"_moves",
	"_travel",
	"_grievance",
	"_hiring",
	"_pay",
	"_leaving",
	"_clock",
	"_letters",
	"_templates",
	"_insurance",
	"_feedback",
	"_overtime",
)


def run(password=None):
	with as_user(HR):
		for part in PARTS:
			globals()[part]()


def _user(first):
	return frappe.db.get_value("Employee", _employee(first), "user_id")


# ------------------------------------------------------------------ grades


def _grades():
	"""Grades the workshop and the office are paid by."""
	for grade, pay in (("Workshop", 4500), ("Office", 12000), ("Management", 25000)):
		once(
			"Employee Grade",
			{"name": grade},
			{"__newname": grade, "default_base_pay": pay, "default_salary_structure": "Sahara Standard"},
		)


# ------------------------------------------------------------------ leave


def _leave_rules():
	"""The leave policy everybody is on, the days the workshop may not take
	off, a day back taken from Bilal, and Tariq's untaken days paid out."""
	annual = frappe.db.get_value("Leave Type", {"name": ["like", "%Annual%"]}) or "Privilege Leave"
	sick = frappe.db.get_value("Leave Type", {"name": ["like", "%Sick%"]}) or "Sick Leave"
	policy = once(
		"Leave Policy",
		{"title": "Sahara Standard Leave"},
		{
			"title": "Sahara Standard Leave",
			"leave_policy_details": [
				{"leave_type": annual, "annual_allocation": 30},
				{"leave_type": sick, "annual_allocation": 15},
			],
		},
		submit=True,
	)
	# Next year's, since this year's leave was allocated by hand.
	year = today().year + 1
	for first in ("Noor",):
		employee = _employee(first)
		if not frappe.db.exists("Leave Policy Assignment", {"employee": employee}):
			make(
				{
					"doctype": "Leave Policy Assignment",
					"employee": employee,
					"company": COMPANY,
					"leave_policy": policy.name,
					"effective_from": f"{year}-01-01",
					"effective_to": f"{year}-12-31",
				},
				submit=True,
			)
	once(
		"Leave Block List",
		{"leave_block_list_name": "Year-end handovers"},
		{
			"leave_block_list_name": "Year-end handovers",
			"company": COMPANY,
			"applies_to_all_departments": 0,
			"leave_block_list_dates": [
				{"block_date": f"{today().year}-12-{day:02d}", "reason": "Handovers before the holidays"}
				for day in (15, 16, 17)
			],
		},
	)
	_compensatory(annual)
	_adjusted(annual)
	_encashed(annual)


def _compensatory(annual):
	"""Yousef worked a holiday on site, and asks for the day back."""
	employee = _employee("Yousef")
	if frappe.db.exists("Compensatory Leave Request", {"employee": employee}):
		return
	holiday = frappe.db.get_value(
		"Holiday",
		{
			"parent": frappe.db.get_value("Company", COMPANY, "default_holiday_list"),
			"holiday_date": ["<", today()],
			"weekly_off": 0,
		},
		"holiday_date",
		order_by="holiday_date desc",
	)
	if not holiday:
		return
	if not frappe.db.exists("Attendance", {"employee": employee, "attendance_date": holiday, "docstatus": 1}):
		make(
			{
				"doctype": "Attendance",
				"employee": employee,
				"attendance_date": holiday,
				"status": "Present",
				"company": COMPANY,
			},
			submit=True,
		)
	with as_user(_user("Yousef")):
		make(
			{
				"doctype": "Compensatory Leave Request",
				"employee": employee,
				"work_from_date": holiday,
				"work_end_date": holiday,
				"leave_type": annual,
				"reason": "Glazing the Bayview lobby on the holiday, so the client could open on time",
			}
		)


def _adjusted(annual):
	"""Two days taken back from Bilal's allocation, given twice by mistake."""
	employee = _employee("Bilal")
	if frappe.db.exists("Leave Adjustment", {"employee": employee}):
		return
	allocation = frappe.db.get_value(
		"Leave Allocation", {"employee": employee, "docstatus": 1, "leave_type": annual}
	)
	if allocation:
		make(
			{
				"doctype": "Leave Adjustment",
				"employee": employee,
				"company": COMPANY,
				"leave_allocation": allocation,
				"leave_type": annual,
				"adjustment_type": "Reduce",
				"leaves_to_adjust": 2,
				"posting_date": ago(10),
				"reason_for_adjustment": "Two days given twice when the allocation was copied",
			},
			submit=True,
		)


def _encashed(annual):
	"""Tariq is paid for five of his untaken days."""
	employee = _employee("Tariq")
	if frappe.db.exists("Leave Encashment", {"employee": employee}):
		return
	frappe.db.set_value("Leave Type", annual, "allow_encashment", 1)
	period = frappe.db.get_value("Leave Period", {"is_active": 1, "company": COMPANY})
	make(
		{
			"doctype": "Leave Encashment",
			"employee": employee,
			"company": COMPANY,
			"leave_type": annual,
			"leave_period": period,
			"encashment_date": ago(5),
			"encashment_days": 5,
			"currency": "AED",
		}
	)


# ------------------------------------------------------------------ shifts


def _shifts():
	"""The workshop's week on the Day shift, given by a schedule, and Bilal
	on the Night shift for the Marina job."""
	day = frappe.db.get_value("Shift Type", {"name": ["like", "%Day%"]}) or frappe.db.get_value(
		"Shift Type", {}
	)
	night = frappe.db.get_value("Shift Type", {"name": ["like", "%Night%"]}) or day
	schedule = once(
		"Shift Schedule",
		{"shift_type": day},
		{
			"__newname": "Workshop week",
			"shift_type": day,
			"frequency": "Every Week",
			"repeat_on_days": [
				{"day": one} for one in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
			],
		},
	)
	employee = _employee("Bilal")
	if not frappe.db.exists("Shift Assignment", {"employee": employee}):
		make(
			{
				"doctype": "Shift Assignment",
				"employee": employee,
				"company": COMPANY,
				"shift_type": night,
				"start_date": ago(14),
				"end_date": ahead(14),
				"status": "Active",
			},
			submit=True,
		)
	employee = _employee("Ravi")
	if not frappe.db.exists("Shift Schedule Assignment", {"employee": employee}):
		make(
			{
				"doctype": "Shift Schedule Assignment",
				"employee": employee,
				"company": COMPANY,
				"shift_schedule": schedule.name,
				"shift_status": "Active",
				"enabled": 1,
				"create_shifts_after": ago(7),
			}
		)


# ------------------------------------------------------------------ training


def _training():
	"""Working at height, taught to the installers, with what each made of it
	and how each did."""
	program = once(
		"Training Program",
		{"training_program": "Working at Height"},
		{
			"training_program": "Working at Height",
			"description": "Harnesses, anchors and edge protection for curtain wall installation.",
			"trainer_name": "Dubai Safety Institute",
		},
	)
	people = [_employee(first) for first in ("Yousef", "Bilal", "Imran")]
	event = frappe.db.get_value("Training Event", {"training_program": program.name})
	if not event:
		event = make(
			{
				"doctype": "Training Event",
				"event_name": "Working at Height, " + str(ago(20).year),
				"training_program": program.name,
				"type": "Workshop",
				"level": "Beginner",
				"company": COMPANY,
				"start_time": f"{ago(20)} 08:00:00",
				"end_time": f"{ago(20)} 16:00:00",
				"location": "Workshop yard, Al Quoz",
				"introduction": "A day on harnesses and edge protection, before the Bayview facade.",
				"event_status": "Completed",
				"employees": [{"employee": one, "attendance": "Present"} for one in people],
			},
			submit=True,
		).name
	if not frappe.db.exists("Training Result", {"training_event": event}):
		make(
			{
				"doctype": "Training Result",
				"training_event": event,
				"employees": [
					{"employee": one, "hours": 8, "grade": "A" if k == 0 else "B", "result": "Pass"}
					for k, one in enumerate(people)
				],
			},
			submit=True,
		)
	if not frappe.db.exists("Training Feedback", {"training_event": event}):
		with as_user(_user("Yousef")):
			make(
				{
					"doctype": "Training Feedback",
					"training_event": event,
					"employee": people[0],
					"feedback": "The anchor practice on the mock-up was the useful part.",
				},
				submit=True,
			)


# ------------------------------------------------------------------ growth


def _growth():
	"""Rania's goals for the year, the criteria feedback is given on, Samir's
	feedback on her, and the skills the workshop is mapped on."""
	for criteria in ("Quality of work", "Working with the client", "Site safety"):
		once("Employee Feedback Criteria", {"criteria": criteria}, {"criteria": criteria})
	employee = _employee("Rania")
	cycle = frappe.db.get_value("Appraisal Cycle", {})
	kra = frappe.db.get_value("KRA", {})
	if not frappe.db.exists("Goal", {"employee": employee}):
		make(
			{
				"doctype": "Goal",
				"goal_name": "Hand over the Mansour villa with no snags",
				"employee": employee,
				"appraisal_cycle": cycle,
				"kra": kra,
				"start_date": on(1, 1),
				"end_date": on(6, 30),
				"progress": 60,
			}
		)
	appraisal = frappe.db.get_value("Appraisal", {"employee": employee})
	if appraisal and not frappe.db.exists("Employee Performance Feedback", {"employee": employee}):
		with as_user("samir@one.test"):
			make(
				{
					"doctype": "Employee Performance Feedback",
					"employee": employee,
					"appraisal": appraisal,
					"appraisal_cycle": cycle,
					"reviewer": _employee("Samir"),
					"feedback": "Ran the villa handover well; the snag list was short and closed in a week.",
					"feedback_ratings": [
						{"criteria": "Quality of work", "per_weightage": 60, "rating": 0.8},
						{"criteria": "Site safety", "per_weightage": 40, "rating": 1},
					],
				},
				submit=True,
			)
	for skill in ("Glazing", "Silicone sealing", "Working at height"):
		once("Skill", {"name": skill}, {"skill_name": skill})
	employee = _employee("Joseph")
	if not frappe.db.exists("Employee Skill Map", {"employee": employee}):
		make(
			{
				"doctype": "Employee Skill Map",
				"employee": employee,
				"employee_skills": [
					{"skill": "Glazing", "proficiency": 0.8},
					{"skill": "Silicone sealing", "proficiency": 0.6},
				],
			}
		)


def _moves():
	"""Fatima is made Accountant, and Noor moves from Sales to Projects."""
	employee = _employee("Fatima")
	if not frappe.db.exists("Employee Promotion", {"employee": employee}):
		make(
			{
				"doctype": "Employee Promotion",
				"employee": employee,
				"company": COMPANY,
				"promotion_date": ago(3),
				"revised_ctc": 9000,
				"promotion_details": [
					{
						"property": "Designation",
						"current": "Accounts Assistant",
						"new": "Accountant",
						"fieldname": "designation",
					}
				],
			},
			submit=True,
		)
	employee = _employee("Noor")
	if not frappe.db.exists("Employee Transfer", {"employee": employee}):
		department = frappe.db.get_value("Department", {"department_name": "Projects", "company": COMPANY})
		make(
			{
				"doctype": "Employee Transfer",
				"employee": employee,
				"company": COMPANY,
				"transfer_date": ahead(10),
				"transfer_details": [
					{
						"property": "Department",
						"current": frappe.db.get_value("Employee", employee, "department"),
						"new": department,
						"fieldname": "department",
					}
				],
			}
		)


# ------------------------------------------------------------------ travel and an advance


def _travel():
	"""Samir flies to Riyadh to see a curtain wall supplier, with an advance
	for the trip, and the company van's log for the month."""
	purpose = once("Purpose of Travel", {"name": "Supplier visit"}, {"purpose_of_travel": "Supplier visit"})
	employee = _employee("Samir")
	if not frappe.db.exists("Travel Request", {"employee": employee}):
		make(
			{
				"doctype": "Travel Request",
				"employee": employee,
				"travel_type": "International",
				"purpose_of_travel": purpose.name,
				"travel_funding": "Fully Sponsored",
				"description": "Factory visit and mock-up review at the curtain wall supplier",
				"itinerary": [
					{
						"travel_from": "Dubai",
						"travel_to": "Riyadh",
						"mode_of_travel": "Flight",
						"departure_date": f"{ahead(12)} 07:00:00",
						"arrival_date": f"{ahead(12)} 09:00:00",
						"lodging_required": 1,
					},
					{
						"travel_from": "Riyadh",
						"travel_to": "Dubai",
						"mode_of_travel": "Flight",
						"departure_date": f"{ahead(14)} 19:00:00",
						"arrival_date": f"{ahead(14)} 22:00:00",
					},
				],
				"costings": [
					{
						"expense_type": frappe.db.get_value("Expense Claim Type", {"name": "Travel"})
						or frappe.db.get_value("Expense Claim Type", {}),
						"sponsored_amount": 3200,
						"total_amount": 3200,
					}
				],
			}
		)
	if not frappe.db.exists("Employee Advance", {"employee": employee}):
		advance_account = frappe.db.get_value(
			"Account", {"company": COMPANY, "account_name": ["like", "%Employee Advance%"], "is_group": 0}
		)
		make(
			{
				"doctype": "Employee Advance",
				"employee": employee,
				"company": COMPANY,
				"purpose": "Hotel and taxis for the Riyadh supplier visit",
				"advance_amount": 2500,
				"currency": "AED",
				"exchange_rate": 1,
				"posting_date": ago(1),
				"advance_account": advance_account,
			},
			submit=True,
		)
	_vehicle()


def _vehicle():
	license_plate = "DXB 41927"
	if not frappe.db.exists("Vehicle", license_plate):
		with as_user("Administrator"):
			make(
				{
					"doctype": "Vehicle",
					"license_plate": license_plate,
					"make": "Toyota",
					"model": "Hiace",
					"last_odometer": 84200,
					"uom": frappe.db.get_value("UOM", {"name": ["in", ["Litre", "Liter"]]}) or "Nos",
					"fuel_type": "Diesel",
					"employee": _employee("Sanjay"),
				}
			)
	if not frappe.db.exists("Vehicle Log", {"license_plate": license_plate}):
		once("Vehicle Service Item", {"name": "Oil change"}, {"service_item": "Oil change"})
		make(
			{
				"doctype": "Vehicle Log",
				"license_plate": license_plate,
				"employee": _employee("Sanjay"),
				"date": ago(4),
				"odometer": 85310,
				"fuel_qty": 62,
				"price": 3.1,
				"supplier": frappe.db.get_value("Supplier", {}),
				"service_detail": [
					{
						"service_item": "Oil change",
						"type": "Service",
						"frequency": "Quarterly",
						"expense_amount": 280,
					}
				],
			},
			submit=True,
		)


# ------------------------------------------------------------------ grievance


def _grievance():
	"""Arun says the workshop's extraction is not working, and HR looks into it."""
	kind = once(
		"Grievance Type",
		{"name": "Working conditions"},
		{
			"name": "Working conditions",
			"__newname": "Working conditions",
			"description": "The place, tools or hours work is done in.",
		},
	)
	employee = _employee("Arun")
	if frappe.db.exists("Employee Grievance", {"raised_by": employee}):
		return
	department = frappe.db.get_value("Department", {"department_name": "Workshop", "company": COMPANY})
	make(
		{
			"doctype": "Employee Grievance",
			"subject": "Fumes in the cutting bay",
			"raised_by": employee,
			"date": ago(9),
			"grievance_type": kind.name,
			"grievance_against_party": "Department",
			"grievance_against": department,
			"description": "The extraction over the cutting bay has been off for two weeks and the fumes stay in.",
			"status": "Investigated",
			"cause_of_grievance": "The extractor's motor burnt out and no repair was booked.",
		}
	)


# ------------------------------------------------------------------ hiring


def _hiring():
	"""Templates the openings and offers are written from, the year's staffing
	plan, a requisition for another estimator, and a referral."""
	designation = "Estimator"
	once(
		"Job Opening Template",
		{"template_title": "Workshop trade"},
		{
			"template_title": "Workshop trade",
			"designation": "Glazier",
			"department": frappe.db.get_value(
				"Department", {"department_name": "Workshop", "company": COMPANY}
			),
			"description": "Work in the Al Quoz workshop on window and door units.",
		},
	)
	once(
		"Job Offer Term Template",
		{"title": "Workshop offer"},
		{
			"title": "Workshop offer",
			"offer_terms": [
				{"offer_term": frappe.db.get_value("Offer Term", {}), "value": "Six months' probation"}
			],
		},
	)
	if not frappe.db.exists("Staffing Plan", {"company": COMPANY}):
		make(
			{
				"doctype": "Staffing Plan",
				"name": f"Sahara {today().year}",
				"__newname": f"Sahara {today().year}",
				"company": COMPANY,
				"from_date": str(on(1, 1)),
				"to_date": f"{today().year}-12-31",
				"staffing_details": [
					{"designation": "Site Engineer", "vacancies": 2, "estimated_cost_per_position": 16000},
					{"designation": "Glazier", "vacancies": 3, "estimated_cost_per_position": 4600},
				],
			}
		)
	employee = _employee("Omar")
	if not frappe.db.exists("Job Requisition", {"requested_by": employee}):
		# Raised by HR for him: hrms lets only HR make one.
		make(
			{
				"doctype": "Job Requisition",
				"designation": designation,
				"department": frappe.db.get_value(
					"Department", {"department_name": "Sales", "company": COMPANY}
				),
				"requested_by": employee,
				"no_of_positions": 1,
				"expected_compensation": 9000,
				"posting_date": str(ago(6)),
				"expected_by": str(ahead(45)),
				"description": "Tenders doubled since spring; Noor cannot price them all.",
				"reason_for_requesting": "More tenders than one estimator can price",
			}
		)
	employee = _employee("Rania")
	if not frappe.db.exists("Employee Referral", {"referrer": employee}):
		with as_user("rania@one.test"):
			make(
				{
					"doctype": "Employee Referral",
					"first_name": "Hassan",
					"last_name": "Qasim",
					"email": "hassan.qasim@example.com",
					"contact_no": "+971 50 413 2290",
					"for_designation": "Site Engineer",
					"referrer": employee,
					"date": ago(12),
					"current_employer": "Gulf Facades",
					"current_job_title": "Site Engineer",
					"qualification_reason": "Ran curtain wall sites for five years; we worked together at Gulf Facades.",
				},
				submit=True,
			)


# ------------------------------------------------------------------ pay


def _pay():
	"""Pay this month beyond the structure: a bonus, a sales incentive, a
	retention bonus, back pay for Huda's raise, and Imran's pay held while his
	visa is renewed. No Payroll Correction: it gives back days taken without
	pay, and nobody in the demo took any."""
	this_month = get_first_day(today())
	component = _component("Bonus", "BON")
	employee = _employee("Tariq")
	if not frappe.db.exists("Additional Salary", {"employee": employee, "salary_component": component}):
		make(
			{
				"doctype": "Additional Salary",
				"employee": employee,
				"company": COMPANY,
				"salary_component": component,
				"amount": 1500,
				"payroll_date": this_month,
				"currency": "AED",
				"overwrite_salary_structure_amount": 1,
			},
			submit=True,
		)
	employee = _employee("Omar")
	if not frappe.db.exists("Employee Incentive", {"employee": employee}):
		make(
			{
				"doctype": "Employee Incentive",
				"employee": employee,
				"company": COMPANY,
				"salary_component": _component("Sales Incentive", "SI"),
				"incentive_amount": 4000,
				"payroll_date": this_month,
				"currency": "AED",
			},
			submit=True,
		)
	employee = _employee("Samir")
	if not frappe.db.exists("Retention Bonus", {"employee": employee}):
		make(
			{
				"doctype": "Retention Bonus",
				"employee": employee,
				"company": COMPANY,
				"salary_component": _component("Retention Bonus", "RB"),
				"bonus_amount": 10000,
				"bonus_payment_date": ahead(60),
				"currency": "AED",
			},
			submit=True,
		)
	employee = _employee("Imran")
	if not frappe.db.exists("Salary Withholding", {"employee": employee}):
		make(
			{
				"doctype": "Salary Withholding",
				"employee": employee,
				"company": COMPANY,
				"posting_date": this_month,
				"from_date": this_month,
				"payroll_frequency": "Monthly",
				"number_of_withholding_cycles": 1,
				"reason_for_withholding_salary": "Held while his visa is renewed",
			},
			submit=True,
		)
	_arrear()


def _component(name, abbr):
	if not frappe.db.exists("Salary Component", name):
		make(
			{
				"doctype": "Salary Component",
				"salary_component": name,
				"salary_component_abbr": abbr,
				"type": "Earning",
			}
		)
	return name


def _arrear():
	"""Huda's raise back to the start of last month, paid as back pay."""
	employee = _employee("Huda")
	if frappe.db.exists("Arrear", {"employee": employee}):
		return
	# Back pay is worked out on the components marked for it.
	for component in ("Basic Salary", "Housing Allowance", "Transport Allowance"):
		frappe.db.set_value("Salary Component", component, "arrear_component", 1)
	raised = get_first_day(add_months(today(), -1))
	if not frappe.db.exists(
		"Salary Structure Assignment", {"employee": employee, "from_date": raised, "docstatus": 1}
	):
		make(
			{
				"doctype": "Salary Structure Assignment",
				"employee": employee,
				"salary_structure": "Sahara Standard",
				"company": COMPANY,
				"currency": "AED",
				"from_date": raised,
				"base": 20000,
				"payroll_payable_account": _payable(),
			},
			submit=True,
		)
	period = frappe.db.get_value("Payroll Period", {"company": COMPANY})
	make(
		{
			"doctype": "Arrear",
			"employee": employee,
			"company": COMPANY,
			"payroll_period": period,
			"payroll_date": get_first_day(today()),
			"arrear_start_date": get_first_day(add_months(today(), -1)),
			"salary_structure": "Sahara Standard",
			"currency": "AED",
		}
	)


# ------------------------------------------------------------------ leaving


def _leaving():
	"""Joseph's exit interview and the statement that settles what he and the
	company still owe each other."""
	employee = _employee(LEAVER)
	if not frappe.db.exists("Exit Interview", {"employee": employee}):
		make(
			{
				"doctype": "Exit Interview",
				"employee": employee,
				"company": COMPANY,
				"date": add_days(frappe.db.get_value("Employee", employee, "relieving_date"), -3),
				"status": "Completed",
				"employee_status": "Exit Confirmed",
				"interviewers": [{"user": HR}],
				"interview_summary": "Leaving to be near family; would come back for a site role in Dubai.",
			}
		)
	if not frappe.db.exists("Full and Final Statement", {"employee": employee}):
		statement = frappe.new_doc("Full and Final Statement")
		joined, left = frappe.db.get_value("Employee", employee, ["date_of_joining", "relieving_date"])
		statement.update(
			{
				"employee": employee,
				"company": COMPANY,
				"date_of_joining": joined,
				"relieving_date": left,
				"transaction_date": left,
			}
		)
		statement.get_outstanding_statements()
		save(statement)


# ------------------------------------------------------------------ OneHR's own


def _clock():
	"""Where the workshop clocks in: its place on the map and its network,
	Yousef's phone, and one attempt of his the clock flagged. Learnt by the
	clock as people use it, so made as the system."""
	with as_user("Administrator"):
		_clocked()


def _clocked():
	# The workshop clocks itself in: the switch HR turns on in HR Settings.
	frappe.db.set_single_value("HR Settings", "one_self_checkin", 1)
	# Two browsers people signed in on, sorted by the administrator
	# (one/devices.py): the front desk everybody uses, and Nadia's laptop, the
	# asset she holds.
	windows = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
	once(
		"Device",
		{"device_name": "Reception Computer"},
		{
			"device_name": "Reception Computer",
			"use": "Shared",
			"user_agent": windows,
			"last_user": HR,
			"last_seen": f"{ago(1)} 08:02:00",
			"token_hash": frappe.generate_hash(length=64),
		},
	)
	nadia = frappe.db.get_value("Employee", _employee("Nadia"), "user_id")
	if nadia:
		once(
			"Device",
			{"device_name": "Nadia's Laptop"},
			{
				"device_name": "Nadia's Laptop",
				"use": "Assigned",
				"user": nadia,
				"asset": frappe.db.get_value("Asset", {"asset_name": "Laptop Nadia"}),
				"user_agent": windows,
				"last_user": nadia,
				"last_seen": f"{ago(0)} 08:47:00",
				"token_hash": frappe.generate_hash(length=64),
			},
		)
	once(
		"Clock Place",
		{"label": "Al Quoz workshop"},
		{
			"label": "Al Quoz workshop",
			"status": "Confirmed",
			"latitude": 25.1379,
			"longitude": 55.2280,
			"radius": 150,
		},
	)
	once(
		"Clock Network",
		{"label": "Workshop Wi-Fi"},
		{"label": "Workshop Wi-Fi", "status": "Confirmed", "address": "94.200.18.0/24"},
	)
	employee = _employee("Yousef")
	once(
		"Clock Device",
		{"employee": employee},
		{
			"employee": employee,
			"label": "Yousef's phone",
			"platform": "Android",
			"model": "Pixel 8",
			"registered_on": f"{ago(40)} 07:58:00",
			# His old phone, reset by HR: a demo cannot hold a real key, and
			# an Active row without one would ask him to sign with nothing.
			"status": "Reset",
		},
	)
	if not frappe.db.exists("Clock Attempt", {"employee": employee}):
		make(
			{
				"doctype": "Clock Attempt",
				"employee": employee,
				"direction": "IN",
				"outcome": "Flagged",
				"score": 45,
				"note": "Clocked in from a network the workshop has never used, 9 km from the site.",
				"platform": "Android",
			}
		)


def _letters():
	"""A salary certificate Rania asked for, for her bank."""
	employee = _employee("Rania")
	if not frappe.db.exists("Employee Letter", {"employee": employee}):
		with as_user(_user("Rania")):
			make(
				{
					"doctype": "Employee Letter",
					"employee": employee,
					"kind": "Salary Certificate",
					"addressed_to": "Emirates NBD",
					"purpose": "Opening a salary account",
					"letter_date": ago(2),
					"body": "<p>This is to certify that Rania Sabbagh has worked for Sahara Glass &amp; Aluminium as a Site Engineer since August 2022.</p>",
				}
			)


# ------------------------------------------------------------------ the rest


def _templates():
	"""What a new workshop hand is taken through, and what is taken back when
	somebody leaves."""
	department = frappe.db.get_value("Department", {"department_name": "Workshop", "company": COMPANY})
	once(
		"Employee Onboarding Template",
		{"title": "Workshop joiner"},
		{
			"title": "Workshop joiner",
			"company": COMPANY,
			"department": department,
			"activities": [
				{
					"activity_name": "Safety induction and PPE issued",
					"user": _user("Tariq"),
					"begin_on": 0,
					"duration": 1,
				},
				{"activity_name": "Visa medical and Emirates ID", "user": HR, "begin_on": 0, "duration": 10},
				{"activity_name": "Bank account for payroll", "user": HR, "begin_on": 2, "duration": 5},
			],
		},
	)
	once(
		"Employee Separation Template",
		{"title": "Leaving the workshop"},
		{
			"title": "Leaving the workshop",
			"company": COMPANY,
			"department": department,
			"activities": [
				{
					"activity_name": "Tools and PPE handed back",
					"user": _user("Tariq"),
					"begin_on": 0,
					"duration": 2,
				},
				{"activity_name": "Visa cancelled", "user": HR, "begin_on": 0, "duration": 14},
				{"activity_name": "End of service paid", "user": ACCOUNTS, "begin_on": 5, "duration": 5},
			],
		},
	)


def _insurance():
	"""Everybody is insured with Daman, and the office's cards are on file."""
	provider = once(
		"Employee Health Insurance", {"health_insurance_name": "Daman"}, {"health_insurance_name": "Daman"}
	)
	for number, first in enumerate(("Layla", "Samir", "Omar", "Huda", "Mariam"), 1):
		employee = _employee(first)
		if not frappe.db.get_value("Employee", employee, "health_insurance_provider"):
			frappe.db.set_value(
				"Employee",
				employee,
				{"health_insurance_provider": provider.name, "health_insurance_no": f"DMN-4471-{number:04d}"},
			)


def _feedback():
	"""A glazier's workshop trial with Tariq, and his feedback on it. Mira's
	interview stays waiting for Samir's, which OneAI drafts."""
	kind = "Workshop Trial"
	if not frappe.db.exists("Interview Type", kind):
		make(
			{
				"doctype": "Interview Type",
				"interview_type_name": kind,
				"designation": "Glazier",
				"expected_skill_set": [{"skill": "Glazing"}, {"skill": "Silicone sealing"}],
				"description": "A morning glazing a unit in the workshop, with the supervisor.",
			}
		)
	applicant = frappe.db.get_value("Job Applicant", {"designation": "Glazier"}) or frappe.db.get_value(
		"Job Applicant", {"email_id": ["!=", "mira.costa@example.com"]}
	)
	if not applicant or frappe.db.exists("Interview", {"interview_type": kind}):
		return
	trial = make(
		{
			"doctype": "Interview",
			"job_applicant": applicant,
			"interview_type": kind,
			"scheduled_on": ago(6),
			"from_time": "08:00:00",
			"to_time": "11:00:00",
			"status": "Pending",
			"interview_details": [{"interviewer": "tariq@one.test"}],
		}
	)
	with as_user("tariq@one.test"):
		make(
			{
				"doctype": "Interview Feedback",
				"interview": trial.name,
				"interviewer": "tariq@one.test",
				"interview_type": kind,
				"job_applicant": applicant,
				"skill_assessment": [
					{"skill": "Glazing", "rating": 0.8},
					{"skill": "Silicone sealing", "rating": 0.6},
				],
				"result": "Cleared",
				"feedback": "Glazed and sealed a casement cleanly in under two hours; needs practice on structural silicone.",
			},
			submit=True,
		)


def _overtime():
	"""Ravi's overtime last month, finishing the Bayview mock-up."""
	employee = _employee("Ravi")
	if frappe.db.exists("Overtime Slip", {"employee": employee}):
		return
	starts = get_first_day(add_months(today(), -1))
	make(
		{
			"doctype": "Overtime Slip",
			"employee": employee,
			"company": COMPANY,
			"posting_date": get_last_day(starts),
			"start_date": starts,
			"end_date": get_last_day(starts),
			"overtime_details": [
				{
					"date": add_days(starts, day),
					"overtime_type": "Workshop Overtime",
					"overtime_duration": 3,
					"standard_working_hours": 8,
				}
				for day in (9, 10, 16)
			],
		}
	)
