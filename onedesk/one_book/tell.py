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
	the credit controllers are told in One rather than mailed."""
	frappe.has_permission("Customer", ptype="email", doc=customer, throw=True)
	currency = frappe.db.get_value("Customer", customer, "default_currency") or frappe.db.get_default(
		"currency"
	)
	notify.notify(
		"Credit Limit Crossed",
		frappe.parse_json(credit_controller_users_list),
		record=("Customer", customer),
		customer=frappe.db.get_value("Customer", customer, "customer_name") or customer,
		outstanding=fmt_money(customer_outstanding, currency=currency),
		limit=fmt_money(credit_limit, currency=currency),
	)
