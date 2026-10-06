"""What to order, and the purchase orders it becomes.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, flt, nowdate

from onedesk.one_book.currency import bill_in
from onedesk.one_inventory.item import last_bought


def quantity(level: float, reorder_qty: float, projected: float) -> float:
	"""How many to order of an item at or below its level: its reorder
	quantity, or enough to bring it back to the level if that is more —
	ERPNext's own rule. Pure."""
	return max(flt(reorder_qty), flt(level) - flt(projected))


def rows() -> list[dict]:
	requested = frappe.db.sql(
		"""select item.item_code, item.item_name, item.warehouse, item.name as material_request_item,
			item.parent as material_request, item.stock_qty - item.ordered_qty as qty, item.stock_uom as uom
		from `tabMaterial Request Item` item join `tabMaterial Request` request on request.name = item.parent
		where request.docstatus = 1 and request.material_request_type = 'Purchase'
			and request.status not in ('Stopped', 'Cancelled') and item.stock_qty > item.ordered_qty
		order by request.transaction_date, item.idx""",
		as_dict=True,
	)
	# Rows already on a draft order are being ordered: showing them again
	# invites ordering twice.
	drafted = frappe.db.sql(
		"""select item.item_code, item.warehouse, item.material_request_item
		from `tabPurchase Order Item` item join `tabPurchase Order` doc on doc.name = item.parent
		where doc.docstatus = 0""",
		as_dict=True,
	)
	on_draft = {row.material_request_item for row in drafted if row.material_request_item}
	requested = [row for row in requested if row.material_request_item not in on_draft]
	asked = {(row.item_code, row.warehouse) for row in requested} | {(row.item_code, row.warehouse) for row in drafted}
	low = frappe.db.sql(
		"""select level.parent as item_code, item.item_name, level.warehouse, item.stock_uom as uom,
			level.warehouse_reorder_level as level, level.warehouse_reorder_qty as reorder_qty,
			coalesce(bin.projected_qty, 0) as projected
		from `tabItem Reorder` level join `tabItem` item on item.name = level.parent
		left join `tabBin` bin on bin.item_code = level.parent and bin.warehouse = level.warehouse
		where item.disabled = 0 and item.is_purchase_item = 1 and level.material_request_type = 'Purchase'
			and level.warehouse_reorder_level > 0 and coalesce(bin.projected_qty, 0) <= level.warehouse_reorder_level""",
		as_dict=True,
	)
	out = [dict(row, why=_("Requested")) for row in requested]
	for row in low:
		if (row.item_code, row.warehouse) in asked:
			continue
		out.append(dict(row, qty=quantity(row.level, row.reorder_qty, row.projected), why=_("Low")))
	for row in out:
		row["supplier"], row["rate"] = supplier_for(row["item_code"])
	return out


def supplier_for(item: str) -> tuple:
	from erpnext import get_default_company

	default = frappe.db.get_value(
		"Item Default", {"parent": item, "company": get_default_company()}, "default_supplier"
	)
	last = last_bought(item)
	return default or (last.supplier if last else None), (last.rate if last else None)


def grouped(picked: list[dict], fallback: str | None = None) -> dict:
	"""The rows to order, by supplier; a row with none goes to `fallback`, or
	is left out. Pure."""
	out: dict = {}
	for row in picked:
		supplier = row.get("supplier") or fallback
		if supplier and flt(row.get("qty")) > 0:
			out.setdefault(supplier, []).append(row)
	return out


@frappe.whitelist(methods=["POST"])
def order(rows: str | list, supplier: str | None = None) -> list[str]:
	"""A draft purchase order per supplier from the ticked rows."""
	frappe.has_permission("Purchase Order", "create", throw=True)
	from erpnext import get_default_company

	picked = json.loads(rows) if isinstance(rows, str) else rows
	made = []
	for name, lines in grouped(picked, supplier).items():
		doc = frappe.new_doc("Purchase Order")
		doc.company = get_default_company()
		doc.supplier = name
		doc.transaction_date = nowdate()
		# A supplier billing in another currency is ordered from in theirs;
		# ERPNext prices the lines in it from the buying price list.
		bill_in(doc, "Supplier", name)
		for line in lines:
			lead = frappe.get_cached_value("Item", line["item_code"], "lead_time_days") or 0
			doc.append(
				"items",
				{
					"item_code": line["item_code"],
					"qty": flt(line["qty"]),
					"warehouse": line["warehouse"],
					"schedule_date": add_days(nowdate(), max(int(lead), 1)),
					"material_request": line.get("material_request"),
					"material_request_item": line.get("material_request_item"),
				},
			)
		doc.set_missing_values()
		doc.insert()
		made.append(doc.name)
	if not made:
		frappe.throw(_("Nothing to order: pick rows, and a supplier for those that have none."))
	return made
