"""Work a supplier does on our own materials, powder coating say, as OneAI
reads it: what is out now, what went and what came back, each order as
ERPNext's Subcontracting Order keeps it. Subcontracting Order itself is
frappe's own list and form, and every change is its own buttons. How it
works is in the module's AGENTS.md.
"""

import erpnext
import frappe
from frappe.utils import flt, getdate, today

MOST = 40
OUT = ("Open", "Partial Material Transferred", "Material Transferred", "Partially Received")
DONE = ("Completed", "Closed")


def figures() -> dict:
	"""Orders still out, those with materials still to send, those past the
	day they were due back, and what the materials with suppliers are worth."""
	if not frappe.has_permission("Subcontracting Order", "read"):
		return {"out": None, "to_send": None, "late": None, "worth": None}
	out = frappe.get_list(
		"Subcontracting Order",
		filters={"docstatus": 1, "status": ["in", OUT], "company": erpnext.get_default_company()},
		fields=["name", "status", "schedule_date", "supplier_warehouse"],
	)
	day = getdate(today())
	return {
		"out": len(out),
		"to_send": sum(1 for one in out if one.status in ("Open", "Partial Material Transferred")),
		"late": sum(1 for one in out if one.schedule_date and getdate(one.schedule_date) < day),
		"worth": _held({one.supplier_warehouse for one in out if one.supplier_warehouse}),
	}


def _held(warehouses: set) -> float | None:
	"""What the stock in suppliers' warehouses is worth, as the reader may see
	it."""
	if not frappe.has_permission("Bin", "read"):
		return None
	if not warehouses:
		return 0.0
	return flt(
		sum(
			flt(one.stock_value)
			for one in frappe.get_list("Bin", filters={"warehouse": ["in", list(warehouses)]}, fields=["stock_value"])
		)
	)


def orders(done: bool = False, search: str | None = None) -> list[dict]:
	"""Subcontracting orders, still out or done with, the latest first: each
	with what the supplier makes and how much came back, the materials sent
	and used, and when it is due back."""
	if not frappe.has_permission("Subcontracting Order", "read"):
		return []
	filters = {"docstatus": 1, "status": ["in", DONE if done else OUT], "company": erpnext.get_default_company()}
	or_filters = {"name": ["like", f"%{search}%"], "supplier_name": ["like", f"%{search}%"]} if search else None
	found = frappe.get_list(
		"Subcontracting Order",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"supplier",
			"supplier_name",
			"status",
			"transaction_date",
			"schedule_date",
			"per_received",
			"total",
			"project",
			"purchase_order",
			"supplier_warehouse",
		],
		order_by="transaction_date desc, creation desc",
		limit=MOST,
	)
	names = [one.name for one in found] or [""]
	makes: dict = {}
	for row in frappe.get_all(
		"Subcontracting Order Item",
		filters={"parent": ["in", names]},
		fields=["parent", "item_code", "item_name", "qty", "received_qty", "stock_uom"],
		order_by="idx",
	):
		makes.setdefault(row.parent, []).append(
			{
				"item": row.item_code,
				"name": row.item_name,
				"image": frappe.get_cached_value("Item", row.item_code, "image"),
				"qty": flt(row.qty),
				"back": flt(row.received_qty),
				"uom": row.stock_uom,
				"unit": _unit(row.stock_uom),
			}
		)
	sent: dict = {}
	for row in frappe.get_all(
		"Subcontracting Order Supplied Item",
		filters={"parent": ["in", names]},
		fields=["parent", "rm_item_code", "required_qty", "supplied_qty", "consumed_qty", "returned_qty", "stock_uom"],
		order_by="idx",
	):
		sent.setdefault(row.parent, []).append(
			{
				"item": row.rm_item_code,
				"name": frappe.get_cached_value("Item", row.rm_item_code, "item_name") or row.rm_item_code,
				"needed": flt(row.required_qty),
				"sent": flt(row.supplied_qty) - flt(row.returned_qty),
				"used": flt(row.consumed_qty),
				"uom": row.stock_uom,
				"unit": _unit(row.stock_uom),
			}
		)
	projects = {
		one.name: one.project_name
		for one in frappe.get_all("Project", filters={"name": ["in", [one.project for one in found if one.project] or [""]]}, fields=["name", "project_name"])
	}
	day = getdate(today())
	return [
		{
			**one,
			"transaction_date": str(one.transaction_date) if one.transaction_date else None,
			"schedule_date": str(one.schedule_date) if one.schedule_date else None,
			"per_received": flt(one.per_received),
			"total": flt(one.total),
			"project_name": projects.get(one.project),
			"late": one.status in OUT and bool(one.schedule_date) and getdate(one.schedule_date) < day,
			"makes": makes.get(one.name, []),
			"materials": sent.get(one.name, []),
		}
		for one in found
	]


def to_order() -> list[dict]:
	"""Subcontracted purchase orders with no subcontracting order made from
	them yet, so nothing can be sent out for them."""
	if not frappe.has_permission("Purchase Order", "read"):
		return []
	found = frappe.get_list(
		"Purchase Order",
		filters={
			"docstatus": 1,
			"is_subcontracted": 1,
			"status": ["not in", ["Closed", "Completed", "Cancelled"]],
			"company": erpnext.get_default_company(),
		},
		fields=["name", "supplier", "supplier_name", "transaction_date", "schedule_date"],
		order_by="transaction_date desc",
		limit=MOST,
	)
	made = set(
		frappe.get_all(
			"Subcontracting Order", filters={"purchase_order": ["in", [one.name for one in found] or [""]], "docstatus": ["<", 2]}, pluck="purchase_order"
		)
	)
	return [
		{**one, "transaction_date": str(one.transaction_date) if one.transaction_date else None, "schedule_date": str(one.schedule_date) if one.schedule_date else None}
		for one in found
		if one.name not in made
	]


def _unit(uom: str | None) -> str | None:
	"""A unit by its symbol where the workspace gave it one (m for Meter)."""
	return (frappe.get_cached_value("UOM", uom, "symbol") or uom) if uom else uom
