"""Sahara Glass Saudi, the sister company in Riyadh, in riyals: its own
stores, stock, buying and selling, pipeline and books, Samir's installation
project and Ahmed, its site supervisor, on the Saudi weekend. Its chart is
the one ERPNext builds when nobody names one (docs/ACCOUNTS.md); the riyal
and the dirham are both pegged to the dollar, so their rate holds."""

import frappe
from frappe.utils import add_days, getdate, today

from onedesk.one_book.currency import bill_in
from onedesk.one_demo.base import ago, as_user, dated, make, on, once, save, tag

BRANCH = "Sahara Glass Saudi"
ABBR = "SGS"
CURRENCY = "SAR"
OWNER = "wsadmin@one.test"
STORES = "karim@one.test"
SALES = "omar@one.test"

RATES = (("SAR", "AED", 0.9793), ("AED", "SAR", 1.0211))

OPENING = (("ALU-6063", 400, 26.5), ("GLS-DGU", 80, 155), ("HW-HINGE", 150, 35), ("SIL-CLR", 60, 29), ("WIN-CS12", 30, 640))


def wh(name: str) -> str:
	return f"{name} - {ABBR}"


def run(password=None):
	_company()
	_rates()
	_years()
	_opening()
	supplier, customer = _parties()
	_bought(supplier)
	_sold(customer)
	_pipeline(customer)
	_books()
	_job(customer)
	_people()


def _company():
	if frappe.db.exists("Company", BRANCH):
		return
	with as_user(OWNER):
		tag(
			frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": BRANCH,
					"abbr": ABBR,
					"default_currency": CURRENCY,
					"country": "Saudi Arabia",
					"phone_no": "+966 11 465 3380",
					"email": "riyadh@saharaglass.test",
					"website": "saharaglass.test",
				}
			).insert()
		)


def _rates():
	frappe.db.set_value("Currency", CURRENCY, "enabled", 1)
	for source, target, rate in RATES:
		if not frappe.db.exists("Currency Exchange", {"from_currency": source, "to_currency": target}):
			make(
				{
					"doctype": "Currency Exchange",
					"date": on(1, 1),
					"from_currency": source,
					"to_currency": target,
					"exchange_rate": rate,
					"for_buying": 1,
					"for_selling": 1,
				}
			)


def _years():
	"""A fiscal year that names its companies names this one too."""
	for name in frappe.get_all("Fiscal Year", pluck="name"):
		year = frappe.get_doc("Fiscal Year", name)
		if year.get("companies") and BRANCH not in {row.company for row in year.companies}:
			year.append("companies", {"company": BRANCH})
			year.save()


def _opening():
	if frappe.db.exists("Stock Reconciliation", {"company": BRANCH, "purpose": "Opening Stock", "docstatus": 1}):
		return
	with as_user(STORES):
		doc = frappe.new_doc("Stock Reconciliation")
		doc.purpose = "Opening Stock"
		doc.company = BRANCH
		doc.set_warehouse = wh("Stores")
		dated(doc, on(1, 1))
		doc.posting_time = "08:00:00"
		doc.expense_account = frappe.db.get_value("Account", {"company": BRANCH, "account_name": "Temporary Opening"})
		for code, qty, rate in OPENING:
			doc.append("items", {"item_code": code, "warehouse": wh("Stores"), "qty": qty, "valuation_rate": rate})
		save(doc, submit=True)


def _parties():
	supplier = once(
		"Supplier",
		{"supplier_name": "Riyadh Aluminium Extrusions"},
		{"supplier_name": "Riyadh Aluminium Extrusions", "supplier_group": _group("Supplier Group"), "supplier_type": "Company", "country": "Saudi Arabia", "default_currency": CURRENCY},
	).name
	customer = once(
		"Customer",
		{"customer_name": "Al Olaya Towers"},
		{"customer_name": "Al Olaya Towers", "customer_group": _group("Customer Group"), "customer_type": "Company", "territory": _territory(), "default_currency": CURRENCY},
	).name
	return supplier, customer


def _group(doctype: str) -> str:
	return frappe.db.get_value(doctype, {"is_group": 0}, "name", order_by="creation asc")


def _territory() -> str:
	return frappe.db.get_value("Territory", "Saudi Arabia") or frappe.db.get_value("Territory", {"is_group": 0}, "name", order_by="creation asc")


def _bought(supplier: str):
	"""Karim orders profile for Riyadh, and half of it has come."""
	from erpnext.buying.doctype.purchase_order.mapper import make_purchase_receipt

	if frappe.db.exists("Purchase Order", {"company": BRANCH, "docstatus": 1}):
		return
	with as_user(STORES):
		order = frappe.new_doc("Purchase Order")
		order.supplier = supplier
		order.company = BRANCH
		dated(order, ago(24), "transaction_date")
		bill_in(order, "Supplier", supplier)
		order.schedule_date = add_days(order.transaction_date, 14)
		order.append("items", {"item_code": "ALU-6063", "qty": 100, "uom": "Bar", "rate": 155, "schedule_date": order.schedule_date, "warehouse": wh("Stores")})
		order.append("items", {"item_code": "SEAL-EPDM", "qty": 800, "rate": 4.1, "schedule_date": order.schedule_date, "warehouse": wh("Stores")})
		order = save(order, submit=True)
		receipt = make_purchase_receipt(order.name)
		dated(receipt, ago(12))
		receipt.supplier_delivery_note = "RAE-DN-3307"
		for row in receipt.items:
			row.qty = row.received_qty = row.qty / 2
		save(receipt, submit=True)


def _sold(customer: str):
	"""Omar sells casement windows to a tower in Riyadh, and they go out from
	the Riyadh stores."""
	from erpnext.selling.doctype.sales_order.mapper import make_delivery_note

	if frappe.db.exists("Sales Order", {"company": BRANCH, "docstatus": 1}):
		return
	with as_user(SALES):
		order = frappe.new_doc("Sales Order")
		order.customer = customer
		order.company = BRANCH
		dated(order, ago(18), "transaction_date")
		bill_in(order, "Customer", customer)
		order.delivery_date = add_days(order.transaction_date, 10)
		order.set_warehouse = wh("Stores")
		order.append("items", {"item_code": "WIN-CS12", "qty": 12, "rate": 1150, "delivery_date": order.delivery_date, "warehouse": wh("Stores")})
		order = save(order, submit=True)
	with as_user(STORES):
		note = make_delivery_note(order.name)
		dated(note, ago(9))
		save(note, submit=True)


def _pipeline(customer: str):
	"""Omar's Riyadh pipeline: a lead met at an exhibition, and the tower's
	next phase at Proposal with its quotation in riyals."""
	from erpnext.crm.doctype.opportunity.mapper import make_quotation

	from onedesk.one_demo.crm import _stages_to

	with as_user(SALES):
		if not frappe.db.exists("UTM Source", "Exhibition"):
			tag(frappe.get_doc({"doctype": "UTM Source"}).insert(set_name="Exhibition"))
		once(
			"Lead",
			{"email_id": "faisal@diriyahdev.example"},
			{
				"first_name": "Faisal",
				"last_name": "Al Harbi",
				"company_name": "Diriyah Developments",
				"email_id": "faisal@diriyahdev.example",
				"company": BRANCH,
				"territory": _territory(),
				"utm_source": "Exhibition",
				"lead_owner": SALES,
			},
		)
		title = "Al Olaya Towers Phase 2"
		if frappe.db.exists("Opportunity", {"title": title}):
			return
		deal = make(
			{
				"doctype": "Opportunity",
				"title": title,
				"company": BRANCH,
				"opportunity_from": "Customer",
				"party_name": customer,
				"opportunity_owner": SALES,
				"sales_stage": "New",
				"currency": CURRENCY,
				"opportunity_amount": 69000,
				"expected_closing": add_days(ago(0), 30),
			}
		)
		for passed in _stages_to("Proposal"):
			deal.reload()
			deal.sales_stage = passed
			deal.save()
		quote = make_quotation(deal.name)
		quote.append("items", {"item_code": "WIN-CS12", "qty": 60, "rate": 1150})
		quote.valid_till = add_days(ago(0), 20)
		save(quote, submit=True)


def _books():
	"""Huda invoices the windows that went out, takes half of it into the
	Riyadh cash account, books Riyadh Aluminium's bill for what came, and
	pays a third of it."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
	from erpnext.stock.doctype.purchase_receipt.mapper import make_purchase_invoice
	from erpnext.stock.doctype.delivery_note.mapper import make_sales_invoice

	if frappe.db.exists("Sales Invoice", {"company": BRANCH, "docstatus": 1}):
		return _pay_a_third()
	with as_user("huda@one.test"):
		note = frappe.db.get_value("Delivery Note", {"company": BRANCH, "docstatus": 1}, "name")
		invoice = make_sales_invoice(note)
		dated(invoice, ago(8))
		invoice.due_date = add_days(invoice.posting_date, 30)
		for row in invoice.get("payment_schedule") or []:
			row.due_date = invoice.due_date
		invoice = save(invoice, submit=True)
		payment = get_payment_entry("Sales Invoice", invoice.name, party_amount=invoice.grand_total / 2)
		payment.posting_date = ago(3)
		payment.reference_no, payment.reference_date = "RYD-TT-1182", ago(3)
		save(payment, submit=True)
		receipt = frappe.db.get_value("Purchase Receipt", {"company": BRANCH, "docstatus": 1}, "name")
		bill = make_purchase_invoice(receipt)
		dated(bill, ago(10))
		bill.bill_no, bill.bill_date = "RAE-INV-5521", ago(11)
		bill.due_date = add_days(bill.posting_date, 45)
		for row in bill.get("payment_schedule") or []:
			row.due_date = bill.due_date
		save(bill, submit=True)
	_pay_a_third()


def _pay_a_third():
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	bill = frappe.db.get_value("Purchase Invoice", {"company": BRANCH, "docstatus": 1, "is_return": 0}, ["name", "grand_total"], as_dict=True)
	if not bill or frappe.db.exists("Payment Entry", {"company": BRANCH, "party_type": "Supplier", "docstatus": 1}):
		return
	with as_user("huda@one.test"):
		payment = get_payment_entry("Purchase Invoice", bill.name, party_amount=round(bill.grand_total / 3))
		payment.posting_date = ago(2)
		payment.reference_no, payment.reference_date = "RYD-CHQ-0417", ago(2)
		save(payment, submit=True)


def _job(customer: str):
	"""Samir runs the tower's installation for Riyadh: a milestone with its
	steps, the survey done and the fixing under way."""
	if frappe.db.exists("Project", {"company": BRANCH}):
		return
	with as_user("samir@one.test"):
		project = frappe.new_doc("Project")
		project.update(
			{
				"project_name": "Al Olaya Towers Installation",
				"company": BRANCH,
				"customer": customer,
				"expected_start_date": ago(20),
				"expected_end_date": add_days(ago(20), 75),
			}
		)
		project = save(project)
		milestone = save(
			frappe.get_doc(
				{
					"doctype": "Task",
					"subject": "Installation",
					"project": project.name,
					"company": BRANCH,
					"is_group": 1,
					"is_milestone": 1,
					"exp_start_date": ago(20),
					"exp_end_date": add_days(ago(20), 70),
				}
			)
		)
		for subject, start, days, status in (
			("Site survey", ago(20), 4, "Completed"),
			("Fix brackets on levels 1 to 4", ago(12), 20, "Working"),
			("Glaze levels 1 to 4", add_days(ago(12), 21), 25, "Open"),
		):
			save(
				frappe.get_doc(
					{
						"doctype": "Task",
						"subject": subject,
						"project": project.name,
						"company": BRANCH,
						"parent_task": milestone.name,
						"exp_start_date": start,
						"exp_end_date": add_days(start, days),
						"status": status,
					}
				)
			)


SUPERVISOR = ("Ahmed", "Al-Qahtani", "ahmed@one.test")


def _people():
	"""Riyadh's calendar (Friday and Saturday off, Founding Day and National
	Day), its leave year and the accounts its claims go to; and Ahmed, the
	tower's site supervisor, with his leave allowance, a few days off taken,
	the last two weeks' attendance and a taxi claim Samir approved."""
	from onedesk.one_hr import expense

	year = getdate(today()).year
	holidays = f"{BRANCH} {year}"
	if not frappe.db.exists("Holiday List", holidays):
		days = frappe.new_doc("Holiday List")
		days.update({"holiday_list_name": holidays, "from_date": f"{year}-01-01", "to_date": f"{year}-12-31"})
		for name, day in (("Founding Day", f"{year}-02-22"), ("Saudi National Day", f"{year}-09-23")):
			days.append("holidays", {"holiday_date": day, "description": name})
		for weekday in ("Friday", "Saturday"):
			days.weekly_off = weekday
			days.get_weekly_off_dates()
		days.insert()
	frappe.db.set_value("Company", BRANCH, "default_holiday_list", holidays)
	if not frappe.db.exists("Holiday List Assignment", {"applicable_for": "Company", "assigned_to": BRANCH, "docstatus": 1}):
		make(
			{
				"doctype": "Holiday List Assignment",
				"applicable_for": "Company",
				"assigned_to": BRANCH,
				"holiday_list": holidays,
				"from_date": f"{year}-01-01",
			},
			submit=True,
		)
	if not frappe.db.exists("Leave Period", {"company": BRANCH}):
		make({"doctype": "Leave Period", "from_date": f"{year}-01-01", "to_date": f"{year}-12-31", "company": BRANCH, "is_active": 1})
	for kind in frappe.get_all("Expense Claim Type", pluck="name"):
		claim_type = frappe.get_doc("Expense Claim Type", kind)
		if not any(row.company == BRANCH for row in claim_type.accounts):
			claim_type.append("accounts", {"company": BRANCH, "default_account": f"Expense Claims - {ABBR}"})
			claim_type.save()
	if not frappe.db.exists("Department", {"company": BRANCH, "department_name": "Projects"}):
		make({"doctype": "Department", "department_name": "Projects", "company": BRANCH, "parent_department": frappe.db.get_value("Department", {"is_group": 1, "company": BRANCH}) or "All Departments"})
	first, last, email = SUPERVISOR
	employee = frappe.db.get_value("Employee", {"company": BRANCH, "first_name": first})
	if not employee:
		employee = make(
			{
				"doctype": "Employee",
				"first_name": first,
				"last_name": last,
				"gender": "Male",
				"date_of_birth": "1988-04-17",
				"date_of_joining": f"{year - 2}-03-01",
				"company": BRANCH,
				"designation": "Workshop Supervisor",
				"department": frappe.db.get_value("Department", {"company": BRANCH, "department_name": "Projects"})
				or frappe.db.get_value("Department", {"company": BRANCH, "is_group": 0}),
				"holiday_list": holidays,
				"leave_approver": "samir@one.test",
				"expense_approver": "samir@one.test",
				"personal_email": email,
			}
		).name
	if not frappe.db.exists("Leave Allocation", {"employee": employee, "docstatus": 1}):
		make(
			{
				"doctype": "Leave Allocation",
				"employee": employee,
				"leave_type": "Privilege Leave",
				"from_date": f"{year}-01-01",
				"to_date": f"{year}-12-31",
				"new_leaves_allocated": 21,
			},
			submit=True,
		)
	starts = ago(30)
	while getdate(starts).weekday() != 6:
		starts = add_days(starts, 1)
	if not frappe.db.exists("Leave Application", {"employee": employee}):
		make(
			{
				"doctype": "Leave Application",
				"employee": employee,
				"leave_type": "Privilege Leave",
				"from_date": starts,
				"to_date": add_days(starts, 2),
				"leave_approver": "samir@one.test",
				"description": "Family visit in Abha",
				"status": "Approved",
			},
			submit=True,
		)
	for back in range(14, 0, -1):
		day = ago(back)
		if getdate(day).weekday() in (4, 5) or frappe.db.exists("Attendance", {"employee": employee, "attendance_date": day}):
			continue
		make({"doctype": "Attendance", "employee": employee, "attendance_date": day, "status": "Present", "company": BRANCH}, submit=True)
	if not frappe.db.exists("Expense Claim", {"employee": employee}):
		claim = frappe.new_doc("Expense Claim")
		claim.update(
			{
				"employee": employee,
				"company": BRANCH,
				"expense_approver": "samir@one.test",
				"payable_account": frappe.db.get_value("Company", BRANCH, "default_payable_account") or f"Creditors - {ABBR}",
				"project": frappe.db.get_value("Project", {"company": BRANCH}),
			}
		)
		dated(claim, ago(5))
		claim.append("expenses", {"expense_date": ago(6), "expense_type": "Travel", "description": "Taxis between the tower and the Riyadh stores", "amount": 185, "sanctioned_amount": 185})
		claim = save(claim)
		with as_user("samir@one.test"):
			expense.approve(claim.name)
