"""What ERPNext mailed from OneBook's screens, told through the hub instead
(onedesk/notifications/README.md)."""

import frappe
from frappe.utils import add_days, fmt_money, formatdate, getdate

from onedesk.one import notify


@frappe.whitelist()
def credit_limit(
	customer: str, customer_outstanding: float, credit_limit: float, credit_controller_users_list: str | list
):
	"""ERPNext's `customer.send_emails`, which the credit limit dialog calls:
	the credit controllers are told in One rather than mailed. Who they are
	and what the customer owes are read here, as erpnext's check reads them;
	the dialog's own list and figures are not trusted, since anybody who may
	mail a customer can call this."""
	from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding
	from frappe.utils import get_fullname
	from frappe.utils.user import get_users_with_role

	frappe.has_permission("Customer", ptype="email", doc=customer, throw=True)
	company = frappe.defaults.get_user_default("company") or frappe.defaults.get_global_default("company")
	limit = get_credit_limit(customer, company)
	if not limit:
		return
	role = frappe.db.get_single_value("Accounts Settings", "credit_controller") or "Sales Master Manager"
	currency = frappe.db.get_value("Customer", customer, "default_currency") or frappe.db.get_default(
		"currency"
	)
	notify.notify(
		"Credit Limit Crossed",
		get_users_with_role(role),
		record=("Customer", customer),
		customer=frappe.db.get_value("Customer", customer, "customer_name") or customer,
		by=get_fullname(frappe.session.user),
		outstanding=fmt_money(get_customer_outstanding(customer, company), currency=currency),
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
		fields=["name", "customer", "customer_name", "owner", "due_date", "outstanding_amount", "currency"],
	):
		notify.notify(
			"Invoice Overdue",
			_theirs(one.owner, one.customer),
			record=("Sales Invoice", one.name),
			sender="Administrator",
			invoice=one.name,
			customer=one.customer_name or one.customer,
			outstanding=fmt_money(one.outstanding_amount, currency=one.currency),
			date=formatdate(one.due_date),
		)


def bills_due() -> None:
	"""Monday morning: supplier bills falling due in the coming week, to accounts."""
	if not frappe.db.get_value("Notification Type", "Bills Due This Week", "enabled"):
		return
	from frappe.utils.user import get_users_with_role

	bills = frappe.get_all(
		"Purchase Invoice",
		filters={
			"docstatus": 1,
			"outstanding_amount": [">", 0],
			"due_date": ["between", [getdate(), add_days(getdate(), 6)]],
		},
		fields=["due_date", "outstanding_amount"],
		order_by="due_date asc",
	)
	if not bills:
		return
	currency = frappe.db.get_default("currency")
	notify.notify(
		"Bills Due This Week",
		sorted({*get_users_with_role("Accounts User"), *get_users_with_role("Accounts Manager")}),
		link="/desk/purchase-invoice?docstatus=1&outstanding_amount=%5B%22%3E%22%2C0%5D",
		sender="Administrator",
		count=len(bills),
		total=fmt_money(sum(one.outstanding_amount for one in bills), currency=currency),
		first=formatdate(bills[0].due_date),
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
