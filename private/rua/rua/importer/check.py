"""The import, checked against the old app's own figures and against the
books' own rules. Every line is the old app's number beside One's. A line
that differs and is meant to says why; one that differs and isn't is a
fault in the import.

Last, a contract with retention is billed on the copy and taken back, to
show that what Rua never used works with Rua's own accounts.
"""

import json

import frappe
from frappe.utils import add_months, flt, getdate, today
from onedesk.one_project.retention import HELD

from rua.importer.attendance import state
from rua.importer.people import ANNUAL
from rua.importer.quotations import QUOTATION

NEAR = 1.0


def run(run_):
	rows = []

	def line(subject, old, one, why=None, near=NEAR):
		difference = flt(one, 2) - flt(old, 2)
		result = "Agrees" if abs(difference) <= near else ("Explained" if why else "Differs")
		rows.append(
			{
				"subject": subject,
				"old": flt(old, 2),
				"one": flt(one, 2),
				"difference": flt(difference, 2),
				"result": result,
				"note": why if result != "Agrees" else None,
			}
		)

	old = Old(run_)
	counts(run_, old, line)
	sales(run_, old, line)
	buying(run_, old, line)
	books(run_, old, line)
	people(run_, old, line)
	retention_sample(run_, line)
	projects(run_, old)
	doc = frappe.get_single("Rua Import")
	doc.set("checks", rows)
	doc.flags.ignore_permissions = True
	doc.save()


class Old:
	"""The old app's own totals, worked out the way it worked them out
	(its reconcile_single_project_financials)."""

	def __init__(self, run_):
		self.invoices = [
			one
			for one in run_.docs("RUA Invoice")
			if one.get("type") == "Tax Invoice" and one.get("status") == "Final"
		]
		from rua.importer.payments import copies, family
		from rua.importer.projects import merged, own_contracts

		payments = [one for one in run_.docs("RUA Payment") if one.get("status") == "Submitted"]
		self.twice = [one for one in payments if one["name"] in copies(payments, family(run_))]
		self.counted_twice = {one["name"] for one in self.twice}
		payments = [one for one in payments if one["name"] not in self.counted_twice]
		self.received = [one for one in payments if one.get("type") == "Receive"]
		self.paid = [one for one in payments if one.get("type") == "Pay"]
		self.petty = [one for one in payments if one.get("type") == "Pay: Petty Cash"]
		self.final_lpos = [one for one in run_.docs("RUA LPO") if one.get("status") == "Final"]
		self.projects = run_.docs("RUA Project")
		self.joined = merged()
		self.own, _beyond = own_contracts(self.projects, self.joined)

	@staticmethod
	def total(rows, field):
		return sum(flt(one.get(field)) for one in rows)


def one(sql, *values):
	return flt(frappe.db.sql(sql, values)[0][0])


def counts(run_, old, line):
	made = dict(
		frappe.db.sql("select target_doctype, count(*) from `tabRua Import Record` group by target_doctype")
	)
	from rua.importer.projects import folded

	projects = [p for p in old.projects if p.get("status") != "Tender"]
	tenders = [p for p in old.projects if p.get("status") == "Tender"]
	line(
		"Projects, an Original Contract or Scope, or a merged sub-project, folded into its main project",
		sum(1 for p in projects if not folded(p, old.joined)),
		one(
			"select count(distinct target_name) from `tabRua Import Record` where target_doctype = 'Project'"
		),
		near=0,
	)
	line(
		"Tenders, as opportunities",
		len(tenders),
		made.get("Opportunity"),
		"A tender with no client named has nobody to be an opportunity for",
		near=0,
	)
	line(
		"Contracts, as sales orders",
		sum(1 for value in old.own.values() if value > 0),
		one("select count(*) from `tabSales Order` where docstatus = 1"),
		near=0,
	)
	line("Quotations", len(run_.docs(QUOTATION)), made.get("Quotation"), near=0)
	line("Employees", len(run_.docs("RUA Employee")), made.get("Employee"), near=0)
	line("Leave", len(run_.docs("RUA Leave")), made.get("Leave Application"), near=0)


def sales(run_, old, line):
	invoices = old.invoices
	everything = sum(flt(p.get("contract_value")) for p in old.projects if p.get("status") != "Tender")
	line(
		"Contract value, each piece of work once",
		sum(old.own.values()),
		one("select sum(grand_total) from `tabSales Order` where docstatus = 1"),
	)
	line(
		"Contract value the old app counted twice",
		everything - sum(old.own.values()),
		0,
		"A main project's contract was the total of its sub-projects' and was added to theirs, or a merged "
		"sub-project's was already in its main's. Each is listed",
	)
	line(
		"Invoiced, with VAT",
		old.total(invoices, "grand_total"),
		one("select sum(grand_total) from `tabSales Invoice` where docstatus = 1"),
	)
	line(
		"Invoiced before VAT, less retention",
		old.total(invoices, "amount_after_retention"),
		one("select sum(net_total) from `tabSales Invoice` where docstatus = 1"),
	)
	line(
		"VAT on sales",
		old.total(invoices, "vat_after_retention"),
		one("select sum(total_taxes_and_charges) from `tabSales Invoice` where docstatus = 1"),
	)
	line(
		"Payments the old app has twice",
		old.total(old.twice, "amount"),
		0,
		"The same payment entered again on another part of the project. Each copy is listed and left out",
	)
	line(
		"Received from clients, each payment once",
		old.total(old.received, "amount"),
		one(
			"select sum(paid_amount) from `tabPayment Entry` where docstatus = 1 and payment_type = 'Receive'"
		),
	)
	kept = sum(flt(i.get("amount")) - flt(i.get("amount_after_retention")) for i in invoices)
	line(
		"Retention held",
		kept,
		one("select sum(one_retention_held) from `tabSales Invoice` where docstatus = 1"),
	)
	line(
		"Retention in Retention Receivable",
		kept,
		one(
			"""select sum(g.debit - g.credit) from `tabGL Entry` g where g.is_cancelled = 0
			and g.account in (select name from `tabAccount` where account_name = 'Retention Receivable')"""
		),
	)
	line(
		"Invoices holding retention",
		sum(1 for i in invoices if flt(i.get("amount")) - flt(i.get("amount_after_retention")) > 0.01),
		one("select count(*) from `tabSales Invoice` where docstatus = 1 and one_retention > 0"),
		near=0,
	)


def buying(run_, old, line):
	odd = [
		f"{lpo['name']} {row.get('item')}: {flt(row.get('qty'))} x {flt(row.get('unit_price'))} is not {flt(row.get('total_amount'))}"
		for lpo in old.final_lpos
		for row in lpo.get("items") or []
		if abs(flt(row.get("qty")) * flt(row.get("unit_price")) - flt(row.get("total_amount"))) > 0.01
	]
	why = (
		(
			"A line's total in the old LPO isn't its quantity times its price; One bills the total, the rest as a "
			"Line Difference. " + "; ".join(odd)
		)
		if odd
		else None
	)
	line(
		"Final LPOs, as bills",
		old.total(old.final_lpos, "grand_total"),
		one(
			"""select sum(pi.grand_total) from `tabPurchase Invoice` pi where pi.docstatus = 1 and exists
			(select 1 from `tabPurchase Invoice Item` i where i.parent = pi.name and i.purchase_order is not null and i.purchase_order != '')"""
		),
		why,
	)
	line(
		"Paid to suppliers",
		old.total(old.paid, "amount"),
		one("select sum(paid_amount) from `tabPayment Entry` where docstatus = 1 and payment_type = 'Pay'"),
	)
	line(
		"Petty cash",
		old.total(old.petty, "amount"),
		one("select sum(grand_total) from `tabPurchase Invoice` where docstatus = 1 and is_paid = 1"),
	)


def balance(account_type, run_):
	return one(
		"""select sum(g.debit - g.credit) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
		where g.is_cancelled = 0 and g.company = %s and a.account_type = %s""",
		run_.company,
		account_type,
	)


def books(run_, old, line):
	debit = one("select sum(debit) from `tabGL Entry` where is_cancelled = 0 and company = %s", run_.company)
	credit = one(
		"select sum(credit) from `tabGL Entry` where is_cancelled = 0 and company = %s", run_.company
	)
	line("The books balance: debits, credits", debit, credit, near=0.01)
	line(
		"Owed by clients: invoiced less received",
		old.total(old.invoices, "grand_total") - old.total(old.received, "amount"),
		balance("Receivable", run_),
	)
	line(
		"Owed to suppliers: final LPOs less paid",
		-(old.total(old.final_lpos, "grand_total") - old.total(old.paid, "amount")),
		balance("Payable", run_),
		"The same LPO lines as above",
	)
	line(
		"In the banks: received less paid",
		old.total(old.received, "amount") - old.total(old.paid, "amount"),
		balance("Bank", run_),
	)
	line("Spent from petty cash", -old.total(old.petty, "amount"), balance("Cash", run_))
	vat201(run_, old, line)


def vat201(run_, old, line):
	"""The UAE VAT return over the whole history: standard-rated sales and
	the VAT on them, as the old invoices add up."""
	from frappe.desk.query_report import run as report

	said = report(
		"UAE VAT 201",
		filters={"company": run_.company, "from_date": "2023-01-01", "to_date": today()},
		ignore_prepared_report=True,
	)
	rows = [row for row in said.get("result") or [] if isinstance(row, dict)]
	sales_row = next((row for row in rows if str(row.get("no")) == "1a"), None)
	if not sales_row:
		return
	line(
		"VAT return, sales in Abu Dhabi",
		old.total(old.invoices, "amount_after_retention"),
		number(sales_row.get("amount")),
	)
	line(
		"VAT return, VAT on those sales",
		old.total(old.invoices, "vat_after_retention"),
		number(sales_row.get("vat_amount")),
	)


def number(text):
	"""A figure the report formatted for the page, as a number. Pure."""
	if isinstance(text, int | float):
		return text
	cleaned = "".join(ch for ch in str(text or "") if ch.isdigit() or ch in ".-")
	return flt(cleaned)


def people(run_, old, line):
	marked = 0
	people_ = {
		one["name"]: getdate(one.get("joining_date") or one.get("creation"))
		for one in run_.docs("RUA Employee")
	}

	for day in run_.docs("RUA Attendance"):
		log = day.get("attendance_log")
		log = json.loads(log) if isinstance(log, str) else (log or {})
		when = getdate(day.get("date"))
		marked += sum(
			1
			for who, said in log.items()
			if who in people_ and isinstance(said, dict) and state(said) and when >= people_[who]
		)
	line(
		"Days on the roll-call",
		marked,
		one("select count(*) from `tabAttendance` where docstatus = 1"),
		"A day an approved leave covers is marked On Leave by the leave, including days the roll-call didn't take",
	)
	line(
		"Leave days taken",
		sum(
			max((getdate(one.get("return_date")) - getdate(one.get("leave_date"))).days, 1)
			for one in run_.docs("RUA Leave")
			if one.get("leave_date") and one.get("return_date")
		),
		one(
			"select sum(total_leave_days) from `tabLeave Application` where docstatus = 1 and leave_type = %s",
			ANNUAL,
		),
	)


def retention_sample(run_, line):
	"""Rua held retention once. A sample contract with 10% held, half of it
	billed, shows One holds it on Rua's own accounts, taxed when released as
	the UAE taxes it; then it is taken back."""
	from onedesk.one_project.kinds import CONTRACT_ITEM
	from onedesk.one_project.progress import bill_progress

	from rua.importer.projects import taxes

	customer = frappe.db.get_value("Customer", {"disabled": 0})
	if not customer:
		return
	frappe.db.savepoint("rua_retention_sample")
	try:
		template, rows = taxes(run_, inclusive=False)
		order = frappe.get_doc(
			{
				"doctype": "Sales Order",
				"company": run_.company,
				"customer": customer,
				"transaction_date": today(),
				"delivery_date": today(),
				"one_retention": 10,
				"one_retention_due": add_months(today(), 12),
				"taxes_and_charges": template,
				"taxes": rows,
				"disable_rounded_total": 1,
				"items": [{"item_code": CONTRACT_ITEM, "qty": 1, "rate": 100000, "delivery_date": today()}],
			}
		)
		order.insert(ignore_permissions=True)
		order.submit()
		invoice = bill_progress(order.name, doctype="Sales Order", done=50)
		invoice.insert(ignore_permissions=True)
		invoice.submit()
		booked = one(
			"""select sum(g.debit - g.credit) from `tabGL Entry` g join `tabAccount` a on a.name = g.account
			where g.is_cancelled = 0 and g.voucher_no = %s and a.account_name = 'Retention Receivable'""",
			invoice.name,
		)
		line("Sample contract: 10% held on half of 100,000", 5000, invoice.one_retention_held)
		line("Sample contract: held in Retention Receivable", 5000, booked)
		line("Sample contract: VAT on the work less retention", 2250, invoice.total_taxes_and_charges)
		line("Sample contract: invoice total", 47250, invoice.grand_total)
	finally:
		frappe.db.rollback(save_point="rua_retention_sample")


def projects(run_, old):
	"""A project whose invoices or receipts don't add up to the old app's, by
	project, is listed for the accountant."""
	was = {}
	for project in old.projects:
		made = run_.made("RUA Project", project["name"], "Project")
		if not made:
			continue
		billed, received = was.get(made, (0, 0))
		billed += sum(flt(i.get("grand_total")) for i in old.invoices if i.get("project") == project["name"])
		received += sum(flt(r.get("amount")) for r in old.received if r.get("project") == project["name"])
		was[made] = (billed, received)
	for made, (was_billed, was_received) in was.items():
		billed = one(
			"select sum(grand_total) from `tabSales Invoice` where docstatus = 1 and project = %s", made
		)
		received = one(
			"select sum(paid_amount) from `tabPayment Entry` where docstatus = 1 and payment_type = 'Receive' and project = %s",
			made,
		)
		if abs(billed - was_billed) > NEAR or abs(received - was_received) > NEAR:
			run_.note(
				"To Check",
				"Project",
				made,
				f"Billed {was_billed:,.2f} and received {was_received:,.2f} in the old app; {billed:,.2f} and {received:,.2f} here",
			)
		elif was_received and not was_billed:
			run_.note(
				"No Invoice",
				"Project",
				made,
				f"Received {was_received:,.2f} and nothing invoiced in the old app",
			)
