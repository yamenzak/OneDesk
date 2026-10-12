"""Lots (page/lots, frontend/src/lots): batches and serial numbers as one
tool, what each lot holds and where, which go off soon, and the items kept in
lots. The item's Stock tab shows the same rows. How it works is in the
module's README, Under the hood.
"""

import frappe
from frappe.utils import flt

from onedesk.one_inventory import batches

#: How many lots or numbers a tab lists before a search narrows them.
MOST = 60


@frappe.whitelist()
def read(view: str = "batches", search: str | None = None, item: str | None = None, soon: bool | int = 0) -> dict:
	"""The figures, and the batches, serial numbers or items one tab shows."""
	said = {
		"switched_on": bool(frappe.db.get_single_value("Stock Settings", "enable_serial_and_batch_no_for_item")),
		"can": {
			"Batch": bool(frappe.has_permission("Batch", "create")),
			"Item": bool(frappe.has_permission("Item", "write")),
			"switch": bool(set(frappe.get_roles()) & set(_fixers())),
		},
		"figures": figures(),
		"batches": [],
		"serials": [],
		"items": [],
	}
	if view == "serials":
		said["serials"] = serials(search=search, item=item)
	elif view == "items":
		said["items"] = kept_in_lots(search=search)
	else:
		said["batches"] = lots(search=search, item=item, soon=frappe.utils.cint(soon))
	return said


def _fixers() -> tuple:
	from onedesk.one_inventory import ready

	return ready.FIXERS


def figures() -> dict:
	"""Lots with something left, those going off within a month and those
	gone off, and serial numbers in stock, each as the reader may see them."""
	out = {"lots": None, "going_off": None, "gone": None, "serials": None}
	if frappe.has_permission("Batch", "read"):
		held = frappe.get_list("Batch", filters={"disabled": 0, "batch_qty": [">", 0]}, fields=["expiry_date", "batch_qty"])
		states = [batches.state(one.expiry_date, one.batch_qty) for one in held]
		out.update(lots=len(held), going_off=states.count("Expiring Soon"), gone=states.count("Expired"))
	if frappe.has_permission("Serial No", "read"):
		out["serials"] = len(frappe.get_list("Serial No", filters={"status": "Active"}, pluck="name"))
	return out


def lots(search: str | None = None, item: str | None = None, soon: int = 0) -> list[dict]:
	"""Lots with something left, those going off first, each with where it is
	and how much is there."""
	if not frappe.has_permission("Batch", "read"):
		return []
	filters = {"disabled": 0, "batch_qty": [">", 0]}
	if item:
		filters["item"] = item
	or_filters = {"batch_id": ["like", f"%{search}%"], "item_name": ["like", f"%{search}%"], "item": ["like", f"%{search}%"]} if search else None
	found = frappe.get_list(
		"Batch",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "batch_id", "item", "item_name", "batch_qty", "stock_uom", "expiry_date", "manufacturing_date", "supplier"],
		order_by="creation desc",
		limit=MOST,
	)
	out = []
	for one in found:
		state = batches.state(one.expiry_date, one.batch_qty)
		if soon and not state:
			continue
		out.append(
			{
				**one,
				"batch_qty": flt(one.batch_qty),
				"expiry_date": str(one.expiry_date) if one.expiry_date else None,
				"manufacturing_date": str(one.manufacturing_date) if one.manufacturing_date else None,
				"state": state,
				"where": batches.left(one.name),
			}
		)
	# Those going off first, then those with no date.
	return sorted(out, key=lambda one: (one["expiry_date"] is None, one["expiry_date"] or ""))


def serials(search: str | None = None, item: str | None = None) -> list[dict]:
	"""Serial numbers, those in stock first, each with where it is or who has
	it, and its warranty."""
	if not frappe.has_permission("Serial No", "read"):
		return []
	filters = {"item_code": item} if item else {}
	or_filters = {"serial_no": ["like", f"%{search}%"], "item_name": ["like", f"%{search}%"]} if search else None
	found = [
		{**one, "warranty_expiry_date": str(one.warranty_expiry_date) if one.warranty_expiry_date else None}
		for one in frappe.get_list(
			"Serial No",
			filters=filters,
			or_filters=or_filters,
			fields=["name", "serial_no", "item_code", "item_name", "status", "warehouse", "customer", "batch_no", "warranty_expiry_date"],
			order_by="modified desc",
			limit=MOST,
		)
	]
	return sorted(found, key=lambda one: one["status"] != "Active")


@frappe.whitelist()
@frappe.read_only()
def can_be_tracked(doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None = None):
	"""The items Track Lots offers: stock items not kept in lots or by
	number yet that have never moved, since ERPNext fixes how an item is kept
	once it has."""
	moved = set(frappe.get_all("Bin", filters={"actual_qty": ["!=", 0]}, pluck="item_code", distinct=True))
	moved |= set(frappe.get_all("Stock Ledger Entry", filters={"is_cancelled": 0}, pluck="item_code", distinct=True))
	found = frappe.get_list(
		"Item",
		filters={"is_stock_item": 1, "has_batch_no": 0, "has_serial_no": 0, "disabled": 0},
		or_filters={"name": ["like", f"%{txt}%"], "item_name": ["like", f"%{txt}%"]} if txt else None,
		fields=["name", "item_name"],
		order_by="item_name asc",
		limit=0,
	)
	free = [[one.name, one.item_name] for one in found if one.name not in moved]
	return free[int(start) : int(start) + int(page_len)]


def kept_in_lots(search: str | None = None) -> list[dict]:
	"""The items kept in lots or by serial number, and how each is set up."""
	if not frappe.has_permission("Item", "read"):
		return []
	or_filters = {"has_batch_no": 1, "has_serial_no": 1}
	filters = {"disabled": 0}
	if search:
		filters["item_name"] = ["like", f"%{search}%"]
	return frappe.get_list(
		"Item",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"item_name",
			"image",
			"stock_uom",
			"has_batch_no",
			"has_serial_no",
			"create_new_batch",
			"batch_number_series",
			"has_expiry_date",
			"shelf_life_in_days",
			"serial_no_series",
		],
		order_by="item_name asc",
		limit=MOST,
	)
