"""What an item's, an asset's, a warehouse's, a receipt's and a delivery's
form say above their fields: the heads, the measures they place and the verbs
they offer. See one/head.py.
"""

from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import flt, fmt_money, formatdate, getdate, today
from frappe.utils.caching import request_cache

from onedesk.one import figures
from onedesk.one_inventory import assets, custody, item

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


# ------------------------------------------------------------------ an item


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
		# The day goes in the label, as a party's last invoice does.
		return {
			"label": _("Last Bought · {0}").format(formatdate(last.on_date)),
			"value": _("{0} from {1}").format(_money(last.rate), last.supplier),
		}
	return {"value": _("Never"), "tone": "quiet"} if doc.is_stock_item else None


# ------------------------------------------------------------------ an asset


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


def where(doc):
	return doc.location or {"value": _("Nowhere yet"), "tone": "waiting"}


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
		"label": _("Next Service · {0}").format(formatdate(service.due_date)),
		"value": service.task_name,
		"tone": "alarm" if getdate(service.due_date) < getdate(today()) else None,
		"route": f"/desk/asset-maintenance-log/{quote(service.name)}",
	}


def who_has_it(doc):
	if not doc.custodian:
		return {"value": _("Nobody"), "tone": "quiet", "route": None}
	return _asset(doc.name)["custodian_name"] or doc.custodian


# ------------------------------------------------------------------ a warehouse


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


# ------------------------------------------------------------------ a receipt


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
	supplier in another currency is said beside it."""
	if doc.docstatus == 1:
		value = sum(flt(row.valuation_rate) * flt(row.stock_qty) for row in doc.items)
	else:
		value = flt(doc.base_net_total)
	company = frappe.get_cached_value("Company", doc.company, "default_currency")
	if doc.currency and doc.currency != company:
		return {
			"label": _("Worth · {0}").format(fmt_money(doc.net_total, currency=doc.currency)),
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


# ------------------------------------------------------------------ a delivery


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
		return {"label": _("Total · {0}").format(fmt_money(doc.base_grand_total, currency=company)), "value": shown}
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


# ------------------------------------------------------------------ buying


def _company_money(doc) -> str:
	return frappe.get_cached_value("Company", doc.company, "default_currency")


def _total(doc):
	"""In the supplier's money, with the company's beside it when they differ."""
	company = _company_money(doc)
	shown = fmt_money(doc.grand_total, currency=doc.currency)
	if doc.currency and doc.currency != company:
		return {"label": _("Total · {0}").format(fmt_money(doc.base_grand_total, currency=company)), "value": shown}
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


def request_wanted(doc):
	return _wanted(doc.schedule_date, doc.docstatus != 1 or flt(doc.per_received) >= 100 or doc.status in ("Stopped", "Cancelled"))


def request_quotes(doc):
	"""The quotes suppliers sent for it, opening the request that asked them."""
	asked = frappe.get_all(
		"Request for Quotation Item",
		filters={"material_request": doc.name, "docstatus": ["<", 2]},
		pluck="parent",
		distinct=True,
	)
	if not asked:
		return None
	quotes = frappe.get_all(
		"Supplier Quotation Item",
		filters={"request_for_quotation": ["in", asked], "docstatus": ["<", 2]},
		pluck="parent",
		distinct=True,
	)
	value = _("{0} of {1}").format(len(quotes), len(_asked(asked[0]))) if len(asked) == 1 else str(len(quotes))
	return {"value": value, "route": f"/desk/request-for-quotation/{quote(asked[0])}"}


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


def order_wanted(doc):
	"""The earliest day goods still to come are wanted."""
	waiting = [row.schedule_date for row in doc.items if flt(row.received_qty) < flt(row.qty)]
	if doc.docstatus != 1 or doc.status in ("Closed", "On Hold", "Completed"):
		return formatdate(doc.schedule_date) if doc.schedule_date else None
	if not waiting:
		return None
	return _wanted(min(waiting), False)


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
		return {"value": said, "tone": "quiet", "label": _("Ended")}
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


# ------------------------------------------------------------------ a movement


#: What makes goods, whose value is what was made, with what it used beside it.
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


# ------------------------------------------------------------------ a count


def count_items(doc):
	"""ERPNext keeps only the lines a count changed, so each one is a difference."""
	return str(len(doc.items))


def count_where(doc):
	return _places(row.warehouse for row in doc.items)


# ------------------------------------------------------------------ the charts


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
		"labels": [formatdate(day, "MMM yy") for day, _value in points],
		"values": [value for _day, value in points],
		"currency": frappe.db.get_default("currency"),
		"said": _("{0} at the end").format(_money(points[-1][1])),
	}


CHARTS = {
	"item.moved": {"doctypes": ["Item"], "label": _lt("Out of Stock, Month by Month"), "figures": moved},
	"asset.life": {"doctypes": ["Asset"], "label": _lt("Worth Over Its Life"), "figures": life},
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
	"asset.where": where,
	"asset.next_service": next_service,
	"asset.who_has_it": who_has_it,
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
	"request.wanted": request_wanted,
	"request.quotes": request_quotes,
	"rfq.request": rfq_request,
	"rfq.answered": rfq_answered,
	"rfq.cheapest": rfq_cheapest,
	"quote.request": quote_request,
	"quote.valid": quote_valid,
	"quote.cheapest": quote_cheapest,
	"quote.ordered": quote_ordered,
	"order.total": order_total,
	"order.wanted": order_wanted,
	"order.blanket": order_blanket,
	"blanket.party": blanket_party,
	"blanket.runs": blanket_runs,
	"blanket.ordered": blanket_ordered,
	"blanket.orders": blanket_orders,
}


# ------------------------------------------------------------------ the two movements


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


# ------------------------------------------------------------------ the heads

HEADS = [
	{
		"doctype": "Item",
		"band": [
			{
				"label": _lt("Assets"),
				"source": "Count",
				"of_doctype": "Asset",
				"filters": [["item_code", "=", "{{ doc.name }}"], ["docstatus", "<", 2]],
				"shown_when": FIXED,
				"route": "/desk/asset?item_code={{ doc.name }}",
			},
			{
				"label": _lt("Not Yet Registered"),
				"source": "Count",
				"of_doctype": "Asset",
				"filters": [["item_code", "=", "{{ doc.name }}"], ["docstatus", "=", 0]],
				"shown_when": FIXED,
				"route": "/desk/asset?item_code={{ doc.name }}&docstatus=0",
				"tone": "waiting",
				"hide_empty": 1,
			},
			{
				"label": _lt("On Hand"),
				"source": "Measure",
				"measure": "item.on_hand",
				"shown_when": STOCK,
				"route": "/desk/query-report/Stock Balance?item_code={{ doc.name }}",
			},
			{"label": _lt("Free to Sell"), "source": "Measure", "measure": "item.free", "shown_when": STOCK},
			{
				"label": _lt("On Order"),
				"source": "Measure",
				"measure": "item.on_order",
				"shown_when": STOCK,
				"route": '/desk/purchase-order?item_code={{ doc.name }}&docstatus=1&status=["not in",["Completed","Closed"]]',
			},
			{"label": _lt("Worth"), "source": "Measure", "measure": "item.worth", "shown_when": STOCK},
			{"label": _lt("Reorder"), "source": "Measure", "measure": "item.reorder", "shown_when": STOCK},
			{
				"label": _lt("Last Bought"),
				"source": "Measure",
				"measure": "item.last_bought",
				"shown_when": [["is_fixed_asset", "=", 0]],
			},
		],
		"charts": [{"chart": "item.moved", "shown_when": STOCK}],
	},
	{
		"doctype": "Asset",
		"band": [
			{"label": _lt("Worth Now"), "source": "Measure", "measure": "asset.worth_now"},
			{"label": _lt("Cost"), "source": "Measure", "measure": "asset.cost"},
			{"label": _lt("Depreciation"), "source": "Measure", "measure": "asset.depreciation"},
			{"label": _lt("Written Off"), "source": "Measure", "measure": "asset.written_off"},
			{"label": _lt("Next Depreciation"), "source": "Measure", "measure": "asset.next_depreciation"},
			{"label": _lt("Where"), "source": "Measure", "measure": "asset.where"},
			{
				"label": _lt("Next Service"),
				"source": "Measure",
				"measure": "asset.next_service",
				"shown_when": [["maintenance_required", "=", 1]],
			},
			{
				"label": _lt("Who Has It"),
				"source": "Measure",
				"measure": "asset.who_has_it",
				"shown_when": SUBMITTED,
				"route": "/desk/employee/{{ doc.custodian }}",
			},
		],
		"verbs": [{"verb": "asset.give"}, {"verb": "asset.take_back"}],
		"charts": [{"chart": "asset.life", "shown_when": SUBMITTED}],
	},
	{
		"doctype": "Warehouse",
		"band": [
			{
				"label": _lt("Items Held"),
				"source": "Measure",
				"measure": "warehouse.items",
				"route": "/desk/stock-on-hand?warehouse={{ doc.name }}",
			},
			{"label": _lt("Worth"), "source": "Measure", "measure": "warehouse.worth"},
			{
				"label": _lt("Low"),
				"source": "Measure",
				"measure": "warehouse.low",
				"route": "/desk/stock-on-hand?warehouse={{ doc.name }}",
			},
			{
				"label": _lt("Last Move"),
				"source": "Measure",
				"measure": "warehouse.last",
				"route": "/desk/query-report/Stock Ledger?warehouse={{ doc.name }}",
			},
		],
	},
	{
		"doctype": "Purchase Order",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Total"), "source": "Measure", "measure": "order.total"},
			{"label": _lt("Wanted By"), "source": "Measure", "measure": "order.wanted"},
			{"label": _lt("Agreed On"), "source": "Measure", "measure": "order.blanket"},
			{
				"label": _lt("Received"),
				"source": "Field",
				"field": "per_received",
				"shown_when": [["docstatus", "=", 1]],
			},
			{
				"label": _lt("Billed"),
				"source": "Field",
				"field": "per_billed",
				"shown_when": [["docstatus", "=", 1]],
			},
		],
	},
	{
		"doctype": "Material Request",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Asked By"), "source": "Measure", "measure": "request.asked_by"},
			{"label": _lt("Wanted By"), "source": "Measure", "measure": "request.wanted"},
			{"label": _lt("Quotes"), "source": "Measure", "measure": "request.quotes"},
			{
				"label": _lt("Ordered"),
				"source": "Field",
				"field": "per_ordered",
				"shown_when": [["docstatus", "=", 1], ["material_request_type", "=", "Purchase"]],
			},
			{
				"label": _lt("Received"),
				"source": "Field",
				"field": "per_received",
				"shown_when": [["docstatus", "=", 1], ["material_request_type", "=", "Purchase"]],
			},
		],
	},
	{
		"doctype": "Request for Quotation",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Request"), "source": "Measure", "measure": "rfq.request"},
			{"label": _lt("Answered"), "source": "Measure", "measure": "rfq.answered"},
			{"label": _lt("Cheapest"), "source": "Measure", "measure": "rfq.cheapest"},
		],
	},
	{
		"doctype": "Supplier Quotation",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Asked On"), "source": "Measure", "measure": "quote.request"},
			{"label": _lt("Total"), "source": "Measure", "measure": "order.total"},
			{"label": _lt("Valid Till"), "source": "Measure", "measure": "quote.valid"},
			{"label": _lt("Cheapest On"), "source": "Measure", "measure": "quote.cheapest"},
			{"label": _lt("Ordered On"), "source": "Measure", "measure": "quote.ordered"},
		],
	},
	{
		"doctype": "Blanket Order",
		"band": [
			{"label": _lt("With"), "source": "Measure", "measure": "blanket.party"},
			{"label": _lt("Runs"), "source": "Measure", "measure": "blanket.runs"},
			{"label": _lt("Ordered"), "source": "Measure", "measure": "blanket.ordered"},
			{"label": _lt("Orders"), "source": "Measure", "measure": "blanket.orders", "shown_when": SUBMITTED},
		],
	},
	{
		"doctype": "Purchase Receipt",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Order"), "source": "Measure", "measure": "receipt.order"},
			{"label": _lt("Worth"), "source": "Measure", "measure": "receipt.worth"},
			{"label": _lt("Landed Costs"), "source": "Measure", "measure": "receipt.landed"},
			{"label": _lt("Rejected"), "source": "Measure", "measure": "receipt.rejected"},
			{
				"label": _lt("Billed"),
				"source": "Field",
				"field": "per_billed",
				"shown_when": [["docstatus", "=", 1], ["is_return", "=", 0]],
			},
		],
	},
	{
		"doctype": "Delivery Note",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Order"), "source": "Measure", "measure": "delivery.order"},
			{"label": _lt("Total"), "source": "Measure", "measure": "delivery.total"},
			{"label": _lt("Trip"), "source": "Measure", "measure": "delivery.trip"},
			{
				"label": _lt("Billed"),
				"source": "Field",
				"field": "per_billed",
				"shown_when": [["docstatus", "=", 1], ["is_return", "=", 0]],
			},
			{
				"label": _lt("Returned"),
				"source": "Field",
				"field": "per_returned",
				"shown_when": [["per_returned", ">", 0]],
			},
		],
	},
	{
		"doctype": "Stock Entry",
		"band": [
			{"label": _lt("Project"), "source": "Measure", "measure": "project.of"},
			{"label": _lt("Type"), "source": "Field", "field": "stock_entry_type"},
			{"label": _lt("From"), "source": "Measure", "measure": "move.from"},
			{"label": _lt("To"), "source": "Measure", "measure": "move.to"},
			{"label": _lt("Value"), "source": "Measure", "measure": "move.value"},
			{"label": _lt("Used"), "source": "Measure", "measure": "move.used"},
			{
				"label": _lt("Arrived"),
				"source": "Field",
				"field": "per_transferred",
				"shown_when": [["add_to_transit", "=", 1], ["docstatus", "=", 1]],
			},
		],
	},
	{
		"doctype": "Stock Reconciliation",
		"band": [
			{"label": _lt("Purpose"), "source": "Field", "field": "purpose"},
			{"label": _lt("Where"), "source": "Measure", "measure": "count.where"},
			{"label": _lt("Items"), "source": "Measure", "measure": "count.items"},
			{"label": _lt("Difference"), "source": "Field", "field": "difference_amount", "shown_when": [["docstatus", "=", 1]]},
		],
	},
]
