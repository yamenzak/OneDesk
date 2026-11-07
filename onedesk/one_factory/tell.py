"""What OneFactory tells people (its kinds are in notifications.py)."""

import frappe
from frappe import _

from onedesk.one import notify


def _buys(user: str) -> bool:
	"""Whoever made a subcontracting order and still buys for the company."""
	return bool(
		frappe.db.get_value("User", user, "enabled")
		and {"Purchase User", "Purchase Manager", "Manufacturing User", "Manufacturing Manager"} & set(frappe.get_roles(user))
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


def late() -> None:
	"""Each morning: work orders wanted yesterday and not all made, told once
	to whoever made the work order and to the project's manager."""
	from frappe.utils import add_days, formatdate, getdate

	for one in frappe.get_all(
		"Work Order",
		filters={
			"docstatus": 1,
			"status": ["in", ["Not Started", "In Process", "Stock Reserved", "Stock Partially Reserved"]],
			"expected_delivery_date": add_days(getdate(), -1),
		},
		fields=["name", "owner", "item_name", "qty", "produced_qty", "stock_uom", "project", "expected_delivery_date"],
	):
		people = {one.owner} if _makes(one.owner) else set()
		if one.project:
			people.add(frappe.db.get_value("Project", one.project, "one_manager"))
		people = sorted(filter(None, people))
		if people:
			notify.notify(
				"Work Order Late",
				people,
				record=("Work Order", one.name),
				sender="Administrator",
				dedupe_on=["document_type", "document_name"],
				order=one.name,
				item=one.item_name,
				due=formatdate(one.expected_delivery_date),
				made=_("{0} of {1} {2}").format(frappe.format(one.produced_qty, {"fieldtype": "Float"}), frappe.format(one.qty, {"fieldtype": "Float"}), _(one.stock_uom or "")).strip(),
			)


def _makes(user: str) -> bool:
	"""Whoever made a work order and still works in the workshop."""
	return bool(
		frappe.db.get_value("User", user, "enabled")
		and {"Manufacturing User", "Manufacturing Manager"} & set(frappe.get_roles(user))
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
