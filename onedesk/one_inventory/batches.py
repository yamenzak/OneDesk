"""Lots and their dates: ERPNext's Batch, with what is left of each and where,
where it came from and where it went, and which are near or past their
expiry date while some is still in stock. ERPNext keeps a batch's moves in the
Serial and Batch Entry rows of each move's bundle, and only marks a batch
expired in its list."""

import frappe
from frappe.utils import add_days, flt, getdate, today

#: How many days ahead a batch is expiring soon.
SOON = 30


def _entries(batch: str) -> list:
	"""The batch's moves that count, oldest first, as ERPNext's ledger
	posted them: received is more than nothing, sent out less."""
	return frappe.get_all(
		"Serial and Batch Entry",
		filters={"batch_no": batch, "docstatus": 1, "is_cancelled": 0},
		fields=["warehouse", "qty", "voucher_type", "voucher_no", "posting_datetime"],
		order_by="posting_datetime asc, creation asc",
	)


def left(batch: str) -> list[dict]:
	"""What is left of the batch in each warehouse, most first."""
	held = {}
	for row in _entries(batch):
		held[row.warehouse] = held.get(row.warehouse, 0) + flt(row.qty)
	return sorted(
		(
			{"warehouse": warehouse, "label": _called(warehouse), "qty": qty}
			for warehouse, qty in held.items()
			if flt(qty, 6) > 0
		),
		key=lambda one: -one["qty"],
	)


def _called(warehouse: str | None) -> str | None:
	"""A warehouse by its own name, without the company's letters after it."""
	return warehouse and (frappe.get_cached_value("Warehouse", warehouse, "warehouse_name") or warehouse)


def moves(batch: str) -> list[dict]:
	"""Each document that brought the batch into a warehouse or took it out,
	with how much, newest first: a transfer is out of one and into another.
	Its oldest in is where it came from."""
	said = {}
	for row in _entries(batch):
		key = (row.voucher_type, row.voucher_no, row.warehouse)
		one = said.setdefault(
			key,
			{
				"doctype": row.voucher_type,
				"name": row.voucher_no,
				"warehouse": row.warehouse,
				"on": row.posting_datetime,
				"qty": 0.0,
			},
		)
		one["qty"] += flt(row.qty)
	return list(reversed(said.values()))


def state(expiry_date, qty, day=None) -> str | None:
	"""Expired, Expiring Soon or nothing, for a batch with `qty` in stock.
	Pure."""
	if not expiry_date or flt(qty) <= 0:
		return None
	day = getdate(day or today())
	expiry = getdate(expiry_date)
	if expiry < day:
		return "Expired"
	if expiry <= add_days(day, SOON):
		return "Expiring Soon"
	return None


def dated(item: str | None = None) -> list:
	"""The batches with some in stock and an expiry date within SOON days or
	past, soonest first, as the reader may see them."""
	filters = {
		"disabled": 0,
		"batch_qty": [">", 0],
		"expiry_date": ["<=", add_days(today(), SOON)],
	}
	if item:
		filters["item"] = item
	return frappe.get_list(
		"Batch",
		filters=filters,
		fields=["name", "batch_id", "item", "item_name", "batch_qty", "stock_uom", "expiry_date"],
		order_by="expiry_date asc",
	)
