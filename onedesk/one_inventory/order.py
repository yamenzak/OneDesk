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
	quantity, and what it is short of the level on top when the reorder
	quantity alone would not bring it back — ERPNext's own rule. Pure."""
	level, reorder_qty, projected = flt(level), flt(reorder_qty), flt(projected)
	if projected + reorder_qty <= level:
		return reorder_qty + level - projected
	return reorder_qty


def left(asked: float, ordered: float, held: float) -> float:
	"""What a request line still needs ordering: what it asks for, less what
	submitted orders took and what draft orders hold. Pure."""
	return max(flt(asked) - flt(ordered) - flt(held), 0)


def drafted(lines: list[str], company: str, but: str | None = None) -> dict:
	"""How much of each request line the company's draft orders hold, in
	stock units, {material_request_item: qty}, leaving out the order `but`."""
	if not lines:
		return {}
	rows = frappe.db.sql(
		"""select item.material_request_item, sum(item.stock_qty) as qty
		from `tabPurchase Order Item` item join `tabPurchase Order` doc on doc.name = item.parent
		where doc.docstatus = 0 and doc.company = %(company)s and doc.name != %(but)s
			and item.material_request_item in %(lines)s
		group by item.material_request_item""",
		{"lines": tuple(lines), "company": company, "but": but or ""},
	)
	return {line: flt(qty) for line, qty in rows}


def within_requests(doc, method=None) -> None:
	"""Purchase Order validate: a request line is not ordered beyond what it
	asks for, counting other draft orders too. ERPNext checks it only on
	submit, so two drafts could each order the whole of it. Safe under bulk
	edit and Data Import, and To Order reads the same sums."""
	ours: dict = {}
	for row in doc.items:
		if row.material_request_item:
			ours[row.material_request_item] = ours.get(row.material_request_item, 0) + flt(row.stock_qty or row.qty)
	if not ours:
		return
	asked = {
		row.name: row
		for row in frappe.get_all(
			"Material Request Item",
			filters={"name": ["in", list(ours)]},
			fields=["name", "parent", "item_code", "stock_qty", "ordered_qty"],
		)
	}
	held = drafted(list(ours), doc.company, but=doc.name)
	allowance = flt(frappe.db.get_single_value("Buying Settings", "over_order_allowance"))
	for line, qty in ours.items():
		one = asked.get(line)
		if not one:
			continue
		room = left(one.stock_qty, one.ordered_qty, held.get(line)) * (1 + allowance / 100)
		if qty > room + 0.0001:
			frappe.throw(
				_("Only {0} of {1} on {2} is left to order. Other orders hold the rest.").format(
					frappe.format(room, {"fieldtype": "Float"}), one.item_code, one.parent
				),
				title=_("Ordered Already"),
			)


def rows() -> list[dict]:
	"""What to order, in the company's warehouses: each open purchase request
	line not yet ordered, then each item at or below its level with nothing
	asked for it."""
	from onedesk.one.company import reader_company

	company = reader_company()
	allowed = frappe.get_list(
		"Material Request",
		filters={"company": company, "docstatus": 1, "material_request_type": "Purchase", "status": ["not in", ["Stopped", "Cancelled"]]},
		pluck="name",
		limit_page_length=0,
	)
	requested = frappe.db.sql(
		"""select item.item_code, item.item_name, item.warehouse, item.name as material_request_item,
			item.parent as material_request, item.stock_qty, item.ordered_qty, item.stock_uom as uom,
			item.project, item.schedule_date as needed_by
		from `tabMaterial Request Item` item join `tabMaterial Request` request on request.name = item.parent
		where request.docstatus = 1 and request.material_request_type = 'Purchase' and request.company = %(company)s
			and request.name in %(allowed)s and item.stock_qty > item.ordered_qty
		order by request.transaction_date, item.idx""",
		{"company": company, "allowed": allowed or [""]},
		as_dict=True,
	)
	held = drafted([row.material_request_item for row in requested], company)
	for row in requested:
		row["qty"] = left(row.pop("stock_qty"), row.pop("ordered_qty"), held.get(row.material_request_item))
	requested = [row for row in requested if row["qty"] > 0]
	titles = dict(
		frappe.get_all(
			"Project",
			filters={"name": ["in", list({row.project for row in requested if row.project}) or [""]]},
			fields=["name", "project_name"],
			as_list=True,
		)
	)
	for row in requested:
		row["project_title"] = titles.get(row.project) or row.project
	drafted_lows = frappe.db.sql(
		"""select item.item_code, item.warehouse
		from `tabPurchase Order Item` item join `tabPurchase Order` doc on doc.name = item.parent
		where doc.docstatus = 0 and doc.company = %(company)s""",
		{"company": company},
		as_dict=True,
	)
	asked = {(row.item_code, row.warehouse) for row in requested} | {(row.item_code, row.warehouse) for row in drafted_lows}
	low = [] if not frappe.has_permission("Bin", "read") else frappe.db.sql(
		"""select level.parent as item_code, item.item_name, level.warehouse, item.stock_uom as uom,
			level.warehouse_reorder_level as level, level.warehouse_reorder_qty as reorder_qty,
			coalesce(bin.projected_qty, 0) as projected, coalesce(bin.actual_qty, 0) as actual
		from `tabItem Reorder` level join `tabItem` item on item.name = level.parent
		join `tabWarehouse` warehouse on warehouse.name = level.warehouse and warehouse.company = %(company)s
		left join `tabBin` bin on bin.item_code = level.parent and bin.warehouse = level.warehouse
		where item.disabled = 0 and item.is_purchase_item = 1 and level.material_request_type = 'Purchase'
			and level.warehouse_reorder_level > 0 and coalesce(bin.projected_qty, 0) <= level.warehouse_reorder_level""",
		{"company": company},
		as_dict=True,
	)
	out = [dict(row, key=row.material_request_item, why="requested") for row in requested]
	for row in low:
		if (row.item_code, row.warehouse) in asked:
			continue
		qty = quantity(row.level, row.reorder_qty, row.projected)
		out.append(dict(row, key=f"{row.item_code}:{row.warehouse}", qty=qty, why="low"))
	for row in out:
		row["supplier"], row["rate"] = supplier_for(row["item_code"], company)
	return out


def supplier_for(item: str, company: str | None = None) -> tuple:
	"""Who an item is bought from, its default supplier or whoever sold it
	last, and what it cost a stock unit then."""
	from onedesk.one.company import reader_company

	default = frappe.db.get_value(
		"Item Default", {"parent": item, "company": company or reader_company()}, "default_supplier"
	)
	last = last_bought(item)
	return default or (last.supplier if last else None), (last.unit_rate if last else None)


@frappe.whitelist()
@frappe.read_only()
def read() -> dict:
	"""To Order's page (one_inventory/page/to_order): each line to order with
	its picture, unit and warehouse by their own names, what it would cost at
	the last price, and the figures above them."""
	frappe.has_permission("Material Request", "read", throw=True)
	from erpnext import get_company_currency
	from onedesk.one.company import reader_company

	company = reader_company()
	lines = rows()
	items = {
		one.name: one
		for one in frappe.get_all(
			"Item",
			filters={"name": ["in", list({row["item_code"] for row in lines}) or [""]]},
			fields=["name", "image", "stock_uom"],
		)
	}
	symbols = dict(
		frappe.get_all(
			"UOM",
			filters={"name": ["in", list({row["uom"] for row in lines}) or [""]], "symbol": ["is", "set"]},
			fields=["name", "symbol"],
			as_list=True,
		)
	)
	places = dict(
		frappe.get_all(
			"Warehouse",
			filters={"name": ["in", list({row["warehouse"] for row in lines}) or [""]]},
			fields=["name", "warehouse_name"],
			as_list=True,
		)
	)
	suppliers = dict(
		frappe.get_all(
			"Supplier",
			filters={"name": ["in", list({row["supplier"] for row in lines if row["supplier"]}) or [""]]},
			fields=["name", "supplier_name"],
			as_list=True,
		)
	)
	for row in lines:
		row["image"] = (items.get(row["item_code"]) or {}).get("image")
		row["unit"] = symbols.get(row["uom"]) or row["uom"]
		row["warehouse_label"] = places.get(row["warehouse"]) or row["warehouse"]
		row["supplier_name"] = suppliers.get(row["supplier"]) or row["supplier"]
		row["cost"] = flt(row["qty"]) * flt(row["rate"]) if row["rate"] else None
	priced = [row["cost"] for row in lines if row["cost"] is not None]
	return {
		"lines": lines,
		"currency": get_company_currency(company) if company else None,
		"figures": {
			"lines": len(lines),
			"requested": sum(1 for row in lines if row["why"] == "requested"),
			"low": sum(1 for row in lines if row["why"] == "low"),
			"cost": sum(priced),
			"unpriced": len(lines) - len(priced),
			"suppliers": len({row["supplier"] for row in lines if row["supplier"]}),
		},
		"can": {
			"order": bool(frappe.has_permission("Purchase Order", "create")),
			"request": bool(frappe.has_permission("Material Request", "create")),
		},
	}


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
	from onedesk.one.company import reader_company

	picked = json.loads(rows) if isinstance(rows, str) else rows
	made = []
	for name, lines in grouped(picked, supplier).items():
		doc = frappe.new_doc("Purchase Order")
		doc.company = reader_company()
		doc.supplier = name
		doc.transaction_date = nowdate()
		bill_in(doc, "Supplier", name)
		for line in lines:
			lead = frappe.get_cached_value("Item", line["item_code"], "lead_time_days") or 0
			doc.append(
				"items",
				{
					"item_code": line["item_code"],
					"qty": flt(line["qty"]),
					"uom": line.get("uom") or frappe.get_cached_value("Item", line["item_code"], "stock_uom"),
					"conversion_factor": 1,
					"warehouse": line["warehouse"],
					"schedule_date": add_days(nowdate(), max(int(lead), 1)),
					"material_request": line.get("material_request"),
					"material_request_item": line.get("material_request_item"),
					"project": (
						frappe.db.get_value("Material Request Item", line["material_request_item"], "project")
						if line.get("material_request_item")
						else line.get("project")
					),
				},
			)
		doc.set_missing_values()
		doc.insert()
		made.append(doc.name)
	if not made:
		frappe.throw(_("Nothing to order: pick rows, and a supplier for those that have none."))
	return made
