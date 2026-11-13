"""What each company of the group beside Sahara Glass is declared as and built
with (one_demo/group.py): its people, address, bank and VAT, and the records
every business keeps, each made for that company by whoever does that work
there: parties and items, invoices and bills with their payments, and the
month's journal entries."""

from dataclasses import dataclass

import frappe
from frappe.utils import add_days, flt, getdate

from onedesk.one_book.currency import bill_in
from onedesk.one_demo.base import as_user, dated, make, on, once, rated, save, tag, today


@dataclass(frozen=True)
class Person:
	"""Somebody on the company's payroll; `email` and `levels` (each app's,
	by folder) when they sign in. The first person runs the company."""

	first: str
	last: str
	email: str | None
	department: str
	designation: str
	gender: str
	joined: str
	pay: int
	levels: tuple = ()


@dataclass(frozen=True)
class Firm:
	name: str
	abbr: str
	field: str
	emirate: str
	street: str
	phone: str
	email: str
	website: str
	tax_id: str
	bank: str
	iban: str
	sales_tax: str
	opening: int
	people: tuple

	@property
	def owner(self) -> str:
		return self.people[0].email

	def wh(self, place: str) -> str:
		return f"{place} - {self.abbr}"

	def answer(self, parent: str) -> dict:
		"""The company as the setup job's answers give it."""
		return {"name": self.name, "abbr": self.abbr, "country": "United Arab Emirates", "currency": "AED", "chart": "Standard", "year_starts": "01-01", "parent": parent}

	def invited(self) -> list[dict]:
		"""Its people who sign in, as the setup job's answers invite them."""
		return [{"email": one.email, "first_name": one.first, "last_name": one.last, "levels": dict(one.levels)} for one in self.people if one.email]


def settle(firm: Firm, password=None) -> str:
	"""The company as its owner sets it up: their people kept to it, its
	details and address, VAT on what it sells and buys, the bank and the
	money it opened the year with. Returns the bank's ledger."""
	_signed_in(firm, password)
	_details(firm)
	_vat(firm)
	bank = _bank(firm)
	if not frappe.db.exists("Journal Entry", {"company": firm.name, "voucher_type": "Opening Entry", "docstatus": 1}):
		entry(firm, on(1, 1), "Opening balances", ((bank, firm.opening, 0), (_equity(firm), 0, firm.opening)), kind="Opening Entry")
	employ(firm)
	return bank


def _signed_in(firm: Firm, password=None) -> None:
	"""Each person who signs in works in this company alone, and has agreed
	to what their first sign-in asks."""
	from frappe.utils.password import update_password

	from onedesk.trust_center import gate

	for one in firm.people:
		if not one.email or not frappe.db.exists("User", one.email):
			continue
		if password:
			update_password(one.email, password)
		if not frappe.db.exists("User Permission", {"user": one.email, "allow": "Company"}):
			frappe.get_doc({"doctype": "User Permission", "user": one.email, "allow": "Company", "for_value": firm.name, "is_default": 1}).insert(ignore_permissions=True)
		frappe.defaults.set_user_default("company", firm.name, one.email)
		with as_user(one.email):
			waiting = [row["document"] for row in gate.standing() if not row["accepted"]]
			if waiting:
				gate.accept(waiting)


def _details(firm: Firm) -> None:
	from onedesk.one_book import vat

	company = frappe.get_doc("Company", firm.name)
	if not company.tax_id:
		company.update({"tax_id": firm.tax_id, "phone_no": firm.phone, "email": firm.email, "website": firm.website})
		company.save()
	if not vat.company_address(firm.name):
		vat.add_address(firm.name, firm.emirate, firm.street, firm.emirate)


def _vat(firm: Firm) -> None:
	"""The return's VAT accounts, and the rate each side charges, as the
	Books Check sets them (one_book/ready.py)."""
	from onedesk.one_book import ready, vat

	if not vat.settled_accounts(firm.name):
		vat.uae_accounts(firm.name)
	ready.charge(firm.name, "Sales Taxes and Charges Template", f"{firm.sales_tax} - {firm.abbr}")
	ready.charge(firm.name, "Purchase Taxes and Charges Template", f"UAE VAT 5% - {firm.abbr}")


def _bank(firm: Firm) -> str:
	from onedesk.one_book.ready import add_bank

	found = frappe.db.get_value("Bank Account", {"company": firm.name, "is_company_account": 1}, "account")
	if found:
		return found
	with as_user(firm.owner):
		made = add_bank(firm.bank, "Current Account", iban=firm.iban)
	return frappe.db.get_value("Bank Account", made, "account")


def account(firm: Firm, name: str, under: str = "Indirect Expenses") -> str:
	"""A ledger by its name, added under `under` where the chart has none."""
	found = frappe.db.get_value("Account", {"company": firm.name, "account_name": name, "is_group": 0})
	if found:
		return found
	parent = frappe.db.get_value("Account", {"company": firm.name, "account_name": under, "is_group": 1})
	return make({"doctype": "Account", "account_name": name, "parent_account": parent, "company": firm.name}).name


def _equity(firm: Firm) -> str:
	return frappe.db.get_value("Account", {"company": firm.name, "root_type": "Equity", "is_group": 0, "account_name": ["like", "%Capital%"]}) or frappe.db.get_value(
		"Account", {"company": firm.name, "root_type": "Equity", "is_group": 0}
	)


def employ(firm: Firm) -> dict:
	"""Everybody on its payroll, each reporting to whoever runs it."""
	made = {}
	for one in firm.people:
		found = frappe.db.get_value("Employee", {"company": firm.name, "first_name": one.first, "last_name": one.last})
		if found:
			made[one.first] = found
			continue
		if not frappe.db.exists("Designation", one.designation):
			make({"doctype": "Designation", "designation_name": one.designation})
		head = firm.people[0]
		made[one.first] = make(
			{
				"doctype": "Employee",
				"first_name": one.first,
				"last_name": one.last,
				"gender": one.gender,
				"date_of_birth": f"{1978 + len(one.first) + len(one.last) % 7}-0{1 + len(one.last) % 9}-1{len(one.first) % 9}",
				"date_of_joining": one.joined,
				"company": firm.name,
				"department": frappe.db.get_value("Department", {"company": firm.name, "department_name": one.department}),
				"designation": one.designation,
				"employment_type": "Full-time" if frappe.db.exists("Employment Type", "Full-time") else None,
				"user_id": one.email,
				"prefered_email": one.email,
				"reports_to": made.get(head.first) if one is not head else None,
				"leave_approver": head.email if one is not head else None,
				"expense_approver": head.email if one is not head else None,
				"status": "Active",
			}
		).name
	return made


def customer(name: str, kind: str = "Company", email: str | None = None, phone: str | None = None, contact: tuple | None = None) -> str:
	"""A customer, with the person to talk to when it is a company."""
	from onedesk.one_demo.masters import _contact

	found = frappe.db.get_value("Customer", {"customer_name": name})
	if found:
		return found
	made = make(
		{
			"doctype": "Customer",
			"customer_name": name,
			"customer_group": "Commercial" if kind == "Company" else "Individual",
			"customer_type": kind,
			"territory": "Dubai",
			"default_currency": "AED",
			"email_id": email if kind == "Individual" else None,
			"mobile_no": phone if kind == "Individual" else None,
		}
	)
	if contact:
		_contact((*contact, email, phone), "Customer", made.name)
	return made.name


def supplier(name: str, group: str, email: str, contact: tuple, firm: Firm | None = None, currency: str = "AED", country: str = "United Arab Emirates") -> str:
	"""A supplier, billing in `currency`: one abroad has a payable account in
	its own currency, as ERPNext wants for a party billed in another one."""
	from onedesk.one_demo.masters import _contact

	found = frappe.db.get_value("Supplier", {"supplier_name": name})
	if not found:
		found = make({"doctype": "Supplier", "supplier_name": name, "supplier_group": group, "default_currency": currency, "country": country}).name
		_contact((*contact, email, None), "Supplier", found)
	if currency != "AED" and firm:
		_payable(firm, found, currency)
	return found


def _payable(firm: Firm, name: str, currency: str) -> None:
	party = frappe.get_doc("Supplier", name)
	if any(row.company == firm.name for row in party.get("accounts")):
		return
	parent = frappe.db.get_value("Account", {"company": firm.name, "account_type": "Payable", "is_group": 0}, "parent_account")
	ledger = once(
		"Account",
		{"company": firm.name, "account_name": f"Creditors {currency}"},
		{"account_name": f"Creditors {currency}", "parent_account": parent, "company": firm.name, "account_type": "Payable", "account_currency": currency},
	).name
	party.append("accounts", {"company": firm.name, "account": ledger})
	party.save()


def item(code: str, name: str, group: str, uom: str, price: float | None = 0, stocked: bool = False) -> str:
	"""An item the company buys or sells, in a group of its own business:
	sold at `price`, sold at a price each invoice gives (None), or only
	bought (0)."""
	for doctype, field, value in (("Item Group", "item_group_name", group), ("UOM", "uom_name", uom)):
		if not frappe.db.exists(doctype, value):
			make({"doctype": doctype, field: value, **({"parent_item_group": "All Item Groups"} if doctype == "Item Group" else {})})
	if frappe.db.exists("Item", code):
		return code
	return make(
		{
			"doctype": "Item",
			"item_code": code,
			"item_name": name,
			"item_group": group,
			"stock_uom": uom,
			"is_stock_item": int(stocked),
			"include_item_in_manufacturing": 0,
			"is_sales_item": int(price != 0),
			"is_purchase_item": 1,
			"standard_rate": price or 0,
		}
	).name


def sell(firm: Firm, user: str, party: str, date, lines, due: int = 30, stock: bool = False, project: str | None = None, remarks: str | None = None):
	"""A sales invoice for `lines` (item, quantity, rate, and what it says
	where it is not the item's name), its goods taken from the stores when
	`stock`."""
	with as_user(user):
		doc = frappe.new_doc("Sales Invoice")
		doc.company = firm.name
		doc.customer = party
		dated(doc, date)
		bill_in(doc, "Customer", party)
		doc.due_date = add_days(date, due)
		doc.project = project
		doc.remarks = remarks
		if stock:
			doc.update_stock = 1
			doc.set_warehouse = firm.wh("Stores")
		for code, qty, rate, *said in lines:
			row = {"item_code": code, "qty": qty, "rate": rate, "project": project}
			if stock:
				row["warehouse"] = firm.wh("Stores")
			if said:
				row["description"] = said[0]
			doc.append("items", row)
		return save(doc, submit=True)


def buy(firm: Firm, user: str, party: str, date, number: str, lines, due: int = 30, stock: bool = False):
	"""A supplier's bill for `lines` (item, quantity, rate, and the ledger it
	is spent on where it is not the item's), received into the stores when
	`stock`."""
	with as_user(user):
		doc = frappe.new_doc("Purchase Invoice")
		doc.company = firm.name
		doc.supplier = party
		dated(doc, date)
		bill_in(doc, "Supplier", party)
		doc.bill_no, doc.bill_date = number, date
		doc.due_date = add_days(date, due)
		if stock:
			doc.update_stock = 1
			doc.set_warehouse = firm.wh("Stores")
		for code, qty, rate, *spent in lines:
			row = {"item_code": code, "qty": qty, "rate": rate}
			if stock:
				row["warehouse"] = firm.wh("Stores")
			if spent:
				row["expense_account"] = account(firm, spent[0])
			doc.append("items", row)
		return save(doc, submit=True)


def settled(firm: Firm, user: str, invoice, date, part: float = 1.0, reference: str | None = None) -> None:
	"""An invoice paid in, or a bill paid out, on `date`: all of it, or
	`part`. Nothing when the day has not come."""
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	if getdate(date) > today():
		return
	invoice.reload()
	with as_user(user):
		amount = flt(invoice.outstanding_amount * part, 2) if part < 1 else None
		payment = get_payment_entry(invoice.doctype, invoice.name, party_amount=amount)
		dated(payment, date)
		payment.reference_no = reference or f"{firm.abbr}-{invoice.name.rsplit('-', 1)[-1]}"
		payment.reference_date = date
		save(rated(payment), submit=True)


def entry(firm: Firm, date, remark: str, lines, kind: str = "Journal Entry") -> None:
	"""A journal entry, `lines` (ledger, debit, credit), named by its remark,
	once."""
	if frappe.db.exists("Journal Entry", {"company": firm.name, "user_remark": remark, "docstatus": 1}):
		return
	doc = frappe.new_doc("Journal Entry")
	doc.voucher_type = kind
	doc.company = firm.name
	dated(doc, date)
	doc.user_remark = remark
	doc.cheque_no = remark[:20]
	doc.cheque_date = date
	for ledger, debit, credit in lines:
		doc.append("accounts", {"account": ledger, "debit_in_account_currency": debit, "credit_in_account_currency": credit})
	save(doc, submit=True)


def monthly(firm: Firm, bank: str, rent: int, utilities: tuple) -> None:
	"""Each month's rent on the first, the month's pay on the last working
	day, and the utility bill on the twentieth, from the bank."""
	pay = sum(one.pay for one in firm.people)
	for month in range(1, today().month + 1):
		day = on(month, 1)
		named = day.strftime("%B")
		entry(firm, day, f"{firm.abbr} rent, {named}", ((account(firm, "Office Rent"), rent, 0), (bank, 0, rent)))
		if month < today().month:
			entry(firm, on(month, 26), f"{firm.abbr} salaries, {named}", ((account(firm, "Salary"), pay, 0), (bank, 0, pay)))
			used = utilities[(month - 1) % len(utilities)]
			entry(firm, on(month, 20), f"{firm.abbr} DEWA, {named}", ((account(firm, "Utility Expenses"), used, 0), (bank, 0, used)))


def event(user: str, subject: str, starts, hours: float, team=(), about: tuple | None = None, place: str | None = None) -> None:
	"""An event as Add Event makes it, once."""
	from frappe.utils import add_to_date, get_datetime

	from onedesk.one_calendar import events

	begins = get_datetime(starts)
	if frappe.db.exists("Event", {"subject": subject, "starts_on": begins}):
		return
	with as_user(user):
		made = events.make(
			{
				"subject": subject,
				"starts_on": str(begins),
				"ends_on": str(add_to_date(begins, hours=hours)),
				"team": list(team),
				"location": place,
				"reference_doctype": about[0] if about else None,
				"reference_docname": about[1] if about else None,
			}
		)
	tag(frappe.get_doc("Event", made))
