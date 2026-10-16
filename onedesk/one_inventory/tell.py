"""What ERPNext mailed from OneInventory, told through the hub instead
(docs/NOTIFICATIONS.md, stage 6)."""

import frappe
from frappe import _, _lt

from onedesk.one import notify


def raised(doc, method=None) -> None:
	"""Material Request on_submit: one raised by reordering (its rows carry
	the level they were raised at) is told to Purchasing, as ERPNext mailed
	them when Stock Settings said to. That switch is off now; Send This on
	the type decides."""
	rows = [row for row in doc.items if row.get("reorder_level")]
	if not rows:
		_asked(doc)
		return
	from erpnext.stock.reorder_item import get_email_list

	notify.notify(
		"Material Request Raised",
		get_email_list(doc.company),
		record=("Material Request", doc.name),
		request=doc.name,
		items=", ".join(row.item_name or row.item_code for row in rows),
	)


def _asked(doc) -> None:
	"""A person's own request to buy something, told to purchasing; to move,
	issue or make something, told to whoever keeps the stores or makes it."""
	from frappe.utils import formatdate
	from frappe.utils.user import get_users_with_role

	if doc.material_request_type != "Purchase":
		roles = (
			("Manufacturing User", "Manufacturing Manager")
			if doc.material_request_type == "Manufacture"
			else ("Stock User", "Stock Manager")
		)
		people = sorted({one for role in roles for one in get_users_with_role(role)} - {frappe.session.user})
		if people:
			notify.notify(
				"Stock Asked",
				people,
				record=("Material Request", doc.name),
				who=frappe.utils.get_fullname(frappe.session.user),
				kind=_lt(doc.material_request_type),
				request=doc.name,
				items=", ".join(dict.fromkeys(row.item_name or row.item_code for row in doc.items)),
				wanted=formatdate(doc.schedule_date) if doc.get("schedule_date") else _("no date"),
			)
		return

	people = sorted(
		{*get_users_with_role("Purchase User"), *get_users_with_role("Purchase Manager")}
		- {frappe.session.user}
	)
	if not people:
		return
	notify.notify(
		"Material Request Asked",
		people,
		record=("Material Request", doc.name),
		who=frappe.utils.get_fullname(frappe.session.user),
		request=doc.name,
		items=", ".join(dict.fromkeys(row.item_name or row.item_code for row in doc.items)),
		wanted=formatdate(doc.schedule_date) if doc.get("schedule_date") else _("no date"),
	)


def deliveries_late() -> None:
	"""Each morning: a customer's order due yesterday and not all delivered,
	told once to whoever made it and the stock managers."""
	if not frappe.db.get_value("Notification Type", "Delivery Late", "enabled"):
		return
	from frappe.utils import add_days, flt, formatdate, getdate
	from frappe.utils.user import get_users_with_role

	stock = get_users_with_role("Stock Manager")
	for one in frappe.get_all(
		"Sales Order",
		filters={
			"docstatus": 1,
			"status": ["in", ["To Deliver and Bill", "To Deliver"]],
			"delivery_date": add_days(getdate(), -1),
			"per_delivered": ["<", 100],
		},
		fields=["name", "owner", "customer", "customer_name", "delivery_date", "per_delivered"],
	):
		maker = frappe.get_all("User", filters={"name": one.owner, "enabled": 1}, pluck="name")
		notify.notify(
			"Delivery Late",
			sorted({*maker, *stock}) or get_users_with_role("Sales Manager"),
			record=("Sales Order", one.name),
			sender="Administrator",
			order=one.name,
			customer=one.customer_name or one.customer,
			due=formatdate(one.delivery_date),
			left=f"{100 - flt(one.per_delivered):g}%",
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


def work_done(doc, method=None) -> None:
	"""Stock Entry on_submit: the making that finishes a work order is told to
	whoever asked for the goods (the request or the customer's order behind
	it, else whoever made the work order) and to the project's manager."""
	if doc.purpose != "Manufacture" or not doc.work_order:
		return
	order = frappe.db.get_value(
		"Work Order",
		doc.work_order,
		[
			"name",
			"status",
			"item_name",
			"produced_qty",
			"stock_uom",
			"fg_warehouse",
			"project",
			"material_request",
			"sales_order",
			"owner",
		],
		as_dict=True,
	)
	if not order or order.status != "Completed":
		return
	asked = None
	if order.material_request:
		asked = frappe.db.get_value("Material Request", order.material_request, "owner")
	elif order.sales_order:
		asked = frappe.db.get_value("Sales Order", order.sales_order, "owner")
	people = {asked or order.owner}
	if order.project:
		people.add(frappe.db.get_value("Project", order.project, "one_manager"))
	notify.notify(
		"Work Order Done",
		sorted(filter(None, people)),
		record=("Work Order", order.name),
		dedupe_on=["document_type", "document_name"],
		order=order.name,
		qty=f"{frappe.format(order.produced_qty, {'fieldtype': 'Float'})} {_(order.stock_uom or '')}".strip(),
		item=order.item_name,
		warehouse=frappe.get_cached_value("Warehouse", order.fg_warehouse, "warehouse_name")
		or order.fg_warehouse,
	)


def handed_over(doc, method=None) -> None:
	"""Asset Movement on_submit: whoever is given a piece of equipment is told,
	by the account on their employee record. ERPNext tells nobody."""
	date = frappe.utils.formatdate(doc.transaction_date)
	by = frappe.utils.get_fullname(doc.owner)
	for row in doc.assets:
		user = frappe.db.get_value("Employee", row.to_employee, "user_id") if row.to_employee else None
		if not user:
			continue
		notify.notify(
			"Equipment Handed Over",
			[user],
			record=("Asset", row.asset),
			asset=row.asset_name or frappe.db.get_value("Asset", row.asset, "asset_name"),
			by=by,
			date=date,
		)


#: How far ahead a service is told.
SOON = 7


def services() -> None:
	"""Daily: a service due within a week is told once to whoever does it, and
	one past its date and not done is told once to them and the maintenance
	team's manager. ERPNext only marks it Overdue."""
	from frappe.utils import add_days, formatdate, getdate, today

	day = getdate(today())
	for log in frappe.get_all(
		"Asset Maintenance Log",
		filters={
			"docstatus": 0,
			"maintenance_status": ["in", ["Planned", "Overdue"]],
			"due_date": ["<=", add_days(day, SOON)],
		},
		fields=["name", "asset_maintenance", "task_name", "due_date", "task_assignee_email"],
	):
		asset = frappe.db.get_value("Asset", log.asset_maintenance, "asset_name") or log.asset_maintenance
		late = getdate(log.due_date) < day
		people = [log.task_assignee_email]
		if late:
			people.append(
				frappe.db.get_value("Asset Maintenance", log.asset_maintenance, "maintenance_manager")
			)
		notify.notify(
			"Service Late" if late else "Service Due",
			sorted(set(filter(None, people))),
			record=("Asset Maintenance Log", log.name),
			# Due and then late are two things to tell, each once.
			dedupe_on=["type", "document_type", "document_name"],
			task=log.task_name,
			asset=asset,
			due=formatdate(log.due_date),
		)


def expiring() -> None:
	"""Daily: a batch with some in stock that expires within a month is told
	once to whoever keeps the stores, so it is used or sold first. ERPNext
	only greys it out in its list. See one_inventory/batches.py."""
	from frappe.utils import add_days, flt, formatdate, today
	from frappe.utils.user import get_users_with_role

	from onedesk.one_inventory.batches import SOON

	people = sorted(get_users_with_role("Stock Manager"))
	if not people:
		return
	for batch in frappe.get_all(
		"Batch",
		filters={
			"disabled": 0,
			"batch_qty": [">", 0],
			"expiry_date": ["between", [today(), add_days(today(), SOON)]],
		},
		fields=["name", "batch_id", "item", "item_name", "batch_qty", "stock_uom", "expiry_date"],
	):
		notify.notify(
			"Expiring Soon",
			people,
			record=("Batch", batch.name),
			dedupe_on=["type", "document_type", "document_name"],
			batch=batch.batch_id or batch.name,
			item=batch.item_name or batch.item,
			left=f"{flt(batch.batch_qty):g} {batch.stock_uom or ''}".strip(),
			on=formatdate(batch.expiry_date),
		)


def _asker(request: str) -> str | None:
	"""Whoever asked for a request, while they can sign in; nobody for one
	reordering raised."""
	owner = frappe.db.get_value("Material Request", request, "owner")
	if owner in ("Administrator", "Guest", frappe.session.user):
		return None
	return owner if frappe.db.get_value("User", owner, "enabled") else None


def moved(doc, method=None) -> None:
	"""Stock Entry on_submit: a request it finishes moving or issuing, told to
	whoever asked. ERPNext's rule tells only a request received."""
	for request in dict.fromkeys(row.material_request for row in doc.items if row.get("material_request")):
		status = frappe.db.get_value("Material Request", request, "status")
		person = _asker(request)
		if status in ("Transferred", "Issued") and person:
			notify.notify(
				"Material Request Done",
				person,
				record=("Material Request", request),
				dedupe_on=["document_type", "document_name"],
				request=request,
				status=_lt(status),
			)


def update_status(name: str, status: str):
	"""ERPNext's Stop and Re-open (material_request.update_status), and a
	request stopped told to whoever asked."""
	from erpnext.stock.doctype.material_request.material_request import update_status as theirs

	theirs(name, status)
	person = _asker(name)
	if status == "Stopped" and person:
		notify.notify(
			"Material Request Stopped",
			person,
			record=("Material Request", name),
			request=name,
			by=frappe.utils.get_fullname(frappe.session.user),
		)


def reorder_failed() -> None:
	"""Hourly: reordering that could not raise a request, from the hour's
	Error Log, told to the stock and buying managers. ERPNext mails only
	System Managers, nobody's role in a workspace."""
	from frappe.utils import add_to_date, now_datetime
	from frappe.utils.user import get_users_with_role

	found = frappe.get_all(
		"Error Log",
		filters={
			"method": "Unable to create material request",
			"creation": [">=", add_to_date(now_datetime(), hours=-1)],
		},
		pluck="name",
	)
	people = sorted({*get_users_with_role("Stock Manager"), *get_users_with_role("Purchase Manager")})
	if found and people:
		notify.notify(
			"Reordering Failed",
			people,
			link="/desk/material-request",
			sender="Administrator",
			count=len(found),
		)


def back_late() -> None:
	"""Each morning: subcontracted goods due back yesterday and not back,
	told once to whoever made the order."""
	from frappe.utils import add_days, formatdate, getdate

	for one in frappe.get_all(
		"Subcontracting Order",
		filters={
			"docstatus": 1,
			"status": ["not in", ["Completed", "Closed", "Cancelled"]],
			"schedule_date": add_days(getdate(), -1),
		},
		fields=["name", "owner", "supplier", "supplier_name", "schedule_date"],
	):
		people = [one.owner] if _buys(one.owner) else None
		if people:
			notify.notify(
				"Back From Supplier Late",
				people,
				record=("Subcontracting Order", one.name),
				sender="Administrator",
				dedupe_on=["document_type", "document_name"],
				supplier=one.supplier_name or one.supplier,
				order=one.name,
				due=formatdate(one.schedule_date),
			)
