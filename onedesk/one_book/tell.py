"""What ERPNext mailed from OneBook's screens, told through the hub instead
(onedesk/notifications/README.md)."""

import frappe
from frappe.utils import add_days, flt, fmt_money, formatdate, getdate

from onedesk.one import notify


@frappe.whitelist(methods=["POST"])
def credit_limit(customer: str, company: str):
	"""ERPNext's `customer.send_emails`, which the credit limit dialog calls:
	the credit controllers are told in One rather than mailed, with what the
	customer owes the company in the company's currency, read as ERPNext's
	own check reads it."""
	from erpnext import get_company_currency
	from erpnext.selling.doctype.customer.customer import (
		get_credit_controller_users,
		get_credit_limit,
		get_customer_outstanding,
		is_sales_order_credit_check_bypassed,
	)
	from frappe.utils import get_fullname

	frappe.has_permission("Customer", ptype="email", doc=customer, throw=True)
	frappe.has_permission("Company", doc=company, throw=True)
	limit = get_credit_limit(customer, company)
	if not limit:
		return
	currency = get_company_currency(company)
	outstanding = get_customer_outstanding(customer, company, is_sales_order_credit_check_bypassed(customer, company))
	notify.notify(
		"Credit Limit Crossed",
		get_credit_controller_users(),
		record=("Customer", customer),
		customer=frappe.db.get_value("Customer", customer, "customer_name") or customer,
		by=get_fullname(frappe.session.user),
		outstanding=fmt_money(outstanding, currency=currency),
		limit=fmt_money(limit, currency=currency),
	)


def overdue() -> None:
	"""Each morning: an invoice that went past its due date yesterday, unpaid,
	told once to whoever made it and the customer's account manager."""
	if not frappe.db.get_value("Notification Type", "Invoice Overdue", "enabled"):
		return
	for one in frappe.get_all(
		"Sales Invoice",
		filters={
			"docstatus": 1,
			"is_return": 0,
			"outstanding_amount": [">", 0],
			"due_date": add_days(getdate(), -1),
		},
		fields=["name", "customer", "customer_name", "owner", "due_date", "outstanding_amount", "currency", "party_account_currency"],
	):
		notify.notify(
			"Invoice Overdue",
			_theirs(one.owner, one.customer),
			record=("Sales Invoice", one.name),
			sender="Administrator",
			invoice=one.name,
			customer=one.customer_name or one.customer,
			outstanding=fmt_money(one.outstanding_amount, currency=one.party_account_currency or one.currency),
			date=formatdate(one.due_date),
		)


def bills_due() -> None:
	"""Monday morning: supplier bills falling due in the coming week, to accounts."""
	if not frappe.db.get_value("Notification Type", "Bills Due This Week", "enabled"):
		return
	from frappe.utils.user import get_users_with_role

	from erpnext import get_company_currency

	bills = frappe.get_all(
		"Purchase Invoice",
		filters={
			"docstatus": 1,
			"outstanding_amount": [">", 0],
			"due_date": ["between", [getdate(), add_days(getdate(), 6)]],
		},
		fields=["company", "due_date", "outstanding_amount", "party_account_currency", "conversion_rate"],
		order_by="due_date asc",
	)
	people = sorted({*get_users_with_role("Accounts User"), *get_users_with_role("Accounts Manager")})
	for company in sorted({one.company for one in bills}):
		ours = [one for one in bills if one.company == company]
		currency = get_company_currency(company)
		owed = sum(
			flt(one.outstanding_amount) * ((flt(one.conversion_rate) or 1) if one.party_account_currency and one.party_account_currency != currency else 1)
			for one in ours
		)
		notify.notify(
			"Bills Due This Week",
			people,
			link=f"/desk/purchase-invoice?docstatus=1&company={company}&outstanding_amount=%5B%22%3E%22%2C0%5D",
			sender="Administrator",
			count=len(ours),
			total=fmt_money(owed, currency=currency),
			first=formatdate(ours[0].due_date),
		)


def paid_online(doc, method=None) -> None:
	"""Payment Entry on_submit: a payment made through a payment link, told to
	whoever made the invoice or order it pays and the customer's account
	manager."""
	if doc.payment_type != "Receive" or doc.party_type != "Customer":
		return
	for row in doc.references:
		if not row.get("payment_request") or row.reference_doctype not in ("Sales Invoice", "Sales Order"):
			continue
		owner = frappe.db.get_value(row.reference_doctype, row.reference_name, "owner")
		people = [one for one in _theirs(owner, doc.party) if one != frappe.session.user]
		if people:
			notify.notify(
				"Paid Online",
				people,
				record=(row.reference_doctype, row.reference_name),
				sender="Administrator",
				customer=doc.party_name or doc.party,
				amount=fmt_money(row.allocated_amount, currency=doc.paid_from_account_currency),
				invoice=row.reference_name,
			)


def _theirs(owner: str, customer: str) -> list[str]:
	"""Whoever made the record and the customer's account manager, while they
	can sign in; accounts when neither can."""
	from frappe.utils.user import get_users_with_role

	people = [owner, frappe.db.get_value("Customer", customer, "account_manager")]
	found = frappe.get_all(
		"User", filters={"name": ["in", [one for one in people if one]], "enabled": 1}, pluck="name"
	)
	return found or get_users_with_role("Accounts Manager")


def payment_waiting(row, people: list[str], doc, reasons: list[str]) -> None:
	"""Who may approve a payment out of the ordinary (unusual.py)."""
	from frappe.utils import get_fullname

	notify.notify(
		"Payment Waiting for Approval",
		people,
		record=("Second Approval", row.name),
		who=get_fullname(row.asked_by),
		amount=fmt_money(doc.paid_amount, currency=doc.paid_from_account_currency),
		party=doc.party_name or doc.party,
		reasons=" · ".join(reasons),
	)


def bank_details_waiting(row, people: list[str], party: str, changes: list[str]) -> None:
	"""Who may approve a party's changed bank details (details.py)."""
	from frappe.utils import get_fullname

	notify.notify(
		"Bank Details Waiting for Approval",
		people,
		record=("Second Approval", row.name),
		who=get_fullname(row.asked_by),
		party=party,
		changes=" · ".join(changes),
	)


def bank_details_changed(address: str, party: str) -> None:
	"""A supplier or customer, at its own address, that the bank details it is
	paid into changed (details.py)."""
	from onedesk.one.company import workspace_company

	company = workspace_company()
	notify.mail(
		"Bank Details Changed",
		address,
		party=party,
		company=frappe.db.get_value("Company", company, "company_name") if company else "",
	)
