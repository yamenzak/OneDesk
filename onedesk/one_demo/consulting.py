"""Bayan Consulting, the group's services firm in DIFC: four consultants who
sell their time. Nexa Telecom's operating model, done between February and
June, and Emirates Retail's pricing review, under way, are billed by the
hour at the end of each month from the timesheets; Jebel Ali Logistics Park
pays a monthly retainer for forty hours of Daniel's advice, and the hours
over it; a one-day strategy workshop is billed on its own."""

import frappe
from frappe.utils import add_days, add_months, get_first_day, get_last_day, getdate

from onedesk.one_demo import firm
from onedesk.one_demo.base import as_user, make, on, save, today
from onedesk.one_demo.firm import Firm, Person

FIRM = Firm(
	name="Bayan Consulting",
	abbr="BYC",
	field="services",
	emirate="Dubai",
	street="Office 2104, Burj Daman, DIFC",
	phone="+971 4 389 6650",
	email="contact@bayanconsulting.test",
	website="bayanconsulting.test",
	tax_id="100845678900003",
	bank="ADCB",
	iban="AE650301290056632100003",
	sales_tax="UAE VAT 5%",
	opening=500000,
	people=(
		Person("Daniel", "Price", "daniel@one.test", "Management", "Managing Partner", "Male", "2018-09-02", 45000, (("one_project", "Manager"), ("one_book", "Manager"), ("one_crm", "Manager"), ("one_hr", "User"))),
		Person("Meera", "Iyer", "meera@one.test", "Operations", "Senior Consultant", "Female", "2020-01-12", 27000, (("one_project", "User"), ("one_task", "User"))),
		Person("Kenji", "Watanabe", None, "Operations", "Consultant", "Male", "2022-04-03", 19000),
		Person("Reem", "Al Hashimi", None, "Research & Development", "Analyst", "Female", "2024-02-18", 12500),
	),
)

PARTNER = "daniel@one.test"
CONSULTANT = "meera@one.test"

ACTIVITIES = (("Advisory", 260, 950), ("Analysis", 140, 550))
"""What an hour of each costs the firm and bills at."""

ITEMS = (
	("BYC-HRS", "Consulting Hours", "Consulting Services", "Hour", None, False),
	("BYC-RET", "Monthly Advisory Retainer", "Consulting Services", "Nos", None, False),
	("BYC-WKS", "Strategy Workshop", "Consulting Services", "Nos", 18000, False),
	("BYC-SAAS", "Software Subscriptions", "Consulting Services", "Nos", 0, False),
	("BYC-SUB", "Subcontracted Field Research", "Consulting Services", "Nos", 0, False),
)

CUSTOMERS = (
	("Nexa Telecom FZ-LLC", "procurement@nexatelecom.example", "+97143360202", ("Stefan", "Ilic")),
	("Jebel Ali Logistics Park", "finance@jalpark.example", "+97148810303", ("Khalfan", "Al Mheiri")),
	("Emirates Retail Group", "strategy@emiratesretail.example", "+97142920404", ("Nadine", "Saleh")),
	("Wadi Health Group", "office@wadihealth.example", "+97143030505", ("Yusuf", "Karam")),
)

SUPPLIERS = (
	("Cloudline Software", "Services", "billing@cloudline.example", ("Ana", "Ribeiro")),
	("Insight Field Research", "Services", "accounts@insightfield.example", ("Karan", "Malhotra")),
)

BILLS = (
	("Cloudline Software", (1, 3), "CLS-2601", "BYC-SAAS", 4200, "Software Expenses", (1, 15)),
	("Cloudline Software", (4, 2), "CLS-2602", "BYC-SAAS", 4200, "Software Expenses", (4, 14)),
	("Insight Field Research", (5, 30), "IFR-118", "BYC-SUB", 22000, "Subcontracted Research", (6, 29)),
	("Cloudline Software", (7, 1), "CLS-2603", "BYC-SAAS", 4350, "Software Expenses", (7, 14)),
	("Cloudline Software", (10, 1), "CLS-2604", "BYC-SAAS", 4350, "Software Expenses", (10, 14)),
	("Insight Field Research", (10, 20), "IFR-131", "BYC-SUB", 16500, "Subcontracted Research", None),
)

NEXA = "Nexa Telecom Operating Model"
RETAIL = "Emirates Retail Pricing Review"
PORT = "Jebel Ali Logistics Park Advisory"

PROJECTS = (
	(NEXA, "Time and Materials", "Nexa Telecom FZ-LLC", (2, 2), (6, 26), {}),
	(PORT, "Retainer", "Jebel Ali Logistics Park", (1, 1), (12, 31), {"monthly_fee": 35000, "monthly_hours": 40}),
	(RETAIL, "Time and Materials", "Emirates Retail Group", (8, 3), (12, 18), {}),
)

TASKS = {
	NEXA: (
		("Current-state interviews", (2, 2), (2, 20), CONSULTANT, "Completed"),
		("Process maps", (2, 23), (3, 27), CONSULTANT, "Completed"),
		("Target operating model", (3, 30), (5, 15), CONSULTANT, "Completed"),
		("Roll-out plan", (5, 18), (6, 26), PARTNER, "Completed"),
	),
	RETAIL: (
		("Data request and cleaning", (8, 3), (8, 28), CONSULTANT, "Completed"),
		("Price elasticity models", (8, 31), (10, 9), CONSULTANT, "Completed"),
		("Store trials", (10, 12), (11, 27), CONSULTANT, "Working"),
		("Board recommendations", (11, 30), (12, 18), PARTNER, "Open"),
	),
}

TIME = {
	NEXA: (("Meera", "Advisory", 6), ("Kenji", "Analysis", 8)),
	RETAIL: (("Kenji", "Analysis", 8), ("Reem", "Analysis", 6)),
	PORT: (("Daniel", "Advisory", 2.5),),
}
"""Who works on each, at what, and the hours of each of their four days a week."""

BILLED = {
	NEXA: (((2, 2), (3, 1), (4, 1), (5, 1), (6, 1), (6, 27)), False),
	RETAIL: (((8, 3), (9, 1), (10, 1), (11, 1)), True),
}
"""When each project's time starts, each day it is invoiced up to, and
whether its work goes on after the last."""

WORKSHOP = ("Wadi Health Group", (9, 18))


def run(password=None):
	bank = firm.settle(FIRM, password)
	for code, name, group, uom, price, stocked in ITEMS:
		firm.item(code, name, group, uom, price, stocked)
	for name, cost, bills in ACTIVITIES:
		if not frappe.db.exists("Activity Type", name):
			make({"doctype": "Activity Type", "activity_type": name, "costing_rate": cost, "billing_rate": bills})
	for name, email, phone, contact in CUSTOMERS:
		firm.customer(name, "Company", email, phone, contact)
	for name, group, email, contact in SUPPLIERS:
		firm.supplier(name, group, email, contact)
	if not frappe.db.exists("Project", {"company": FIRM.name}):
		made = {title: _project(title, kind, client, starts, ends, values) for title, kind, client, starts, ends, values in PROJECTS}
		for title, rows in TASKS.items():
			_tasks(made[title], rows)
		for title, (days, goes_on) in BILLED.items():
			_by_the_hour(made[title], days, goes_on)
		_retained(made[PORT])
		_done(made[NEXA])
		customer, day = WORKSHOP
		firm.sell(FIRM, PARTNER, customer, on(*day), (("BYC-WKS", 1, 18000, "Strategy workshop for the board, one day"),))
		for supplier, day, number, code, amount, spent, paid in BILLS:
			bill = firm.buy(FIRM, PARTNER, supplier, on(*day), number, ((code, 1, amount, spent),))
			if paid:
				firm.settled(FIRM, PARTNER, bill, on(*paid))
	firm.monthly(FIRM, bank, 16000, (1500, 1450, 1550, 1700, 1950, 2300, 2500, 2550, 2250, 1850, 1600))


def _project(title, kind, client, starts, ends, values) -> str:
	"""A project as New Project makes it, Daniel running it with Meera on its team."""
	from onedesk.one_project import kinds
	from onedesk.one_project import team as members

	with as_user(PARTNER):
		name = kinds.make({"title": title, "kind": kind, "client": client, "starts": str(on(*starts)), "ends": str(on(*ends)), "manager": PARTNER, **values})
		if frappe.db.get_value("Project", name, "company") != FIRM.name:
			frappe.db.set_value("Project", name, "company", FIRM.name)
		members.add(name, CONSULTANT)
	return name


def _tasks(project, rows) -> None:
	from frappe.desk.form.assign_to import add

	with as_user(PARTNER):
		for subject, starts, ends, who, status in rows:
			task = make({"doctype": "Task", "subject": subject, "project": project, "exp_start_date": on(*starts), "exp_end_date": on(*ends), "status": "Open"})
			if status == "Completed":
				task.reload()
				task.update({"status": "Completed", "completed_on": on(*ends), "completed_by": who})
				task.save()
				continue
			add({"doctype": "Task", "name": task.name, "assign_to": [who], "notify": 0})
			if status != "Open":
				task.reload()
				task.status = status
				task.save()


def _logged(project, starts, until) -> None:
	"""A timesheet a week for each person on the project, four days of their
	hours, from `starts` to the day before `until` or today."""
	for first, activity, hours in TIME[frappe.db.get_value("Project", project, "project_name")]:
		employee = frappe.db.get_value("Employee", {"company": FIRM.name, "first_name": first})
		user = frappe.db.get_value("Employee", employee, "user_id") or PARTNER
		week, end = getdate(starts), min(getdate(until), today())
		while week < end:
			sheet = frappe.new_doc("Timesheet")
			sheet.update({"employee": employee, "company": FIRM.name, "parent_project": project})
			for day in range(4):
				when = add_days(week, day)
				if when >= end:
					break
				sheet.append("time_logs", {"activity_type": activity, "from_time": f"{when} 09:00:00", "hours": hours, "project": project, "is_billable": 1})
			if sheet.time_logs:
				with as_user(user):
					save(sheet)
				with as_user(PARTNER):
					sheet.reload()
					sheet.submit()
			week = add_days(week, 7)


def _by_the_hour(project, days, goes_on: bool) -> None:
	"""The time to each day invoiced on it, as Invoice Time does, and paid a
	month on."""
	from onedesk.one_demo.projects import _redate
	from onedesk.one_project.billing import invoice_time

	for starts, until in zip(days, days[1:], strict=False):
		_logged(project, on(*starts), on(*until))
		if on(*until) >= today():
			return
		with as_user(PARTNER):
			draft = invoice_time(project, item="BYC-HRS")
			invoice = save(_redate(draft, on(*until)), submit=True)
		firm.settled(FIRM, PARTNER, invoice, add_days(invoice.posting_date, 30))
	if goes_on:
		_logged(project, on(*days[-1]), today())


def _retained(project) -> None:
	"""Each month's retainer, with the hours over it, invoiced on its last
	day as Invoice Month does, and paid twenty-five days on."""
	from onedesk.one_demo.projects import _redate
	from onedesk.one_project.retainer import invoice_month

	for month in range(1, today().month):
		first = get_first_day(on(month, 1))
		_logged(project, first, add_months(first, 1))
		with as_user(PARTNER):
			draft = invoice_month(project, month=str(first), item="BYC-RET", overage=1)
			invoice = save(_redate(draft, get_last_day(first)), submit=True)
		firm.settled(FIRM, PARTNER, invoice, add_days(invoice.posting_date, 25))
	_logged(project, get_first_day(today()), today())


def _done(project) -> None:
	with as_user(PARTNER):
		doc = frappe.get_doc("Project", project)
		doc.status = "Completed"
		doc.save()
