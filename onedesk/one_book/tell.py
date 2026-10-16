"""What ERPNext mailed from OneBook's screens, told through the hub instead
(docs/NOTIFICATIONS.md, stage 6)."""

import frappe
from frappe.utils import fmt_money

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
