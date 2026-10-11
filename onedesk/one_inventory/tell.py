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


def late() -> list[dict]:
	"""Submitted orders with goods past the date they were wanted and not all
	here, oldest first. Services are left out, as nothing arrives for them,
	and so are orders closed, on hold or done."""
	from frappe.utils import today

	return frappe.db.sql(
		"""select doc.name, doc.owner, doc.supplier, doc.supplier_name, min(item.schedule_date) as due,
			group_concat(distinct item.item_name order by item.idx separator ', ') as items
		from `tabPurchase Order Item` item join `tabPurchase Order` doc on doc.name = item.parent
			join `tabItem` goods on goods.name = item.item_code
		where doc.docstatus = 1 and doc.status not in ('Closed', 'On Hold', 'Completed', 'Delivered')
			and item.schedule_date < %(today)s and item.received_qty < item.qty
			and (goods.is_stock_item = 1 or goods.is_fixed_asset = 1)
		group by doc.name
		order by due""",
		{"today": today()},
		as_dict=True,
	)


def orders_late() -> None:
	"""Daily: an order whose goods are past their date is told once to
	whoever made it, or to the buying managers when that person no longer
	buys. ERPNext tells nobody."""
	from frappe.utils.user import get_users_with_role

	managers = None
	for one in late():
		people = [one.owner] if _buys(one.owner) else None
		if not people:
			managers = managers if managers is not None else sorted(get_users_with_role("Purchase Manager"))
			people = managers
		if not people:
			continue
		notify.notify(
			"Order Late",
			people,
			record=("Purchase Order", one.name),
			dedupe_on=["document_type", "document_name"],
			supplier=one.supplier_name or one.supplier,
			order=one.name,
			items=one["items"],
			due=frappe.utils.formatdate(one.due),
		)


def _buys(user: str) -> bool:
	return bool(
		frappe.db.get_value("User", user, "enabled")
		and {"Purchase User", "Purchase Manager"} & set(frappe.get_roles(user))
	)
