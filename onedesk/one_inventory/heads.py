"""What an item's, an asset's, a warehouse's, a receipt's and a delivery's
form say above their fields (a work order's and a bill of materials' are
OneFactory's): the heads, the measures they place and the verbs
they offer. See one/head.py.
"""

from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import flt, fmt_money, formatdate, getdate, today
from frappe.utils.caching import request_cache

from onedesk.one import figures, stages
from onedesk.one_inventory import assets, batches, custody, item

FIXED = [["is_fixed_asset", "=", 1]]
STOCK = [["is_stock_item", "=", 1]]
SUBMITTED = [["docstatus", "=", 1]]


@request_cache
def _item(name: str) -> dict:
	return item.said(name)


@request_cache
def _asset(name: str) -> dict:
	return assets.said(name)


def _money(value) -> str:
	return fmt_money(flt(value), currency=frappe.db.get_default("currency"))


def _count(doc, value) -> str:
	return f"{fmt_money(flt(value), precision=0)} {_(doc.stock_uom or '')}".strip()


def on_hand(doc):
	said = _item(doc.name)
	return {"value": _count(doc, said["on_hand"]), "tone": None if said["on_hand"] > 0 else "quiet"}


def free(doc):
	said = _item(doc.name)
	return {"value": _count(doc, said["free"]), "meter": {"value": said["free"], "of": said["on_hand"]}}


def on_order(doc):
	ordered = _item(doc.name)["ordered"]
	if not ordered:
		return {"value": _count(doc, 0), "tone": "quiet", "route": None}
	return _count(doc, ordered)


def worth(doc):
	return _money(_item(doc.name)["value"])


def reorder(doc):
	said = _item(doc.name)
	if said["below"]:
		return {"value": _("Low in {0}").format(", ".join(said["below"])), "tone": "alarm"}
	return {"value": _("Above its level") if said["levels"] else _("No level set"), "tone": "quiet"}


def last_bought(doc):
	"""A service that is only ever sold was never bought, and saying so is noise."""
	last = _item(doc.name)["last"]
	if last:
		return {
			"label": _("Last Purchase Rate · {0}").format(
				formatdate(last.on_date)
			),
			"value": _("{0} from {1}").format(_money(last.rate), last.supplier),
		}
	return {"value": _("Never"), "tone": "quiet"} if doc.is_stock_item else None


def worth_now(doc):
	return _money(_asset(doc.name)["worth"])


def cost(doc):
	return _money(_asset(doc.name)["cost"])


def _depreciating(doc) -> bool:
	said = _asset(doc.name)
	return doc.docstatus == 1 and said["depreciates"] and bool(said["months"])


def depreciation(doc):
	"""Before it is registered, or when it never depreciates. Otherwise the
	two below say it."""
	if doc.docstatus == 0:
		return {"value": _("Starts when registered"), "tone": "waiting"}
	return None if _depreciating(doc) else {"value": _("Does not depreciate"), "tone": "quiet"}


def written_off(doc):
	if not _depreciating(doc):
		return None
	said = _asset(doc.name)
	return {
		"value": _("{0} of {1} months").format(
			said["booked"] * said["frequency"], said["months"] * said["frequency"]
		),
		"meter": {"value": said["booked"], "of": said["months"]},
	}


def next_depreciation(doc):
	if not _depreciating(doc):
		return None
	upcoming = _asset(doc.name)["next"]
	if not upcoming:
		return {"value": _("None left"), "tone": "quiet"}
	return {
		"label": _("Next Depreciation · {0}").format(formatdate(upcoming.schedule_date)),
		"value": _money(upcoming.depreciation_amount),
	}


def next_service(doc):
	"""Only equipment marked Maintenance Required has a service to be due."""
	service = _asset(doc.name)["service"]
	if not service:
		return {
			"value": _("No schedule"),
			"tone": "waiting",
			"route": f"/desk/asset-maintenance/new?asset_name={quote(doc.name)}",
		}
	return {
		"label": _("Next Due Date · {0}").format(formatdate(service.due_date)),
		"value": service.task_name,
		"tone": "alarm" if getdate(service.due_date) < getdate(today()) else None,
		"route": f"/desk/asset-maintenance-log/{quote(service.name)}",
	}


@request_cache
def _held(name: str) -> dict:
	"""What a warehouse holds, with the warehouses under it when it is a group,
	as the reader's Stock on Hand reads it (one_inventory/stock.py)."""
	from onedesk.one_inventory import stock

	lft, rgt = frappe.db.get_value("Warehouse", name, ["lft", "rgt"])
	under = frappe.get_all(
		"Warehouse", filters={"lft": [">=", lft], "rgt": ["<=", rgt], "is_group": 0}, pluck="name"
	)
	bins = frappe.get_list(
		"Bin",
		filters={"warehouse": ["in", under or [""]]},
		fields=[
			"item_code",
			"warehouse",
			"actual_qty",
			"reserved_qty",
			"reserved_stock",
			"ordered_qty",
			"projected_qty",
			"stock_value",
		],
		limit=0,
	)
	items = {
		one.name: dict(one)
		for one in frappe.get_all(
			"Item",
			filters={"name": ["in", list({one.item_code for one in bins}) or [""]]},
			fields=["name", "item_name", "item_group", "stock_uom"],
		)
	}
	levels = frappe.get_all(
		"Item Reorder",
		filters={
			"parenttype": "Item",
			"warehouse": ["in", under or [""]],
			"warehouse_reorder_level": [">", 0],
		},
		fields=["parent", "warehouse", "warehouse_reorder_level"],
	)
	listed = stock.rows([dict(one) for one in bins], levels, items)
	last = (
		frappe.get_list(
			"Stock Ledger Entry",
			filters={"warehouse": ["in", under or [""]], "is_cancelled": 0},
			fields=["posting_date"],
			order_by="posting_datetime desc",
			limit=1,
		)
		if frappe.has_permission("Stock Ledger Entry", "read")
		else []
	)
	return {
		"items": sum(1 for one in listed if one["on_hand"] > 0),
		"worth": sum(one["worth"] for one in listed),
		"low": sum(1 for one in listed if one["low_in"]),
		"last": last[0].posting_date if last else None,
	}


def warehouse_items(doc):
	return _held(doc.name)["items"]


def warehouse_worth(doc):
	return _money(_held(doc.name)["worth"])


def warehouse_low(doc):
	low = _held(doc.name)["low"]
	return {"value": low, "tone": "alarm" if low else "quiet"}


def warehouse_last(doc):
	last = _held(doc.name)["last"]
	return formatdate(last) if last else {"value": _("Never"), "tone": "quiet"}


@request_cache
def _left(name: str) -> list:
	return batches.left(name)


@request_cache
def _moves(name: str) -> list:
	return batches.moves(name)


def batch_left(doc):
	"""What is left of it, and where when it is in more than one warehouse."""
	places = _left(doc.name)
	total = sum(one["qty"] for one in places)
	if not places:
		return {"value": _("None left"), "tone": "quiet"}
	said = _count(doc, total)
	if len(places) == 1:
		called = frappe.get_cached_value("Warehouse", places[0]["warehouse"], "warehouse_name")
		return _("{0} in {1}").format(said, called or places[0]["warehouse"])
	return _("{0} in {1} warehouses").format(said, len(places))


def batch_expires(doc):
	"""Its expiry date, red once past with some left, amber within a month."""
	if not doc.expiry_date:
		return None
	tone = {"Expired": "alarm", "Expiring Soon": "waiting"}.get(
		batches.state(doc.expiry_date, sum(one["qty"] for one in _left(doc.name)))
	)
	return {"value": formatdate(doc.expiry_date), "tone": tone or "quiet"}


def batch_came_from(doc):
	"""The document that first brought it in."""
	moves = [one for one in _moves(doc.name) if one["qty"] > 0]
	if not moves:
		return None
	kind, name = moves[-1]["doctype"], moves[-1]["name"]
	return {
		"value": _("{0} {1}").format(_(kind), name),
		"route": f"/desk/{frappe.scrub(kind).replace('_', '-')}/{quote(name)}",
	}


def batch_went(doc):
	"""How many documents took some out, opening its trace."""
	out = {(one["doctype"], one["name"]) for one in _moves(doc.name) if one["qty"] < 0}
	return {"value": len(out), "tone": None if out else "quiet"}


def receipt_order(doc):
	"""The purchase orders the goods were ordered on."""
	orders = list(dict.fromkeys(row.purchase_order for row in doc.items if row.get("purchase_order")))
	if not orders:
		return {"value": _("Not ordered"), "tone": "quiet"}
	if len(orders) == 1:
		return {"value": orders[0], "route": f"/desk/purchase-order/{quote(orders[0])}"}
	return _("{0} orders").format(len(orders))


def receipt_worth(doc):
	"""What the goods put into stock, in the company's money: once received,
	at what each was valued (landed costs included); before, at its price. A
	service on it, such as a coater's work received for a subcontract, puts
	nothing into stock and counts at what it cost. A supplier in another
	currency is said beside it."""
	if doc.docstatus == 1:
		value = sum(
			flt(row.valuation_rate) * flt(row.stock_qty)
			if frappe.get_cached_value("Item", row.item_code, "is_stock_item")
			else flt(row.base_net_amount)
			for row in doc.items
		)
	else:
		value = flt(doc.base_net_total)
	company = frappe.get_cached_value("Company", doc.company, "default_currency")
	if doc.currency and doc.currency != company:
		return {
			"label": _("Stock Value · {0}").format(fmt_money(doc.net_total, currency=doc.currency)),
			"value": fmt_money(value, currency=company),
		}
	return fmt_money(value, currency=company)


def receipt_landed(doc):
	"""Freight, duty and the rest added to what the goods cost."""
	added = sum(flt(row.get("landed_cost_voucher_amount")) for row in doc.items)
	if not added:
		return None
	return fmt_money(added, currency=frappe.get_cached_value("Company", doc.company, "default_currency"))


def receipt_rejected(doc):
	rejected = sum(flt(row.rejected_qty) for row in doc.items)
	if not rejected:
		return None
	units = {row.uom for row in doc.items if flt(row.rejected_qty)}
	unit = _(units.pop()) if len(units) == 1 else ""
	return {"value": f"{fmt_money(rejected, precision=0)} {unit}".strip(), "tone": "alarm"}


def delivery_order(doc):
	"""The sales orders the goods were sold on."""
	orders = list(dict.fromkeys(row.against_sales_order for row in doc.items if row.get("against_sales_order")))
	if not orders:
		return {"value": _("Not ordered"), "tone": "quiet"}
	if len(orders) == 1:
		return {"value": orders[0], "route": f"/desk/sales-order/{quote(orders[0])}"}
	return _("{0} orders").format(len(orders))


def delivery_total(doc):
	"""In the customer's money, with the company's beside it when they differ."""
	company = frappe.get_cached_value("Company", doc.company, "default_currency")
	shown = fmt_money(doc.grand_total, currency=doc.currency)
	if doc.currency and doc.currency != company:
		return {"label": _("Grand Total · {0}").format(fmt_money(doc.base_grand_total, currency=company)), "value": shown}
	return shown


def delivery_trip(doc):
	"""The trip that takes the goods, when there is one: when it leaves and
	who drives."""
	stop = frappe.db.get_value(
		"Delivery Stop",
		{"delivery_note": doc.name, "docstatus": ["<", 2], "parenttype": "Delivery Trip"},
		"parent",
	)
	if not stop:
		return None
	trip = frappe.db.get_value("Delivery Trip", stop, ["name", "departure_time", "driver_name", "status"], as_dict=True)
	when = formatdate(trip.departure_time) if trip.departure_time else _(trip.status)
	return {
		"value": " · ".join(one for one in (when, trip.driver_name) if one),
		"route": f"/desk/delivery-trip/{quote(trip.name)}",
	}


def _company_money(doc) -> str:
	return frappe.get_cached_value("Company", doc.company, "default_currency")


def _total(doc):
	"""In the supplier's money, with the company's beside it when they differ."""
	company = _company_money(doc)
	shown = fmt_money(doc.grand_total, currency=doc.currency)
	if doc.currency and doc.currency != company:
		return {"label": _("Grand Total · {0}").format(fmt_money(doc.base_grand_total, currency=company)), "value": shown}
	return shown


def _wanted(day, done: bool):
	"""The day goods are wanted, said as late once it has passed and they are
	not all here."""
	if not day:
		return None
	if not done and getdate(day) < getdate(today()):
		return {"value": _("Late since {0}").format(formatdate(day)), "tone": "alarm"}
	return formatdate(day)


def request_asked_by(doc):
	return frappe.utils.get_fullname(doc.owner)


@request_cache
def _asked(rfq: str) -> list:
	return frappe.get_all("Request for Quotation Supplier", filters={"parent": rfq}, pluck="supplier")


@request_cache
def _quoted(rfq: str) -> dict:
	"""Each item's quoted rates on a request, in the company's money so a
	supplier in euros compares, {item_code: [(base_rate, supplier, quote)]},
	cheapest first."""
	rows = frappe.db.sql(
		"""select item.item_code, item.base_rate, quote.supplier, quote.name
		from `tabSupplier Quotation Item` item join `tabSupplier Quotation` quote on quote.name = item.parent
		where item.request_for_quotation = %s and quote.docstatus < 2 and quote.status != 'Expired'""",
		rfq,
	)
	out: dict = {}
	for code, rate, supplier, name in rows:
		out.setdefault(code, []).append((flt(rate), supplier, name))
	return {code: sorted(one) for code, one in out.items()}


def rfq_request(doc):
	requests = list(dict.fromkeys(row.material_request for row in doc.items if row.get("material_request")))
	if not requests:
		return None
	if len(requests) == 1:
		return {"value": requests[0], "route": f"/desk/material-request/{quote(requests[0])}"}
	return _("{0} requests").format(len(requests))


def rfq_answered(doc):
	if doc.docstatus != 1:
		return None
	answered = {supplier for lines in _quoted(doc.name).values() for _rate, supplier, _name in lines}
	asked = _asked(doc.name)
	return {"value": _("{0} of {1}").format(len(answered), len(asked)), "tone": None if answered else "waiting"}


def rfq_cheapest(doc):
	"""Who is cheapest, line by line: one supplier, or how many share the
	lines. Opens the comparison."""
	quoted = _quoted(doc.name)
	if not quoted:
		return None
	best = {lines[0][1] for lines in quoted.values()}
	value = best.pop() if len(best) == 1 else _("Split between {0}").format(len(best))
	return {
		"value": value,
		"route": "/desk/query-report/Supplier Quotation Comparison?"
		+ f"request_for_quotation={quote(doc.name)}&from_date={doc.transaction_date}",
	}


def quote_request(doc):
	asked = list(dict.fromkeys(row.request_for_quotation for row in doc.items if row.get("request_for_quotation")))
	if not asked:
		return None
	return {"value": asked[0], "route": f"/desk/request-for-quotation/{quote(asked[0])}"}


def quote_valid(doc):
	if not doc.valid_till:
		return None
	if doc.status == "Expired" or getdate(doc.valid_till) < getdate(today()):
		return {"value": _("Expired {0}").format(formatdate(doc.valid_till)), "tone": "quiet"}
	return formatdate(doc.valid_till)


def quote_cheapest(doc):
	"""On how many of its lines the quote is the cheapest of those sent for
	the same request."""
	asked = next((row.request_for_quotation for row in doc.items if row.get("request_for_quotation")), None)
	if not asked:
		return None
	quoted = _quoted(asked)
	codes = list(dict.fromkeys(row.item_code for row in doc.items))
	if sum(len(quoted.get(code) or ()) for code in codes) <= len(codes):
		return None
	best = sum(1 for code in codes if quoted.get(code) and quoted[code][0][2] == doc.name)
	return {"value": _("{0} of {1} lines").format(best, len(codes)), "tone": None if best else "quiet"}


def quote_ordered(doc):
	orders = frappe.get_all(
		"Purchase Order Item",
		filters={"supplier_quotation": doc.name, "docstatus": ["<", 2]},
		pluck="parent",
		distinct=True,
	)
	if not orders:
		return None
	if len(orders) == 1:
		return {"value": orders[0], "route": f"/desk/purchase-order/{quote(orders[0])}"}
	return _("{0} orders").format(len(orders))


def order_total(doc):
	return _total(doc)


def _paid(doc) -> float:
	"""What has been paid on an order: what was paid ahead, and what its
	submitted bills no longer owe."""
	bills = frappe.get_all(
		"Purchase Invoice Item",
		filters={"purchase_order": doc.name, "docstatus": 1},
		pluck="parent",
		distinct=True,
	)
	paid = flt(doc.advance_paid)
	for bill in frappe.get_all(
		"Purchase Invoice", filters={"name": ["in", bills or [""]]}, fields=["grand_total", "outstanding_amount"]
	):
		paid += flt(bill.grand_total) - flt(bill.outstanding_amount)
	return min(paid, flt(doc.grand_total))


def order_progress(doc):
	"""Ordered, received, billed, paid."""
	if doc.docstatus != 1:
		return None
	money = lambda value: fmt_money(value, currency=doc.currency)  # noqa: E731
	lines = list(doc.items)
	arrived = sum(1 for row in lines if flt(row.received_qty) >= flt(row.qty))
	received = flt(doc.per_received) >= 100
	billed = flt(doc.per_billed) >= 100
	paid = _paid(doc)
	total = flt(doc.grand_total)
	settled = paid >= total - 0.005
	waiting = [row.schedule_date for row in lines if flt(row.received_qty) < flt(row.qty)]
	late = bool(waiting) and bool(stages.overdue(min(waiting))) and doc.status not in ("Closed", "On Hold")
	return stages.track(
		stages.step(_("Ordered"), "done", formatdate(doc.transaction_date)),
		stages.step(
			_("Received"),
			stages.at(received, True, late),
			_("All in")
			if received
			else _("{0} of {1} lines in").format(arrived, len(lines))
			if arrived
			else _("Late since {0}").format(formatdate(min(waiting)))
			if late
			else _("Due {0}").format(formatdate(min(waiting))),
		),
		stages.step(_("Billed"), stages.at(billed, received or flt(doc.per_billed)), money(total) if billed else stages.share(doc.per_billed)),
		stages.step(
			_("Paid"),
			stages.at(settled, billed or paid),
			_("In full") if settled else _("{0} left").format(money(total - paid)) if billed or paid else "",
		),
		stopped=doc.status in ("Closed", "On Hold"),
	)


def order_said(doc):
	supplier = doc.supplier_name or doc.supplier
	if said := stages.draft(doc, _("A draft. Submit it to order from {0}.").format(supplier)):
		return said
	if doc.status in ("Closed", "On Hold"):
		return {"text": _("{0}; nothing more is expected on it.").format(_(doc.status)), "colour": "gray"}
	waiting = [row.schedule_date for row in doc.items if flt(row.received_qty) < flt(row.qty)]
	if waiting:
		day = min(waiting)
		if (days := stages.overdue(day)) and not flt(doc.per_received):
			return {"text": _("Nothing has come from {0}, and it was wanted {1} ago.").format(supplier, stages.days(days)), "colour": "red"}
		if days:
			return {"text": _("Part has come from {0}; the rest was wanted {1} ago.").format(supplier, stages.days(days)), "colour": "red"}
		return {"text": _("Waiting for {0}; wanted by {1}.").format(supplier, formatdate(day)), "colour": "blue"}
	if flt(doc.per_billed) < 100:
		return {"text": _("Everything is in; the bill from {0} is still to come.").format(supplier), "colour": "orange"}
	paid = _paid(doc)
	if paid < flt(doc.grand_total) - 0.005:
		left = fmt_money(flt(doc.grand_total) - paid, currency=doc.currency)
		return {"text": _("Received and billed; {0} is still to pay.").format(left), "colour": "orange"}
	return {"text": _("Received, billed and paid."), "colour": "green"}


def _request_quotes(doc) -> tuple[int, int]:
	"""How many suppliers were asked to quote for it, and how many did."""
	asked = frappe.get_all(
		"Request for Quotation Item",
		filters={"material_request": doc.name, "docstatus": ["<", 2]},
		pluck="parent",
		distinct=True,
	)
	if not asked:
		return 0, 0
	quotes = frappe.get_all(
		"Supplier Quotation Item",
		filters={"request_for_quotation": ["in", asked], "docstatus": ["<", 2]},
		pluck="parent",
		distinct=True,
	)
	return sum(len(_asked(one)) for one in asked), len(quotes)


def request_progress(doc):
	"""Asked, then quoted, ordered and received when it is to buy; moved,
	issued or made for the rest."""
	if doc.docstatus != 1:
		return None
	kind = doc.material_request_type
	done = flt(doc.per_ordered) >= 100
	late = bool(stages.overdue(doc.schedule_date))
	asked = stages.step(_("Requested"), "done", formatdate(doc.transaction_date))
	if kind == "Purchase":
		suppliers, quotes = _request_quotes(doc)
		received = flt(doc.per_received) >= 100
		return stages.track(
			asked,
			suppliers
			and stages.step(
				_("Quoted"),
				stages.at(quotes >= suppliers or flt(doc.per_ordered), True),
				_("{0} of {1} answered").format(quotes, suppliers),
			),
			stages.step(_("Ordered"), stages.at(done, True, late and not flt(doc.per_ordered)), _("All") if done else stages.share(doc.per_ordered)),
			stages.step(_("Received"), stages.at(received, flt(doc.per_ordered), late and done), _("All in") if received else stages.share(doc.per_received)),
		stopped=doc.status == "Stopped",
	)
	if kind == "Manufacture":
		made = flt(doc.per_received) >= 100
		return stages.track(
			asked,
			stages.step(_("Work Order"), stages.at(done, True), _("All") if done else stages.share(doc.per_ordered)),
			stages.step(_("Manufactured"), stages.at(made, flt(doc.per_ordered), late), _("All") if made else stages.share(doc.per_received)),
		stopped=doc.status == "Stopped",
	)
	if kind == "Customer Provided":
		return stages.track(asked, stages.step(_("Received"), stages.at(done, True, late), _("All in") if done else stages.share(doc.per_ordered)), stopped=doc.status == "Stopped")
	moved = _("Issued") if kind == "Material Issue" else _("Moved")
	return stages.track(asked, stages.step(moved, stages.at(done, True, late), _("All") if done else stages.share(doc.per_ordered)), stopped=doc.status == "Stopped")


def request_said(doc):
	if said := stages.draft(doc, _("A draft. Submit it to ask for these.")):
		return said
	if doc.status in ("Stopped", "Cancelled"):
		return {"text": _("Stopped; nothing more will be done on it."), "colour": "gray"}
	kind = doc.material_request_type
	days = stages.overdue(doc.schedule_date)
	ordered, received = flt(doc.per_ordered), flt(doc.per_received)
	if kind == "Purchase":
		if received >= 100:
			return {"text": _("Ordered and received."), "colour": "green"}
		if ordered >= 100:
			if days:
				return {"text": _("Ordered, but the goods were wanted {0} ago.").format(stages.days(days)), "colour": "red"}
			return {"text": _("Ordered; waiting for the goods."), "colour": "blue"}
		if days:
			return {"text": _("Not all ordered yet, and it was wanted {0} ago.").format(stages.days(days)), "colour": "red"}
		suppliers, quotes = _request_quotes(doc)
		if ordered:
			return {"text": _("Part is ordered; the rest is still to order."), "colour": "orange"}
		if quotes:
			return {"text": _("{0} of {1} suppliers have quoted. Order from the best.").format(quotes, suppliers), "colour": "orange"}
		if suppliers:
			return {"text": _("Waiting for {0} suppliers to quote.").format(suppliers), "colour": "blue"}
		return {"text": _("Nothing ordered yet. Ask for quotes or order it."), "colour": "orange"}
	if kind == "Manufacture":
		if received >= 100:
			return {"text": _("Made."), "colour": "green"}
		if ordered:
			return {"text": _("Being made."), "colour": "red" if days else "blue"}
		return {"text": _("No work order yet. Make one to start."), "colour": "red" if days else "orange"}
	if ordered >= 100:
		return {"text": _("Done."), "colour": "green"}
	if days:
		return {"text": _("Not done yet, and it was wanted {0} ago.").format(stages.days(days)), "colour": "red"}
	return {"text": _("Wanted by {0}.").format(formatdate(doc.schedule_date)), "colour": "blue"}


def rfq_stands(doc):
	"""A request for prices: green once every supplier asked has quoted."""
	if said := stages.draft(doc, ""):
		return said
	answered = {supplier for lines in _quoted(doc.name).values() for _rate, supplier, _name in lines}
	asked = _asked(doc.name)
	return {"colour": "green" if asked and len(answered) >= len(asked) else "blue"}


STANDS = {
	"Purchase Order": "order_said",
	"Material Request": "request_said",
	"Purchase Receipt": "receipt_said",
	"Request for Quotation": "rfq_stands",
}


def stands(doc) -> str | None:
	"""The colour of a buying document's head's sentence, so a project's
	Buying draws its ERPNext status as urgent as the document says it is."""
	said = STANDS.get(doc.doctype)
	said = globals()[said](doc) if said else None
	return said["colour"] if said else None


def _ordered_on(doctype: str, names) -> str:
	names = list(dict.fromkeys(one for one in names if one))
	if len(names) != 1:
		return _("{0} orders").format(len(names)) if names else ""
	return formatdate(frappe.db.get_value(doctype, names[0], "transaction_date"))


def receipt_progress(doc):
	"""Ordered (when it was), received, billed."""
	if doc.docstatus != 1 or doc.is_return:
		return None
	orders = [row.purchase_order for row in doc.items if row.get("purchase_order")]
	billed = flt(doc.per_billed) >= 100
	return stages.track(
		orders and stages.step(_("Ordered"), "done", _ordered_on("Purchase Order", orders)),
		stages.step(_("Received"), "done", formatdate(doc.posting_date)),
		stages.step(_("Billed"), stages.at(billed, True), _("All") if billed else stages.share(doc.per_billed)),
	)


def receipt_said(doc):
	supplier = doc.supplier_name or doc.supplier
	if said := stages.draft(doc, _("A draft. Submit it to put these into stock.")):
		return said
	if doc.is_return:
		return {"text": _("Goods sent back to {0}.").format(supplier), "colour": "gray"}
	if any(flt(row.rejected_qty) for row in doc.items):
		return {"text": _("Some were rejected. Send them back to {0}.").format(supplier), "colour": "red"}
	if flt(doc.per_billed) < 100:
		return {"text": _("In stock; the bill from {0} is still to come.").format(supplier), "colour": "orange"}
	return {"text": _("In stock and billed."), "colour": "green"}


def delivery_progress(doc):
	"""Ordered (when it was), delivered, billed."""
	if doc.docstatus != 1 or doc.is_return:
		return None
	orders = [row.against_sales_order for row in doc.items if row.get("against_sales_order")]
	billed = flt(doc.per_billed) >= 100
	return stages.track(
		orders and stages.step(_("Ordered"), "done", _ordered_on("Sales Order", orders)),
		stages.step(_("Delivered"), "done", formatdate(doc.posting_date)),
		stages.step(_("Billed"), stages.at(billed, True), _("All") if billed else stages.share(doc.per_billed)),
	)


def delivery_said(doc):
	customer = doc.customer_name or doc.customer
	if said := stages.draft(doc, _("A draft. Submit it to take these out of stock for {0}.").format(customer)):
		return said
	if doc.is_return:
		return {"text": _("Goods {0} sent back.").format(customer), "colour": "gray"}
	if flt(doc.per_returned):
		return {"text": _("{0}% of it came back.").format(round(flt(doc.per_returned))), "colour": "orange"}
	if flt(doc.per_billed) < 100:
		return {"text": _("Delivered to {0}; not billed yet.").format(customer), "colour": "orange"}
	return {"text": _("Delivered and billed."), "colour": "green"}


def asset_said(doc):
	if said := stages.draft(doc, _("A draft. Submit it to put it in use.")):
		return said
	if doc.status in ("Sold", "Scrapped"):
		day = doc.get("disposal_date")
		said = _("Sold on {0}.") if doc.status == "Sold" else _("Scrapped on {0}.")
		return {"text": said.format(formatdate(day)) if day else _(doc.status), "colour": "gray"}
	if doc.status in ("Out of Order", "In Maintenance"):
		if doc.status == "In Maintenance":
			return {"text": _("Being serviced."), "colour": "orange"}
		return {"text": _("Out of order; it cannot be used until it is mended."), "colour": "red"}
	service = _asset(doc.name)["service"]
	if service and (days := stages.overdue(service.due_date)):
		return {"text": _("{0} was due {1} ago.").format(service.task_name, stages.days(days)), "colour": "red"}
	holder = _asset(doc.name)["custodian_name"] or doc.custodian
	where = doc.location
	if doc.status == "Fully Depreciated":
		said = _("Written off to nothing, and still in use.")
	elif holder and where:
		said = _("In use by {0}, at {1}.").format(holder, where)
	elif holder:
		said = _("In use by {0}.").format(holder)
	elif where:
		said = _("At {0}; nobody has it.").format(where)
	else:
		said = _("In use.")
	return {"text": said, "colour": "gray" if doc.status == "Fully Depreciated" else "green"}


def order_blanket(doc):
	agreed = list(dict.fromkeys(row.blanket_order for row in doc.items if row.get("blanket_order")))
	if not agreed:
		return None
	return {"value": agreed[0], "route": f"/desk/blanket-order/{quote(agreed[0])}"}


def blanket_party(doc):
	if doc.blanket_order_type == "Purchasing":
		name = doc.supplier_name or doc.supplier
		return {"value": name, "route": f"/desk/supplier/{quote(doc.supplier)}"} if doc.supplier else None
	name = doc.customer_name or doc.customer
	return {"value": name, "route": f"/desk/customer/{quote(doc.customer)}"} if doc.customer else None


def blanket_runs(doc):
	if not doc.from_date or not doc.to_date:
		return None
	said = _("{0} to {1}").format(formatdate(doc.from_date), formatdate(doc.to_date))
	if getdate(doc.to_date) < getdate(today()):
		return {"value": said, "tone": "quiet"}
	return said


def blanket_ordered(doc):
	"""How much of what was agreed has been ordered on it."""
	agreed = sum(flt(row.qty) for row in doc.items)
	ordered = sum(flt(row.ordered_qty) for row in doc.items)
	if not agreed:
		return None
	units = {row.get("stock_uom") or frappe.get_cached_value("Item", row.item_code, "stock_uom") for row in doc.items}
	unit = _(units.pop()) if len(units) == 1 else ""
	return {
		"value": f"{fmt_money(ordered, precision=0)} {unit}".strip(),
		"meter": {"value": ordered, "of": agreed},
	}


def blanket_orders(doc):
	kind = "Purchase Order" if doc.blanket_order_type == "Purchasing" else "Sales Order"
	made = frappe.get_all(
		f"{kind} Item", filters={"blanket_order": doc.name, "docstatus": 1}, pluck="parent", distinct=True
	)
	return {"value": str(len(made)), "tone": None if made else "quiet"}


MADE = ("Manufacture", "Repack", "Disassemble")


def _places(names) -> dict | None:
	"""Warehouses by their own names, one opening its stock."""
	names = list(dict.fromkeys(one for one in names if one))
	if not names:
		return None
	if len(names) > 1:
		return {"value": _("{0} warehouses").format(len(names))}
	called = frappe.get_cached_value("Warehouse", names[0], "warehouse_name") or names[0]
	return {"value": called, "route": f"/desk/stock-on-hand?warehouse={quote(names[0])}"}


def move_from(doc):
	return _places(row.s_warehouse for row in doc.items)


def move_to(doc):
	return _places(row.t_warehouse for row in doc.items)


def move_value(doc):
	"""What the movement is worth: what went in for goods received or made,
	what went out for the rest. A transfer's two are the same."""
	if doc.purpose in MADE or doc.purpose == "Material Receipt":
		value = doc.total_incoming_value
	else:
		value = doc.total_outgoing_value
	return _money(value) if flt(value) else None


def move_used(doc):
	"""What making the goods used up."""
	if doc.purpose not in MADE or not flt(doc.total_outgoing_value):
		return None
	return _money(doc.total_outgoing_value)


def count_items(doc):
	"""ERPNext keeps only the lines a count changed, so each one is a difference."""
	return str(len(doc.items))


def count_where(doc):
	return _places(row.warehouse for row in doc.items)


def _of(made, wanted, unit) -> dict:
	"""So many of so many, with a meter."""
	said = _("{0} of {1}").format(fmt_money(flt(made), precision=0), fmt_money(flt(wanted), precision=0))
	return {"value": f"{said} {_(unit or '')}".strip(), "meter": {"value": flt(made), "of": flt(wanted)}}


def _equipment(name: str) -> dict | None:
	"""An asset by its own name, opening it."""
	if not name:
		return None
	called = frappe.db.get_value("Asset", name, "asset_name") or name
	return {"value": called, "route": f"/desk/asset/{quote(name)}"}


def _people(names) -> dict | None:
	"""Employees by their names, one opening their page."""
	names = list(dict.fromkeys(one for one in names if one))
	if not names:
		return None
	if len(names) > 1:
		return {"value": _("{0} people").format(len(names))}
	called = frappe.db.get_value("Employee", names[0], "employee_name") or names[0]
	return {"value": called, "route": f"/desk/employee/{quote(names[0])}"}


def _locations(names) -> dict | None:
	names = list(dict.fromkeys(one for one in names if one))
	if not names:
		return None
	return {"value": names[0] if len(names) == 1 else _("{0} places").format(len(names))}


def handed_what(doc):
	"""What moved: one asset by its name, or how many."""
	names = list(dict.fromkeys(row.asset for row in doc.assets if row.asset))
	if len(names) > 1:
		return {"value": _("{0} assets").format(len(names))}
	return _equipment(names[0]) if names else None


def handed_to(doc):
	"""Whoever has it now, or where it is kept."""
	return _people(row.to_employee for row in doc.assets) or _locations(row.target_location for row in doc.assets)


def handed_from(doc):
	return _people(row.from_employee for row in doc.assets) or _locations(row.source_location for row in doc.assets)


def service_asset(doc):
	"""The asset a service or schedule is for. A log names it by its schedule,
	and a schedule is named after its asset."""
	return _equipment(doc.get("asset_name") or doc.get("asset_maintenance"))


def service_due(doc):
	"""When it is due, in red once it is late and not done."""
	if not doc.due_date:
		return None
	late = doc.maintenance_status in ("Planned", "Overdue") and getdate(doc.due_date) < getdate(today())
	return {"value": formatdate(doc.due_date), "tone": "alarm" if late else None}


def service_last(doc):
	"""When the task was last done."""
	last = frappe.db.get_value("Asset Maintenance Task", doc.task, "last_completion_date") if doc.task else None
	return formatdate(last) if last else {"value": _("Never"), "tone": "quiet"}


def schedule_next(doc):
	"""The earliest service still to do on the schedule's asset."""
	from onedesk.one_inventory.maintenance import next_service as earliest

	found = earliest(doc.asset_name)
	if not found:
		return {"value": _("Nothing due"), "tone": "quiet"}
	late = getdate(found.due_date) < getdate(today())
	return {
		"label": _("Next Due Date · {0}").format(formatdate(found.due_date)),
		"value": found.task_name,
		"tone": "alarm" if late else None,
		"route": f"/desk/asset-maintenance-log/{quote(found.name)}",
	}


def repair_asset(doc):
	return _equipment(doc.asset)


def repair_out(doc):
	"""How long the asset was out of use: from when it failed to when it was
	mended, or to today while it is not."""
	if not doc.failure_date:
		return None
	end = doc.completion_date if doc.repair_status == "Completed" and doc.completion_date else today()
	days = max((getdate(end) - getdate(doc.failure_date)).days, 0)
	value = _("1 day") if days == 1 else _("{0} days").format(days)
	return {"value": value, "tone": "alarm" if doc.repair_status == "Pending" else None}


def repair_cost(doc):
	value = flt(doc.total_repair_cost) or flt(doc.repair_cost)
	return _money(value) if value else {"value": _("Nothing yet"), "tone": "quiet"}


def worth_change(doc):
	"""What the asset was worth, what it is worth now, and the change."""
	change = flt(doc.new_asset_value) - flt(doc.current_asset_value)
	if not flt(doc.current_asset_value):
		return None
	return {"value": _money(change), "tone": "alarm" if change < 0 else None}


def moved(doc):
	"""What went out of stock each month for a year: sold, used or sent on.
	Read from the stock ledger as the reader's list of it would give it."""
	if not doc.is_stock_item or not frappe.has_permission("Stock Ledger Entry", "read"):
		return None
	day = getdate(today())
	starts = figures.months(day)
	rows = frappe.get_list(
		"Stock Ledger Entry",
		filters={
			"item_code": doc.name,
			"is_cancelled": 0,
			"actual_qty": ["<", 0],
			"posting_date": [">=", starts[0]],
		},
		fields=["posting_date", "actual_qty"],
		limit_page_length=0,
	)
	values = figures.by_month(((getdate(row.posting_date), -flt(row.actual_qty)) for row in rows), day)
	return {
		"labels": [formatdate(one, "MMM") for one in starts],
		"values": values,
		"said": _("{0} in 12 months").format(_count(doc, sum(values))),
		"route": f"/desk/query-report/Stock Ledger?item_code={quote(doc.name)}",
	}


def life(doc):
	"""What the asset is worth after each depreciation, from what it cost to
	what it will be worth at the end, as its own schedule books it."""
	if not _depreciating(doc):
		return None
	schedule = frappe.db.get_value("Asset Depreciation Schedule", {"asset": doc.name, "docstatus": 1}, "name")
	if not schedule:
		return None
	rows = frappe.get_all(
		"Depreciation Schedule",
		filters={"parent": schedule},
		fields=["schedule_date", "accumulated_depreciation_amount"],
		order_by="schedule_date asc",
	)
	if not rows:
		return None
	cost = flt(_asset(doc.name)["cost"])
	start = getdate(doc.available_for_use_date or rows[0].schedule_date)
	points = [(start, cost)] + [
		(getdate(row.schedule_date), cost - flt(row.accumulated_depreciation_amount)) for row in rows
	]
	return {
		"kind": "line",
		"labels": [formatdate(day, "MMM yyyy") for day, _value in points],
		"values": [value for _day, value in points],
		"currency": frappe.db.get_default("currency"),
		"said": _("{0} at the end").format(_money(points[-1][1])),
	}


CHARTS = {
	"item.moved": {"doctypes": ["Item"], "label": _lt("Out of Stock, Month by Month"), "figures": moved},
	"asset.life": {"doctypes": ["Asset"], "label": _lt("Value After Depreciation"), "figures": life},
}


MEASURES = {
	"item.on_hand": on_hand,
	"item.free": free,
	"item.on_order": on_order,
	"item.worth": worth,
	"item.reorder": reorder,
	"item.last_bought": last_bought,
	"asset.worth_now": worth_now,
	"asset.cost": cost,
	"asset.depreciation": depreciation,
	"asset.written_off": written_off,
	"asset.next_depreciation": next_depreciation,
	"asset.next_service": next_service,
	"batch.left": batch_left,
	"batch.expires": batch_expires,
	"batch.came_from": batch_came_from,
	"batch.went": batch_went,
	"warehouse.items": warehouse_items,
	"warehouse.worth": warehouse_worth,
	"warehouse.low": warehouse_low,
	"warehouse.last": warehouse_last,
	"receipt.order": receipt_order,
	"receipt.worth": receipt_worth,
	"receipt.landed": receipt_landed,
	"receipt.rejected": receipt_rejected,
	"delivery.order": delivery_order,
	"delivery.total": delivery_total,
	"delivery.trip": delivery_trip,
	"move.from": move_from,
	"move.to": move_to,
	"move.value": move_value,
	"move.used": move_used,
	"count.items": count_items,
	"count.where": count_where,
	"request.asked_by": request_asked_by,
	"rfq.request": rfq_request,
	"rfq.answered": rfq_answered,
	"rfq.cheapest": rfq_cheapest,
	"quote.request": quote_request,
	"quote.valid": quote_valid,
	"quote.cheapest": quote_cheapest,
	"quote.ordered": quote_ordered,
	"order.total": order_total,
	"order.progress": order_progress,
	"order.said": order_said,
	"material.progress": request_progress,
	"material.said": request_said,
	"receipt.progress": receipt_progress,
	"receipt.said": receipt_said,
	"delivery.progress": delivery_progress,
	"delivery.said": delivery_said,
	"asset.said": asset_said,
	"order.blanket": order_blanket,
	"blanket.party": blanket_party,
	"blanket.runs": blanket_runs,
	"blanket.ordered": blanket_ordered,
	"blanket.orders": blanket_orders,
	"handover.what": handed_what,
	"handover.to": handed_to,
	"handover.from": handed_from,
	"service.asset": service_asset,
	"service.due": service_due,
	"service.last": service_last,
	"schedule.next": schedule_next,
	"repair.asset": repair_asset,
	"repair.out": repair_out,
	"repair.cost": repair_cost,
	"adjustment.change": worth_change,
}


def _movable(doc) -> bool:
	"""A sold or scrapped asset is nobody's to give."""
	return (
		doc.docstatus == 1
		and doc.status not in ("Sold", "Scrapped")
		and frappe.has_permission("Asset Movement", "create")
	)


VERBS = {
	"asset.give": {
		"doctypes": ["Asset"],
		"label": lambda doc: _("Hand To…") if doc.custodian else _("Give To…"),
		"title": lambda doc: _("Hand To Somebody Else") if doc.custodian else _("Give To"),
		"action": _lt("Give"),
		"when": _movable,
		"fields": lambda doc: [
			{
				"fieldtype": "Link",
				"fieldname": "employee",
				"label": _("Employee"),
				"options": "Employee",
				"reqd": 1,
				"filters": {"status": "Active"},
			}
		],
		"run": lambda doc, employee: custody.give(doc.name, employee) and _("Given."),
	},
	"asset.take_back": {
		"doctypes": ["Asset"],
		"label": _lt("Take Back"),
		"action": _lt("Take Back"),
		"when": lambda doc: _movable(doc) and bool(doc.custodian),
		"fields": lambda doc: [
			{
				"fieldtype": "Link",
				"fieldname": "location",
				"label": _("Kept At"),
				"options": "Location",
				"reqd": 1,
				"default": doc.location,
			}
		],
		"run": lambda doc, location: custody.take_back(doc.name, location) and _("Taken back."),
	},
}


HEADS = [
	{
		"doctype": "Item",
		"band": [
			{
				"label": _lt("Asset"),
				"source": "Count",
				"of_doctype": "Asset",
				"filters": [["item_code", "=", "{{ doc.name }}"], ["docstatus", "<", 2]],
				"shown_when": FIXED,
				"route": "/desk/asset?item_code={{ doc.name }}",
			},
			{
				"label": _lt("Draft Assets"),
				"source": "Count",
				"of_doctype": "Asset",
				"filters": [["item_code", "=", "{{ doc.name }}"], ["docstatus", "=", 0]],
				"shown_when": FIXED,
				"route": "/desk/asset?item_code={{ doc.name }}&docstatus=0",
				"tone": "waiting",
				"hide_empty": 1,
			},
			{
				"label": _lt("Actual Qty"),
				"source": "Measure",
				"measure": "item.on_hand",
				"shown_when": STOCK,
				"route": "/desk/query-report/Stock Balance?item_code={{ doc.name }}",
			},
			{"label": _lt("Available Qty"), "source": "Measure", "measure": "item.free", "shown_when": STOCK},
			{
				"label": _lt("Ordered Qty"),
				"source": "Measure",
				"measure": "item.on_order",
				"shown_when": STOCK,
				"route": '/desk/purchase-order?item_code={{ doc.name }}&docstatus=1&status=["not in",["Completed","Closed"]]',
			},
			{"label": _lt("Stock Value"), "source": "Measure", "measure": "item.worth", "shown_when": STOCK},
			{"label": _lt("Reorder Level"), "source": "Measure", "measure": "item.reorder", "shown_when": STOCK},
			{
				"label": _lt("Last Purchase Rate"),
				"source": "Measure",
				"measure": "item.last_bought",
				"shown_when": [["is_fixed_asset", "=", 0]],
			},
		],
		"charts": [{"chart": "item.moved", "shown_when": STOCK}],
	},
	{
		"doctype": "Asset",
		"sentences": [{"measure": "asset.said"}],
		"band": [
			{"label": _lt("Value After Depreciation"), "source": "Measure", "measure": "asset.worth_now"},
			{"label": _lt("Net Purchase Amount"), "source": "Measure", "measure": "asset.cost"},
			{"label": _lt("Depreciation"), "source": "Measure", "measure": "asset.depreciation"},
			{"label": _lt("Depreciations Booked"), "source": "Measure", "measure": "asset.written_off"},
			{"label": _lt("Next Depreciation"), "source": "Measure", "measure": "asset.next_depreciation"},
			{
				"label": _lt("Next Due Date"),
				"source": "Measure",
				"measure": "asset.next_service",
				"shown_when": [["maintenance_required", "=", 1]],
			},
			{
				"label": _lt("Asset Repair"),
				"source": "Count",
				"of_doctype": "Asset Repair",
				"filters": [["asset", "=", "{{ doc.name }}"], ["docstatus", "<", 2]],
				"shown_when": SUBMITTED,
				"route": "/desk/asset-repair?asset={{ doc.name }}",
				"hide_empty": 1,
			},
		],
		"verbs": [{"verb": "asset.give"}, {"verb": "asset.take_back"}],
		"charts": [{"chart": "asset.life", "shown_when": SUBMITTED}],
	},
	{
		"doctype": "Batch",
		"band": [
			{
				"label": _lt("Batch Quantity"),
				"source": "Measure",
				"measure": "batch.left",
				"route": "/desk/query-report/Batch-Wise Balance History?item_code={{ doc.item }}&batch_no={{ doc.name }}",
			},
			{"label": _lt("Manufacturing Date"), "source": "Field", "field": "manufacturing_date", "hide_empty": 1},
			{"label": _lt("Expiry Date"), "source": "Measure", "measure": "batch.expires"},
			{"label": _lt("Source Document"), "source": "Measure", "measure": "batch.came_from"},
			{
				"label": _lt("Issued"),
				"source": "Measure",
				"measure": "batch.went",
				"route": "/desk/query-report/Serial No and Batch Traceability?batches={{ doc.name }}",
			},
		],
	},
	{
		"doctype": "Warehouse",
		"band": [
			{
				"label": _lt("Items"),
				"source": "Measure",
				"measure": "warehouse.items",
				"route": "/desk/stock-on-hand?warehouse={{ doc.name }}",
			},
			{"label": _lt("Stock Value"), "source": "Measure", "measure": "warehouse.worth"},
			{
				"label": _lt("Below Reorder Level"),
				"source": "Measure",
				"measure": "warehouse.low",
				"route": "/desk/stock-on-hand?warehouse={{ doc.name }}",
			},
			{
				"label": _lt("Last Stock Entry"),
				"source": "Measure",
				"measure": "warehouse.last",
				"route": "/desk/query-report/Stock Ledger?warehouse={{ doc.name }}",
			},
		],
	},
	{
		"doctype": "Purchase Order",
		"sentences": [{"measure": "order.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "order.progress"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Grand Total"), "source": "Measure", "measure": "order.total", "shown_when": [["docstatus", "=", 0]]},
			{"label": _lt("Blanket Order"), "source": "Measure", "measure": "order.blanket"},
		],
	},
	{
		"doctype": "Material Request",
		"sentences": [{"measure": "material.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "material.progress"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Requested By"), "source": "Measure", "measure": "request.asked_by"},
		],
	},
	{
		"doctype": "Request for Quotation",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Material Request"), "source": "Measure", "measure": "rfq.request"},
			{"label": _lt("Quoted"), "source": "Measure", "measure": "rfq.answered"},
			{"label": _lt("Cheapest"), "source": "Measure", "measure": "rfq.cheapest"},
		],
	},
	{
		"doctype": "Supplier Quotation",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Request for Quotation"), "source": "Measure", "measure": "quote.request"},
			{"label": _lt("Grand Total"), "source": "Measure", "measure": "order.total"},
			{"label": _lt("Valid Till"), "source": "Measure", "measure": "quote.valid"},
			{"label": _lt("Lowest On"), "source": "Measure", "measure": "quote.cheapest"},
			{"label": _lt("Purchase Order"), "source": "Measure", "measure": "quote.ordered"},
		],
	},
	{
		"doctype": "Blanket Order",
		"band": [
			{"label": _lt("Party"), "source": "Measure", "measure": "blanket.party"},
			{"label": _lt("Validity"), "source": "Measure", "measure": "blanket.runs"},
			{"label": _lt("Ordered Qty"), "source": "Measure", "measure": "blanket.ordered"},
			{"label": _lt("Purchase Order"), "source": "Measure", "measure": "blanket.orders", "shown_when": SUBMITTED},
		],
	},
	{
		"doctype": "Purchase Receipt",
		"sentences": [{"measure": "receipt.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "receipt.progress"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Purchase Order"), "source": "Measure", "measure": "receipt.order"},
			{"label": _lt("Stock Value"), "source": "Measure", "measure": "receipt.worth"},
			{"label": _lt("Landed Cost Voucher"), "source": "Measure", "measure": "receipt.landed"},
			{"label": _lt("Rejected Qty"), "source": "Measure", "measure": "receipt.rejected"},
		],
	},
	{
		"doctype": "Delivery Note",
		"sentences": [{"measure": "delivery.said"}],
		"band": [
			{"label": _lt("Progress"), "source": "Measure", "measure": "delivery.progress"},
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Sales Order"), "source": "Measure", "measure": "delivery.order"},
			{"label": _lt("Grand Total"), "source": "Measure", "measure": "delivery.total"},
			{"label": _lt("Delivery Trip"), "source": "Measure", "measure": "delivery.trip"},
		],
	},
	{
		"doctype": "Stock Entry",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Stock Entry Type"), "source": "Field", "field": "stock_entry_type"},
			{"label": _lt("Default Source Warehouse"), "source": "Measure", "measure": "move.from"},
			{"label": _lt("Default Target Warehouse"), "source": "Measure", "measure": "move.to"},
			{"label": _lt("Total Value"), "source": "Measure", "measure": "move.value"},
			{"label": _lt("Total Outgoing Value"), "source": "Measure", "measure": "move.used"},
			{
				"label": _lt("% Transferred"),
				"source": "Field",
				"field": "per_transferred",
				"shown_when": [["add_to_transit", "=", 1], ["docstatus", "=", 1]],
			},
		],
	},

	{
		"doctype": "Asset Movement",
		"band": [
			{"label": _lt("Asset"), "source": "Measure", "measure": "handover.what"},
			{"label": _lt("From Employee"), "source": "Measure", "measure": "handover.from"},
			{"label": _lt("To Employee"), "source": "Measure", "measure": "handover.to"},
			{"label": _lt("Transaction Date"), "source": "Field", "field": "transaction_date"},
		],
	},
	{
		"doctype": "Asset Maintenance",
		"band": [
			{"label": _lt("Asset"), "source": "Measure", "measure": "service.asset"},
			{"label": _lt("Next Due Date"), "source": "Measure", "measure": "schedule.next"},
			{"label": _lt("Maintenance Team"), "source": "Field", "field": "maintenance_team"},
		],
	},
	{
		"doctype": "Asset Maintenance Log",
		"band": [
			{"label": _lt("Asset"), "source": "Measure", "measure": "service.asset"},
			{"label": _lt("Due Date"), "source": "Measure", "measure": "service.due"},
			{"label": _lt("Assign To"), "source": "Field", "field": "assign_to_name"},
			{"label": _lt("Last Completion Date"), "source": "Measure", "measure": "service.last"},
		],
	},
	{
		"doctype": "Asset Repair",
		"band": [
			{"label": _lt("Asset"), "source": "Measure", "measure": "repair.asset"},
			{"label": _lt("Downtime"), "source": "Measure", "measure": "repair.out"},
			{"label": _lt("Repair Cost"), "source": "Measure", "measure": "repair.cost"},
		],
	},
	{
		"doctype": "Asset Value Adjustment",
		"band": [
			{"label": _lt("Asset"), "source": "Measure", "measure": "repair.asset"},
			{"label": _lt("Current Asset Value"), "source": "Field", "field": "current_asset_value"},
			{"label": _lt("New Asset Value"), "source": "Field", "field": "new_asset_value"},
			{"label": _lt("Difference Amount"), "source": "Measure", "measure": "adjustment.change"},
		],
	},
	{
		"doctype": "Stock Reconciliation",
		"band": [
			{"label": _lt("Purpose"), "source": "Field", "field": "purpose"},
			{"label": _lt("Warehouse"), "source": "Measure", "measure": "count.where"},
			{"label": _lt("Items"), "source": "Measure", "measure": "count.items"},
			{"label": _lt("Difference Amount"), "source": "Field", "field": "difference_amount", "shown_when": [["docstatus", "=", 1]]},
		],
	},
]
