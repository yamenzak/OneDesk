"""OneProject, every way a project runs: fixed price, time and materials,
retainer and internal.
"""

import frappe
from frappe.utils import add_days, add_months, date_diff, flt, get_first_day, getdate

from onedesk.one_demo.base import COMPANY, account, ago, ahead, as_user, dated, make, on, save, tag, today, wh

PM = "samir@one.test"
OWNER = "wsadmin@one.test"
ACCOUNTS_USER = "huda@one.test"
TEMPLATE = "Aluminium & Glazing"

#: The Aluminium & Glazing template: five phases of the work, each ending in a
#: milestone, as a facade contractor runs a job. phase, [(task, begins on
#: day, lasts days)]
PHASES = (
	("Initiation, Engineering & Approvals", (
		("Contract review and kick-off", 0, 3),
		("Site survey and measurements", 3, 5),
		("Shop drawings and structural calculations", 8, 15),
		("Drawings and samples approved by the consultant", 23, 7),
	)),
	("Procurement & Material Management", (
		("Order aluminium profiles", 30, 3),
		("Order glass", 30, 3),
		("Order hardware and accessories", 33, 3),
		("Receive and inspect materials", 45, 10),
		("Approve the site mock-up", 50, 5),
	)),
	("Factory Fabrication & Assembly", (
		("Cut and machine profiles", 55, 12),
		("Assemble frames", 62, 14),
		("Glaze and seal units", 70, 12),
		("Factory quality inspection", 80, 4),
		("Pack and prepare dispatch", 84, 3),
	)),
	("Site Installation & Logistics", (
		("Deliver to site", 87, 2),
		("Fix subframes and anchors", 89, 7),
		("Install frames", 94, 14),
		("Install glass", 104, 12),
		("Fit and adjust hardware", 114, 6),
		("Seal and weatherproof", 118, 6),
	)),
	("Testing, Handover & Closeout", (
		("Water test", 124, 3),
		("Snag list and rectification", 127, 7),
		("Final clean", 134, 2),
		("Handover with O&M manuals", 136, 2),
		("Final account and retention release", 138, 10),
	)),
)


def run(password=None):
	_accounts()
	_template()
	with as_user(PM):
		villa()
		tower()
		acme()
		balcony()
		partitions()
		showroom()
		survey()
		marina()
		facade_care()
		workshop()


# The projects


def villa():
	name = _project(
		"Mansour Villa Windows and Doors",
		kind="Fixed Price",
		client="Mansour & Sons",
		starts=on(2, 15),
		ends=ahead(55),
		template=TEMPLATE,
		team=("rania@one.test", "tariq@one.test", "yousef@one.test", "nadia@one.test"),
		notes="A four-bedroom villa in Al Barsha: casement windows, sliding doors and glass balustrades, handed over in December.",
	)
	if not name:
		return
	order = _contract(
		name,
		on(2, 12),
		[("WIN-CS12", 60, 2400), ("DR-SL24", 20, 6800), ("BAL-GL", 60, 1450), ("SVC-INST", 120, 180)],
		retention=10,
		retention_due=ahead(120),
		handover=50,
	)
	_budget(name, {"Materials": 140000, "Subcontracts": 60000, "Labour": 40000})
	_progress(name, done_through=3, half_way=4)
	_milestone_shares(name, (10, 20, 30, 30, 10))
	first = _bill_progress(order, on(4, 30), done=20)
	_pay(first, on(5, 20))
	second = _bill_progress(order, on(7, 31), lines={0: 70, 1: 40, 2: 30, 3: 20})
	_pay(second, on(8, 25), part=0.6)
	_bill_progress(order, ago(40), lines={0: 90, 1: 60, 2: 50, 3: 35})
	sub = _subcontract(name, "Precision Installers", 58000, on(6, 1), retention=5)
	bill = _bill_progress(sub, on(8, 15), done=40, doctype="Purchase Order")
	_pay(bill, on(9, 5))
	_issue(name, on(5, 18), (("ALU-6063", 420), ("GLS-DGU", 95), ("HW-HINGE", 120), ("HW-HANDLE", 60), ("SEAL-EPDM", 600)))
	_issue(name, on(8, 4), (("ALU-6063", 380), ("GLS-DGU", 88), ("HW-LOCK", 18), ("SIL-CLR", 40)))
	_time(name, ("Arun", "Ravi", "Joseph"), "Fabrication", on(5, 20), weeks=10, hours=28)
	_time(name, ("Yousef", "Bilal"), "Installation", on(8, 10), weeks=7, hours=32)
	_time(name, ("Rania",), "Project Management", on(2, 20), weeks=30, hours=6)
	_extra_work(name, "Mansour & Sons", "Staircase balustrade", [("BAL-GL", 14, 1500), ("SVC-INST", 20, 180)], ago(30))
	_update(name, "Frames for the ground floor are in. Glass for the first floor lands on Thursday.", ago(9))
	_update(name, "Balustrade drawings approved by Khalid. Starting the staircase next week.", ago(3))
	frappe.db.set_value("Project", name, "one_health", "At Risk")


def tower():
	name = _project(
		"Bayview Tower Curtain Wall",
		kind="Fixed Price",
		client="Bayview Developments",
		starts=on(3, 1),
		ends=add_days(today(), 170),
		team=("rania@one.test", "tariq@one.test", "karim@one.test"),
		notes="Unitised curtain wall for a 24-storey residential tower in Business Bay, podium first.",
	)
	if not name:
		return
	order = _contract(name, on(2, 25), [("BAL-GL", 400, 1450), ("WIN-CS12", 300, 2400), ("SVC-INST", 1800, 180)], retention=5, retention_due=ahead(300), handover=50)
	_advance("Bayview Developments", order, 180000, on(3, 10))
	_budget(name, {"Materials": 900000, "Subcontracts": 300000, "Labour": 180000, "Equipment": 60000})
	for part, starts, ends in (("Podium", on(3, 15), ahead(20)), ("Levels 1 to 10", on(6, 1), ahead(110))):
		sub = _project(f"Bayview Tower {part}", kind="Fixed Price", client="Bayview Developments", starts=starts, ends=ends, parent=name)
		_tasks(sub, (
			("Shop drawings", 0, 15, "nadia@one.test", "Completed"),
			("Brackets and embeds", 15, 20, "rania@one.test", "Completed" if part == "Podium" else "Working"),
			("Unit installation", 35, 60, "tariq@one.test", "Working" if part == "Podium" else "Open"),
			("Perimeter sealing", 95, 25, "rania@one.test", "Open"),
		), starts)
	scaffold = _subcontract(name, "Rapid Scaffolding", 66000, on(4, 1))
	_bill_progress(scaffold, on(7, 1), done=50, doctype="Purchase Order")
	_bill_progress(order, on(5, 31), done=8)
	late = _bill_progress(order, ago(75), done=15)
	frappe.db.set_value("Project", name, "one_health", "On Track")
	return late


def acme():
	if frappe.db.exists("Project", {"project_name": "Acme New York Lobby"}):
		return
	name = _project(
		"Acme New York Lobby",
		kind="Fixed Price",
		client="Acme Holdings",
		starts=ahead(20),
		ends=ahead(140),
		notes="Glass entrance and lobby screens for Acme's Manhattan office. Quoted, waiting on their board.",
	)
	quote = frappe.new_doc("Quotation")
	quote.update({"quotation_to": "Customer", "party_name": "Acme Holdings", "currency": "USD", "project": name, "valid_till": ahead(25)})
	dated(quote, ago(6), "transaction_date")
	quote.append("items", {"item_code": "DR-SL24", "qty": 6, "rate": 2100})
	quote.append("items", {"item_code": "BAL-GL", "qty": 30, "rate": 420})
	quote.append("items", {"item_code": "SVC-INST", "qty": 90, "rate": 55})
	save(quote, submit=True)


def balcony():
	name = _project(
		"Rahman Balcony Enclosure",
		kind="Fixed Price",
		client="Aisha Rahman",
		starts=on(3, 2),
		ends=on(5, 30),
		team=("yousef@one.test",),
		notes="Frameless sliding enclosure for a 9 m balcony in Jumeirah Lake Towers.",
	)
	if not name:
		return
	order = _contract(name, on(2, 26), [("DR-SL24", 4, 6800), ("SVC-INST", 40, 180), ("SVC-SURV", 1, 7600)])
	_tasks(name, (
		("Measure the balcony", 0, 2, "rania@one.test", "Completed"),
		("Fabricate the sliding panels", 10, 20, "tariq@one.test", "Completed"),
		("Install and seal", 35, 6, "yousef@one.test", "Completed"),
		("Handover", 45, 1, "samir@one.test", "Completed"),
	), on(3, 2))
	invoice = _bill_progress(order, on(5, 31), done=100)
	_pay(invoice, on(6, 12))
	from onedesk.one_project.status import change

	change(name, "Completed")


def partitions():
	name = _project(
		"Palm Interiors Office Partitions",
		kind="Fixed Price",
		client="Palm Interiors",
		starts=on(7, 1),
		ends=on(9, 30),
		notes="Glass partitions for a co-working floor. The client moved to another building.",
	)
	if not name:
		return
	_tasks(name, (("Site survey", 0, 2, "rania@one.test", "Completed"), ("Partition layout", 3, 10, "nadia@one.test", "Cancelled")), on(7, 1))
	from onedesk.one_project.status import change

	change(name, "Cancelled", close=1)


def showroom():
	name = _project(
		"Nordlicht Showroom Design",
		kind="Time and Materials",
		client="Nordlicht GmbH",
		starts=on(4, 1),
		ends=ahead(45),
		markup=12,
		budget=90000,
		team=("nadia@one.test",),
		notes="Design and supervision of a glass-heavy showroom fit-out in Berlin, billed by the hour.",
	)
	if not name:
		return
	_tasks(name, (
		("Concept options", 0, 14, "nadia@one.test", "Completed"),
		("Design development", 14, 30, "nadia@one.test", "Completed"),
		("Technical drawings", 44, 40, "nadia@one.test", "Working"),
		("Site supervision visits", 84, 60, "samir@one.test", "Open"),
	), on(4, 1))
	_time(name, ("Nadia",), "Design", on(4, 2), weeks=14, hours=22)
	_time(name, ("Samir",), "Site Survey", on(5, 4), weeks=3, hours=8)
	from onedesk.one_project.billing import invoice_time

	with as_user(ACCOUNTS_USER):
		draft = invoice_time(name, item="SVC-DES")
		dated(draft, on(7, 15))
		save(draft, submit=True)
	_pay(frappe.get_doc("Sales Invoice", draft.name), on(8, 2))
	_time(name, ("Nadia",), "Design", on(7, 20), weeks=10, hours=18)
	_buy_for(name, "Euro Hardware Trading", (("HW-HANDLE", 40, 21), ("HW-LOCK", 12, 88)), on(6, 10), currency="EUR")


def survey():
	name = _project(
		"Crescent Schools Window Survey",
		kind="Time and Materials",
		client="Crescent Schools",
		starts=ago(12),
		ends=ahead(10),
		team=("rania@one.test",),
	)
	if not name:
		return
	_tasks(name, (("Survey the east wing", 0, 3, "rania@one.test", "Completed"), ("Survey the west wing", 5, 3, "rania@one.test", "Working"), ("Write the condition report", 9, 5, "rania@one.test", "Open")), ago(12))
	_time(name, ("Rania",), "Site Survey", ago(11), weeks=2, hours=9)


def marina():
	name = _project(
		"Marina Hotels Glazing Care",
		kind="Retainer",
		client="Marina Hotels Group",
		starts=on(1, 1),
		ends=add_days(on(1, 1), 729),
		monthly_fee=12000,
		monthly_hours=40,
		team=("yousef@one.test", "tariq@one.test"),
		notes="Glazing inspection and repairs across three hotels, a visit a week and call-outs within 24 hours.",
	)
	if not name:
		return
	_retainer(name, 1, months=today().month - 1, people=("Yousef", "Bilal"), hours=(9, 10, 11, 9, 12, 10, 14, 13, 9), over=(7,))


def facade_care():
	name = _project(
		"Gulf Properties Facade Care",
		kind="Retainer",
		client="Gulf Properties REIT",
		starts=on(6, 1),
		ends=add_days(on(6, 1), 364),
		monthly_fee=8500,
		monthly_hours=24,
		team=("yousef@one.test",),
	)
	if not name:
		return
	_retainer(name, 6, months=today().month - 6, people=("Imran",), hours=(5, 6, 6, 7))


def workshop():
	name = _project(
		"Workshop CNC Upgrade",
		kind="Internal",
		starts=on(5, 1),
		ends=ahead(25),
		budget=600000,
		team=("tariq@one.test", "karim@one.test"),
		notes="A five-axis profile machining centre for the workshop, and the floor and power it needs.",
	)
	if not name:
		return
	_tasks(name, (
		("Choose the machine", 0, 20, "tariq@one.test", "Completed"),
		("Prepare the floor and power", 25, 30, "karim@one.test", "Completed"),
		("Install and commission", 60, 25, "tariq@one.test", "Working"),
		("Train the fabricators", 90, 10, "tariq@one.test", "Open"),
	), on(5, 1))
	_time(name, ("Tariq",), "Project Management", on(5, 4), weeks=12, hours=4)


# How each is made


def _project(title, kind, starts, ends, client=None, template=None, team=(), notes=None, parent=None, **values):
	if frappe.db.exists("Project", {"project_name": title}):
		return None
	from onedesk.one_project import kinds, team as members

	name = kinds.make(
		{
			"title": title,
			"kind": kind,
			"client": client,
			"starts": str(starts),
			"ends": str(ends),
			"manager": PM,
			"template": template,
			"parent": parent,
			**values,
		}
	)
	tag(frappe.get_doc("Project", name))
	if notes:
		frappe.db.set_value("Project", name, "notes", notes)
	for user in team:
		members.add(name, user)
	return name


def _contract(project, date, lines, retention=0, retention_due=None, handover=0):
	"""The customer's order for the work, made on the day it was signed and
	named the project's contract, as Add Contract does."""
	from onedesk.one_book.currency import bill_in

	doc = frappe.get_doc("Project", project)
	order = frappe.new_doc("Sales Order")
	order.company = COMPANY
	bill_in(order, "Customer", doc.customer)
	order.update(
		{
			"customer": doc.customer,
			"project": project,
			"delivery_date": doc.expected_end_date,
			"one_retention": retention,
			"one_retention_due": retention_due if retention else None,
			"one_retention_handover": handover if retention else 0,
		}
	)
	dated(order, date, "transaction_date")
	for code, qty, rate in lines:
		order.append("items", {"item_code": code, "qty": qty, "rate": rate, "delivery_date": doc.expected_end_date, "project": project})
	save(order, submit=True)
	doc.db_set("sales_order", order.name)
	return order.name


def _bill_progress(order, date, done=None, lines=None, doctype="Sales Order"):
	"""Bill Progress, as the project page asks for it, by whoever keeps the
	books."""
	with as_user(ACCOUNTS_USER):
		return _billed(order, date, done, lines, doctype)


def _billed(order, date, done, lines, doctype):
	from onedesk.one_project.progress import bill_progress

	if lines is not None:
		rows = frappe.get_all(f"{doctype} Item", filters={"parent": order}, fields=["name"], order_by="idx")
		lines = {rows[i].name: share for i, share in lines.items()}
	invoice = bill_progress(order, doctype=doctype, done=done, lines=lines)
	dated(invoice, date)
	if invoice.doctype == "Purchase Invoice":
		invoice.bill_no = f"INV-{order[-5:]}-{date.month}"
		invoice.bill_date = date
	for row in invoice.get("payment_schedule") or []:
		row.due_date = max(getdate(row.due_date), getdate(date))
	invoice.due_date = add_days(date, 30)
	return save(invoice, submit=True)


def _pay(invoice, date, part=1.0):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	with as_user(ACCOUNTS_USER):
		payment = get_payment_entry(invoice.doctype, invoice.name)
		dated(payment, date)
		payment.reference_no = f"TRF-{invoice.name[-6:]}"
		payment.reference_date = date
		if part < 1:
			amount = flt(payment.paid_amount * part, 2)
			payment.paid_amount = amount
			payment.received_amount = flt(amount * flt(payment.source_exchange_rate or 1) / flt(payment.target_exchange_rate or 1), 2)
			for ref in payment.references:
				ref.allocated_amount = min(ref.allocated_amount, amount)
		save(payment, submit=True)


def _advance(customer, order, amount, date):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	with as_user(ACCOUNTS_USER):
		payment = get_payment_entry("Sales Order", order, party_amount=amount)
		dated(payment, date)
		payment.reference_no = f"ADV-{order[-5:]}"
		payment.reference_date = date
		save(payment, submit=True)


def _subcontract(project, supplier, amount, date, retention=0):
	order = frappe.new_doc("Purchase Order")
	order.update(
		{
			"supplier": supplier,
			"company": COMPANY,
			"project": project,
			"schedule_date": add_days(date, 60),
			"one_retention": retention,
			"one_retention_due": ahead(150) if retention else None,
		}
	)
	dated(order, date, "transaction_date")
	order.append("items", {"item_code": "SVC-SUB", "qty": 1, "rate": amount, "schedule_date": add_days(date, 60), "project": project})
	return save(order, submit=True).name


def _buy_for(project, supplier, lines, date, currency=None):
	order = frappe.new_doc("Purchase Order")
	order.update({"supplier": supplier, "company": COMPANY, "project": project, "schedule_date": add_days(date, 14)})
	if currency:
		order.currency = currency
	dated(order, date, "transaction_date")
	for code, qty, rate in lines:
		order.append("items", {"item_code": code, "qty": qty, "rate": rate, "schedule_date": add_days(date, 14), "project": project, "warehouse": wh("Stores")})
	save(order, submit=True)
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_invoice

	# The supplier's bill is the books' to enter.
	with as_user(ACCOUNTS_USER):
		bill = make_purchase_invoice(order.name)
		dated(bill, add_days(date, 12))
		bill.bill_no = f"EH-{order.name[-5:]}"
		bill.update_stock = 1
		return save(bill, submit=True)


def _issue(project, date, lines):
	entry = frappe.new_doc("Stock Entry")
	entry.stock_entry_type = "Material Issue"
	entry.purpose = "Material Issue"
	entry.company = COMPANY
	entry.project = project
	dated(entry, date)
	for code, qty in lines:
		entry.append("items", {"item_code": code, "qty": qty, "s_warehouse": wh("Stores"), "project": project})
	save(entry, submit=True)


def _budget(project, lines):
	from onedesk.one_project.budget import set_budget

	for kind, amount in lines.items():
		set_budget(project, account(COST_TYPES[kind]), amount, "Warn")


def _tasks(project, rows, starts):
	"""(subject, starts after days, lasts days, assigned to, status)"""
	made = []
	for subject, begin, lasts, who, status in rows:
		begins = add_days(starts, begin)
		values = {
			"doctype": "Task",
			"subject": subject,
			"project": project,
			"exp_start_date": begins,
			"exp_end_date": add_days(begins, lasts),
			"status": "Open" if status in ("Completed", "Cancelled") else status,
		}
		task = make(values)
		_assign(task.name, who)
		_finish(task.name, status, add_days(begins, lasts))
		made.append(task.name)
	return made


def _progress(project, done_through, half_way):
	"""The template's phases: those before `done_through` done, the one at
	`half_way` half done, the rest still to come."""
	people = ("rania@one.test", "nadia@one.test", "karim@one.test", "tariq@one.test", "yousef@one.test")
	for i, (phase, tasks) in enumerate(PHASES, 1):
		for j, (subject, *_rest) in enumerate(tasks):
			task = frappe.db.get_value("Task", {"project": project, "subject": subject}, ["name", "exp_end_date"], as_dict=True)
			if not task:
				continue
			_assign(task.name, people[(i + j) % len(people)])
			if i < done_through or (i == done_through and j < len(tasks)) and i <= done_through:
				_finish(task.name, "Completed", task.exp_end_date)
			elif i == half_way and j < len(tasks) // 2:
				_finish(task.name, "Completed", task.exp_end_date)
			elif i == half_way:
				_finish(task.name, "Working", None)
		milestone = frappe.db.get_value("Task", {"project": project, "subject": phase})
		if milestone and i <= done_through:
			_finish(milestone, "Completed", None)


def _milestone_shares(project, shares):
	for (phase, _tasks), share in zip(PHASES, shares, strict=True):
		milestone = frappe.db.get_value("Task", {"project": project, "subject": phase})
		if milestone:
			doc = frappe.get_doc("Task", milestone)
			doc.is_milestone = 1
			doc.one_bill_share = share
			doc.save()


def _assign(task, user):
	from frappe.desk.form.assign_to import add

	if user and not frappe.db.exists("ToDo", {"reference_type": "Task", "reference_name": task, "allocated_to": user, "status": "Open"}):
		add({"doctype": "Task", "name": task, "assign_to": [user], "notify": 0})


def _finish(task, status, on_day):
	if status in ("Open", None):
		return
	doc = frappe.get_doc("Task", task)
	if doc.status == status:
		return
	if status == "Completed":
		for row in doc.depends_on:
			_finish(row.task, "Completed", on_day)
		doc.reload()
		doc.completed_on = min(getdate(on_day or today()), today())
		doc.completed_by = PM
	doc.status = status
	doc.save()


def _time(project, people, activity, starts, weeks, hours):
	"""A timesheet a week for each person, on the project's open tasks."""
	from onedesk.one_project.hours import bills_hours

	tasks = frappe.get_all(
		"Task",
		filters={"project": project, "is_group": 0},
		fields=["name", "status", "exp_start_date", "exp_end_date"],
		order_by="exp_start_date asc",
	)
	billable = 1 if bills_hours(project) else 0
	for first in people:
		employee = frappe.db.get_value("Employee", {"first_name": first})
		for week in range(weeks):
			begins = add_days(starts, week * 7)
			if begins >= today():
				break
			sheet = frappe.new_doc("Timesheet")
			sheet.employee = employee
			sheet.company = COMPANY
			sheet.parent_project = project
			for day in range(min(5, max(1, round(hours / 6)))):
				when = add_days(begins, day)
				if when >= today():
					break
				sheet.append(
					"time_logs",
					{
						"activity_type": activity,
						"from_time": _free(employee, when),
						"hours": round(hours / 5, 1),
						"project": project,
						"is_billable": billable,
						**_on(tasks, when),
					},
				)
			if sheet.time_logs:
				# Each logs their own time, and the project manager logs the
				# workshop's, who have no account, and approves it all.
				with as_user(frappe.db.get_value("Employee", employee, "user_id") or PM):
					save(sheet)
				with as_user(PM):
					sheet.reload()
					sheet.submit()


def _on(tasks, day):
	"""The task a day's time goes on: the one scheduled that day. A log on a
	task already done is marked completed, since ERPNext sets a task with
	time logged on it back to Working otherwise."""
	day = getdate(day)
	found = next((t for t in tasks if t.exp_start_date and getdate(t.exp_start_date) <= day <= getdate(t.exp_end_date or day)), None)
	if not found:
		return {}
	return {"task": found.name, "completed": int(found.status == "Completed")}


def _free(employee, day):
	"""When the person's day is free from: eight, or after what they have
	logged that day on another project."""
	last = frappe.db.sql(
		"""select max(log.to_time) from `tabTimesheet Detail` log
		join `tabTimesheet` sheet on sheet.name = log.parent
		where sheet.employee = %s and sheet.docstatus < 2 and date(log.from_time) = %s""",
		(employee, day),
	)[0][0]
	return str(last) if last else f"{day} 08:00:00"


def _extra_work(parent, customer, title, lines, date):
	"""Extra work the customer asks for: a quotation marked as extra work,
	ordered, which makes it a sub-project (billing.ordered)."""
	from erpnext.selling.doctype.quotation.mapper import make_sales_order

	quote = frappe.new_doc("Quotation")
	quote.update({"quotation_to": "Customer", "party_name": customer, "project": parent, "one_extra_work": 1, "title": title})
	dated(quote, date, "transaction_date")
	quote.valid_till = add_days(date, 30)
	for code, qty, rate in lines:
		quote.append("items", {"item_code": code, "qty": qty, "rate": rate})
	save(quote, submit=True)
	order = make_sales_order(quote.name)
	dated(order, add_days(date, 6), "transaction_date")
	order.delivery_date = ahead(40)
	for row in order.items:
		row.delivery_date = order.delivery_date
	save(order, submit=True)


def _retainer(project, first_month, months, people, hours, over=()):
	from onedesk.one_project.retainer import invoice_month

	for i in range(months):
		month = get_first_day(add_months(on(first_month, 1), i))
		_time(project, people, "Maintenance", add_days(month, 2), weeks=4, hours=hours[i % len(hours)] + (20 if i + first_month in over else 0))
		with as_user(ACCOUNTS_USER):
			draft = invoice_month(project, month=str(month), item="SVC-MAINT", overage=1)
			dated(draft, add_days(add_months(month, 1), -1))
			invoice = save(draft, submit=True)
		if date_diff(today(), invoice.posting_date) > 40:
			_pay(invoice, add_days(invoice.posting_date, 21))


def _update(project, note, date):
	from onedesk.one_project.updates import post

	post(project, note)


#: The expense accounts a project's cost types are, by what they are called.
COST_TYPES = {"Materials": "Cost of Goods Sold", "Subcontracts": "Subcontract Costs", "Labour": "Site Labour", "Equipment": "Equipment Hire"}


def _accounts():
	parent = frappe.db.get_value("Account", {"company": COMPANY, "account_name": "Direct Expenses", "is_group": 1})
	for name in ("Subcontract Costs", "Site Labour", "Equipment Hire"):
		if not frappe.db.exists("Account", account(name)):
			make({"doctype": "Account", "account_name": name, "parent_account": parent, "company": COMPANY, "account_type": "Expense Account"})


def _template():
	"""The Aluminium & Glazing template, as Save as Template keeps one: a
	template task for each phase, its tasks under it, each waiting on the one
	before when that one ends first, and a milestone ending each phase."""
	if frappe.db.exists("Project Template", TEMPLATE):
		return
	rows = []
	previous, ended = None, 0
	for phase, tasks in PHASES:
		begins = tasks[0][1]
		ends = max(start + lasts for _subject, start, lasts in tasks)
		group = make({"doctype": "Task", "subject": phase, "is_template": 1, "is_group": 1, "is_milestone": 1, "start": begins, "duration": ends - begins})
		rows.append({"task": group.name, "subject": phase})
		for subject, start, lasts in tasks:
			task = make(
				{
					"doctype": "Task",
					"subject": subject,
					"is_template": 1,
					"start": start,
					"duration": lasts,
					"parent_task": group.name,
					"depends_on": [{"task": previous}] if previous and ended <= start else [],
				}
			)
			rows.append({"task": task.name, "subject": subject})
			previous, ended = task.name, start + lasts
	template = frappe.new_doc("Project Template")
	template.project_type = None
	for row in rows:
		template.append("tasks", row)
	template.insert(set_name=TEMPLATE)
	tag(template)
