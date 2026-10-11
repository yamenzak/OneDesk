"""What ERPNext mailed from OneInventory, told through the hub instead
(docs/NOTIFICATIONS.md, stage 6)."""

import frappe

from onedesk.one import notify


def raised(doc, method=None) -> None:
	"""Material Request on_submit: one raised by reordering (its rows carry
	the level they were raised at) is told to Purchasing, as ERPNext mailed
	them when Stock Settings said to. That switch is off now; Send This on
	the type decides."""
	rows = [row for row in doc.items if row.get("reorder_level")]
	if not rows:
		return
	from erpnext.stock.reorder_item import get_email_list

	notify.notify(
		"Material Request Raised",
		get_email_list(doc.company),
		record=("Material Request", doc.name),
		request=doc.name,
		items=", ".join(row.item_name or row.item_code for row in rows),
	)


def stock_values() -> None:
	"""Hourly: a recalculation of stock values that failed, and a warehouse
	that posts to an account that is not a stock account, each told once to
	whoever keeps the stock and the books. ERPNext mails the second only to
	System Managers, the operator's role and nobody's in a workspace, and
	marks the first failed without a hook when no outgoing mail is set."""
	from erpnext import get_default_company
	from frappe.utils.user import get_users_with_role

	from onedesk.one_inventory import ready

	people = sorted(set(get_users_with_role("Stock Manager")) | set(get_users_with_role("Accounts Manager")))
	if not people:
		return
	for name in ready.failed_reposts():
		notify.notify(
			"Reposting Failed",
			people,
			record=("Repost Item Valuation", name),
			dedupe_on=["document_type", "document_name"],
			entry=name,
		)
	company = get_default_company()
	if not company or not frappe.get_cached_value("Company", company, "enable_perpetual_inventory"):
		return
	for warehouse, account in ready.wrong_accounts(company):
		notify.notify(
			"Stock Account Wrong",
			people,
			record=("Warehouse", warehouse),
			dedupe_on=["document_type", "document_name"],
			warehouse=warehouse,
			account=account,
		)
