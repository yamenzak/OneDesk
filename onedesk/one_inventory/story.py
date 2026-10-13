"""OneInventory's Home, told as a story (page/inventory, frontend/src/home):
the headline figures with their months, then where stock is, how it moves,
how old it is, buying, making and equipment. Each is read through
frappe.get_list as the reader may see it, for the reader's company, in its
currency. How it works is in the module's README, Under the hood.
"""
import calendar
from collections import defaultdict
from datetime import date

import frappe
from frappe import _
from frappe.utils import add_months, date_diff, flt, getdate, today

#: How many months the story looks back over, this one included.
MONTHS = 12

#: The age bands stock is sorted into, in days (ERPNext's Stock Ageing).
AGES = "30, 90, 180, 365"

#: What a stock entry's purpose means for the story.
PURPOSES = {
	"Material Receipt": "received",
	"Material Issue": "used",
	"Manufacture": "made",
}


def _may(doctype: str) -> bool:
	return bool(frappe.has_permission(doctype, "read"))


def _company() -> str | None:
	"""The company the story is told for: the reader's default company."""
	import erpnext

	return erpnext.get_default_company()


def _ours(filters: dict) -> dict:
	"""The filters, narrowed to the reader's company where there is one."""
	company = _company()
	return {**filters, "company": company} if company else filters


def _warehouses() -> list[str] | None:
	"""The company's warehouses, for what is kept by warehouse (a Bin)."""
	company = _company()
	if not company:
		return None
	return frappe.get_all("Warehouse", filters={"company": company}, pluck="name")


def _bins(filters: dict | None = None) -> dict:
	"""Bin filters, narrowed to the company's warehouses."""
	places = _warehouses()
	filters = dict(filters or {})
	if places is not None:
		filters["warehouse"] = ["in", places or [""]]
	return filters


def _months() -> list[date]:
	start = getdate(today()).replace(day=1)
	return [getdate(add_months(start, -back)) for back in range(MONTHS - 1, -1, -1)]


def _month(day) -> str:
	return getdate(day).replace(day=1).isoformat()


def _end(month: date) -> date:
	return month.replace(day=calendar.monthrange(month.year, month.month)[1])


@frappe.whitelist()
@frappe.read_only()
def read() -> dict:
	"""Everything Home's story draws, each part None when the reader may not
	see it or there is nothing to draw."""
	import erpnext

	company = _company()
	months = _months()
	moves = _moves(months[0]) if _may("Stock Ledger Entry") else None
	if moves:
		first = _month(moves[0].posting_date)
		months = [one for one in months if one.isoformat() >= first] or months
	return {
		"currency": erpnext.get_company_currency(company) if company else None,
		"months": [one.isoformat() for one in months],
		"cards": _cards(months, moves),
		"where": _where(),
		"moves": _flows(months, moves),
		"ages": _ages(company),
		"buying": _buying(months[0]),
		"making": _making(months[0]),
		"equipment": _equipment(months),
	}


def _moves(since: date) -> list[dict]:
	"""Each paper that moved stock since the month the story starts, per
	warehouse: its net worth moved, and what it was."""
	rows = frappe.get_list(
		"Stock Ledger Entry",
		filters=_ours({"is_cancelled": 0, "posting_date": [">=", since]}),
		fields=[
			"posting_date",
			"voucher_type",
			"voucher_no",
			"warehouse",
			{"SUM": "stock_value_difference", "as": "value"},
		],
		group_by="posting_date, voucher_type, voucher_no, warehouse",
		order_by="posting_date asc",
		limit_page_length=0,
	)
	kinds = _kinds(rows)
	for row in rows:
		row.kind = kinds.get((row.voucher_type, row.voucher_no))
	return rows


def _kinds(rows: list) -> dict:
	"""What each paper was: bought, delivered, made, used, received, counted or
	opening stock, with whom it was, read from the paper itself."""
	named = defaultdict(set)
	for row in rows:
		named[row.voucher_type].add(row.voucher_no)
	out = {}

	def read(doctype, fields, kind):
		if not named.get(doctype) or not _may(doctype):
			return
		for one in frappe.get_list(
			doctype,
			filters={"name": ["in", list(named[doctype])]},
			fields=["name", *fields],
			limit_page_length=0,
		):
			out[(doctype, one.name)] = kind(one)

	read("Purchase Receipt", ["supplier_name"], lambda one: ("bought", one.supplier_name))
	read("Purchase Invoice", ["supplier_name"], lambda one: ("bought", one.supplier_name))
	read("Subcontracting Receipt", ["supplier_name"], lambda one: ("bought", one.supplier_name))
	read("Delivery Note", ["customer_name"], lambda one: ("delivered", one.customer_name))
	read("Sales Invoice", ["customer_name"], lambda one: ("delivered", one.customer_name))
	read("Stock Entry", ["purpose", "project"], lambda one: (PURPOSES.get(one.purpose, "moved"), one.project))
	read(
		"Stock Reconciliation",
		["purpose"],
		lambda one: ("opening" if one.purpose == "Opening Stock" else "counted", None),
	)
	return out


def _worth_now() -> float | None:
	if not _may("Bin"):
		return None
	got = frappe.get_list("Bin", filters=_bins(), fields=[{"SUM": "stock_value", "as": "worth"}])
	return flt(got[0].worth) if got else 0.0


def _series(months: list[date], moves: list, kinds: tuple, sign: int = 0) -> list[float]:
	"""The worth each month moved by papers of these kinds; `sign` keeps only
	what came in (1) or went out (-1)."""
	by = defaultdict(float)
	for row in moves:
		kind = (row.kind or (None,))[0]
		if kind not in kinds or (sign and flt(row.value) * sign <= 0):
			continue
		by[_month(row.posting_date)] += flt(row.value)
	return [round(abs(by[one.isoformat()]), 2) for one in months]


def _worth_by_month(months: list[date], moves: list, now: float) -> list[float]:
	"""Stock's worth at the end of each month: today's, less what moved since."""
	out = []
	for month in months:
		end = _end(month)
		later = sum(flt(row.value) for row in moves if getdate(row.posting_date) > end)
		out.append(round(now - later, 2))
	return out


def _taken(months: list[date], moves: list) -> list[float]:
	return [
		a + b
		for a, b in zip(
			_series(months, moves, ("bought",)), _series(months, moves, ("received",)), strict=True
		)
	]


def _sent(months: list[date], moves: list) -> list[float]:
	return [
		a + b
		for a, b in zip(
			_series(months, moves, ("delivered",)), _series(months, moves, ("used",), -1), strict=True
		)
	]


def _made(months: list[date], moves: list) -> list[float]:
	return _series(months, moves, ("made",), 1)


#: The headline figures: the key the page knows each by, and the frappe
#: Number Card (number_card/) whose method counts it.
CARDS = (
	("worth", "Stock Worth"),
	("taken_in", "Taken In This Month"),
	("sent_out", "Sent Out This Month"),
	("made", "Made This Month"),
	("on_order", "Still on Order"),
	("papers", "Moves This Month"),
)


def _cards(months: list[date], moves: list | None) -> dict:
	"""The headline figures, each its Number Card's own value, with its months
	for a sparkline."""
	series = {}
	now = _worth_now()
	if now is not None and moves is not None:
		series.update(
			worth=_worth_by_month(months, moves, now),
			taken_in=_taken(months, moves),
			sent_out=_sent(months, moves),
			made=_made(months, moves),
			papers=_papers(months, moves),
		)
	if _may("Purchase Order"):
		series["on_order"] = _on_order(months)["series"]
	out = {}
	for key, name in CARDS:
		if key in series:
			method = frappe.get_attr(frappe.get_cached_value("Number Card", name, "method"))
			out[key] = {"card": name, "value": method()["value"], "series": series[key]}
	return out


def _card(value, route: list, fieldtype: str = "Currency", options: dict | None = None) -> dict:
	card = {"value": value, "fieldtype": fieldtype, "route": route}
	if options:
		card["route_options"] = options
	return card


def _month_moves() -> tuple[list[date], list]:
	"""This month, and the papers that moved stock in it, for a card."""
	frappe.has_permission("Stock Ledger Entry", "read", throw=True)
	month = getdate(today()).replace(day=1)
	return [month], _moves(month)


@frappe.whitelist()
@frappe.read_only()
def stock_worth(filters: str | None = None) -> dict:
	"""What the stock in every warehouse is worth today (Stock on Hand)."""
	frappe.has_permission("Bin", "read", throw=True)
	return _card(_worth_now(), ["stock-on-hand"])


@frappe.whitelist()
@frappe.read_only()
def taken_in_this_month(filters: str | None = None) -> dict:
	"""The worth of goods bought or taken in since the first of the month."""
	return _card(_taken(*_month_moves())[-1], ["List", "Purchase Receipt"])


@frappe.whitelist()
@frappe.read_only()
def sent_out_this_month(filters: str | None = None) -> dict:
	"""The worth of goods delivered or used on jobs since the first of the month."""
	return _card(_sent(*_month_moves())[-1], ["List", "Delivery Note"])


@frappe.whitelist()
@frappe.read_only()
def made_this_month(filters: str | None = None) -> dict:
	"""The worth of what the workshop made since the first of the month."""
	return _card(_made(*_month_moves())[-1], ["List", "Work Order"])


@frappe.whitelist()
@frappe.read_only()
def still_on_order(filters: str | None = None) -> dict:
	"""The worth of what is ordered from suppliers and not yet here."""
	frappe.has_permission("Purchase Order", "read", throw=True)
	return _card(
		_on_order(_months())["value"], ["List", "Purchase Order"], options={"status": "To Receive and Bill"}
	)


@frappe.whitelist()
@frappe.read_only()
def moves_this_month(filters: str | None = None) -> dict:
	"""How many papers moved stock since the first of the month."""
	return _card(_papers(*_month_moves())[-1], ["query-report", "Stock Ledger"], "Int")


def _papers(months: list[date], moves: list) -> list[int]:
	"""How many papers moved stock each month."""
	seen = defaultdict(set)
	for row in moves:
		if (row.kind or (None,))[0] not in (None, "opening"):
			seen[_month(row.posting_date)].add((row.voucher_type, row.voucher_no))
	return [len(seen[one.isoformat()]) for one in months]


def _on_order(months: list[date]) -> dict:
	"""What is ordered and not yet here, and what was ordered each month."""
	orders = frappe.get_list(
		"Purchase Order",
		filters=_ours({"docstatus": 1, "status": ["not in", ("Closed", "On Hold")]}),
		fields=["transaction_date", "base_net_total", "per_received"],
		limit_page_length=0,
	)
	waiting = sum(flt(one.base_net_total) * (100 - flt(one.per_received)) / 100 for one in orders)
	by = defaultdict(float)
	for one in orders:
		by[_month(one.transaction_date)] += flt(one.base_net_total)
	return {"value": round(waiting, 2), "series": [round(by[one.isoformat()], 2) for one in months]}


def _titles(doctype: str, field: str, names) -> dict:
	"""Each record's plain name (a warehouse without its company's letters, a
	project's title), as the reader may see it."""
	names = [one for one in set(names) if one]
	if not names or not _may(doctype):
		return {}
	return {
		one.name: one[field] or one.name
		for one in frappe.get_list(
			doctype, filters={"name": ["in", names]}, fields=["name", field], limit_page_length=0
		)
	}


def _where() -> dict | None:
	"""Stock's worth by warehouse, by item group, and its most valuable items."""
	if not _may("Bin"):
		return None
	bins = frappe.get_list(
		"Bin",
		filters=_bins({"stock_value": [">", 0]}),
		fields=["warehouse", "item_code", "stock_value"],
		limit_page_length=0,
	)
	if not bins:
		return None
	items = {
		one.name: one
		for one in frappe.get_list(
			"Item",
			filters={"name": ["in", list({one.item_code for one in bins})]},
			fields=["name", "item_name", "item_group"],
			limit_page_length=0,
		)
	}
	warehouses, groups, worth = defaultdict(float), defaultdict(float), defaultdict(float)
	for one in bins:
		item = items.get(one.item_code)
		warehouses[one.warehouse] += flt(one.stock_value)
		groups[item.item_group if item else one.item_code] += flt(one.stock_value)
		worth[one.item_code] += flt(one.stock_value)

	plain = _titles("Warehouse", "warehouse_name", warehouses)

	def rows(by, key):
		return [
			{key: name, "name": plain.get(name, name), "worth": round(value, 2)}
			for name, value in sorted(by.items(), key=lambda kv: -kv[1])
		]

	top = sorted(worth.items(), key=lambda kv: -kv[1])[:8]
	return {
		"warehouses": rows(warehouses, "warehouse"),
		"groups": rows(groups, "group"),
		"items": [
			{"item": code, "name": items[code].item_name if code in items else code, "worth": round(value, 2)}
			for code, value in top
		],
	}


def _flows(months: list[date], moves: list | None) -> dict | None:
	"""How stock moved: its worth month by month, what came in and went out by
	kind, where goods came from and went, and on which days."""
	if not moves:
		return None
	now = _worth_now()
	flow = []
	for month in months:
		day = {"month": month.isoformat()}
		for kind, sign in (("bought", 1), ("received", 1), ("made", 1), ("delivered", -1), ("used", -1)):
			day[kind] = _series([month], moves, (kind,), sign)[0] * sign
		counted = _series([month], moves, ("counted",), 1)[0] - _series([month], moves, ("counted",), -1)[0]
		day["counted"] = round(counted, 2)
		flow.append(day)
	return {
		"worth": [
			{"month": m.isoformat(), "worth": w}
			for m, w in zip(months, _worth_by_month(months, moves, now or 0), strict=True)
		]
		if now is not None
		else None,
		"flow": flow,
		"paths": _paths(moves),
		"days": _days(months, moves),
		"kinds": _kinds_count(moves),
	}


def _paths(moves: list) -> list[dict]:
	"""Goods' path by worth: from each supplier into a warehouse, and from a
	warehouse to a customer, a project or the workshop. A warehouse keeps its
	full name where its plain one is also a supplier's or a customer's."""
	links = defaultdict(float)
	projects = _titles(
		"Project",
		"project_name",
		[(row.kind or (None, None))[1] for row in moves if (row.kind or (None,))[0] == "used"],
	)
	for row in moves:
		kind, who = row.kind or (None, None)
		value, place = flt(row.value), ("place", row.warehouse)
		if kind == "bought" and value > 0:
			links[(("party", who or _("Suppliers")), place)] += value
		elif kind == "received" and value > 0:
			links[(("party", _("Taken In")), place)] += value
		elif kind == "delivered" and value < 0:
			links[(place, ("party", who or _("Customers")))] += -value
		elif kind == "used" and value < 0:
			links[(place, ("party", projects.get(who, who) or _("Used")))] += -value
		elif kind == "made" and value < 0:
			links[(place, ("party", _("Making")))] += -value
	parties = {name for link in links for layer, name in link if layer == "party"}
	plain = _titles(
		"Warehouse", "warehouse_name", [name for link in links for layer, name in link if layer == "place"]
	)

	def label(node):
		layer, name = node
		return name if layer == "party" or plain.get(name, name) in parties else plain.get(name, name)

	return [
		{"from": label(a), "to": label(b), "worth": round(v, 2)}
		for (a, b), v in links.items()
		if round(v, 2) > 0
	]


def _days(months: list[date], moves: list) -> list[dict]:
	"""How many papers moved stock on each weekday of each month."""
	seen = defaultdict(set)
	for row in moves:
		if (row.kind or (None,))[0] in (None, "opening"):
			continue
		day = getdate(row.posting_date)
		seen[(_month(day), day.weekday())].add((row.voucher_type, row.voucher_no))
	return [
		{"month": month.isoformat(), "day": weekday, "moves": len(seen[(month.isoformat(), weekday)])}
		for month in months
		for weekday in range(7)
	]


def _kinds_count(moves: list) -> list[dict]:
	"""How many papers of each kind moved stock over the twelve months."""
	papers = defaultdict(set)
	for row in moves:
		kind = (row.kind or (None,))[0]
		if kind and kind != "opening":
			papers[kind].add((row.voucher_type, row.voucher_no))
	return [
		{"kind": kind, "papers": len(names)}
		for kind, names in sorted(papers.items(), key=lambda kv: -len(kv[1]))
	]


def _ages(company: str | None) -> list[dict] | None:
	"""Stock's worth by how long it has sat, as ERPNext's Stock Ageing counts it."""
	if not company or not frappe.db.exists("Report", "Stock Ageing"):
		return None
	report = frappe.get_cached_doc("Report", "Stock Ageing")
	if not report.is_permitted():
		return None
	from erpnext.stock.report.stock_ageing.stock_ageing import execute

	columns, data, *_rest = execute(frappe._dict(company=company, to_date=today(), range=AGES))
	names = [one["fieldname"] if isinstance(one, dict) else one for one in columns]
	start = names.index("average_age") + 1
	bands = len(AGES.split(",")) + 1
	worth = [0.0] * bands
	for row in data:
		for band in range(bands):
			worth[band] += flt(row[start + band * 2 + 1])
	return [{"band": band, "worth": round(value, 2)} for band, value in enumerate(worth)]


def _buying(since: date) -> dict | None:
	"""Orders since the story starts: how far they came, from whom, and how
	each supplier keeps to the dates."""
	if not _may("Purchase Order"):
		return None
	orders = frappe.get_list(
		"Purchase Order",
		filters=_ours({"docstatus": 1, "transaction_date": [">=", since]}),
		fields=["name", "supplier", "supplier_name", "base_net_total", "per_received", "schedule_date"],
		limit_page_length=0,
	)
	if not orders:
		return None
	got = _received_on([one.name for one in orders])
	asked = _requests(since)
	day = getdate(today())
	suppliers = defaultdict(lambda: {"worth": 0.0, "orders": 0, "late": []})
	for one in orders:
		worth = flt(one.base_net_total)
		said = suppliers[one.supplier]
		said["name"] = one.supplier_name or one.supplier
		said["worth"] += worth
		said["orders"] += 1
		if one.schedule_date:
			came = got.get(one.name) or (None if flt(one.per_received) >= 100 else day)
			if came:
				said["late"].append(max(0, date_diff(came, one.schedule_date)))
	return {
		"requests": asked,
		"suppliers": [
			{
				"supplier": key,
				"name": one["name"],
				"worth": round(one["worth"], 2),
				"orders": one["orders"],
				"late": round(sum(one["late"]) / len(one["late"]), 1) if one["late"] else 0,
			}
			for key, one in sorted(suppliers.items(), key=lambda kv: -kv[1]["worth"])
		],
	}


def _requests(since: date) -> list[dict] | None:
	"""How far the material requests for buying got: asked for, ordered, some
	of it here, all of it here."""
	if not _may("Material Request"):
		return None
	said = defaultdict(int)
	for one in frappe.get_list(
		"Material Request",
		filters=_ours(
			{"docstatus": 1, "material_request_type": "Purchase", "transaction_date": [">=", since]}
		),
		fields=["status", {"COUNT": "*", "as": "n"}],
		group_by="status",
	):
		said[one.status] += one.n
	steps = (
		("asked", sum(said.values())),
		(
			"ordered",
			said["Ordered"] + said["Partially Ordered"] + said["Partially Received"] + said["Received"],
		),
		("arriving", said["Partially Received"] + said["Received"]),
		("here", said["Received"]),
	)
	return [{"step": step, "requests": n} for step, n in steps] if steps[0][1] else None


def _received_on(orders: list[str]) -> dict:
	"""When the last goods of each order came in."""
	if not orders or not _may("Purchase Receipt"):
		return {}
	rows = frappe.get_list(
		"Purchase Receipt",
		filters=[["docstatus", "=", 1], ["Purchase Receipt Item", "purchase_order", "in", orders]],
		fields=["posting_date", "`tabPurchase Receipt Item`.purchase_order as purchase_order"],
		limit_page_length=0,
	)
	last = {}
	for row in rows:
		if row.purchase_order and (
			row.purchase_order not in last or getdate(row.posting_date) > last[row.purchase_order]
		):
			last[row.purchase_order] = getdate(row.posting_date)
	return last


def _making(since: date) -> dict | None:
	"""Work orders by status, the worth of what was made each month by
	product, and the hours each workstation worked. Made is worth, in the
	company's currency, so pieces and metres of different products are never
	stacked as one number."""
	if not _may("Work Order"):
		return None
	statuses = frappe.get_list(
		"Work Order",
		filters=_ours({"docstatus": ["<", 2]}),
		fields=["status", {"COUNT": "*", "as": "orders"}],
		group_by="status",
	)
	made = (
		frappe.get_list(
			"Stock Entry",
			filters=[
				*[[k, "=", v] for k, v in _ours({"docstatus": 1, "purpose": "Manufacture"}).items()],
				["posting_date", ">=", since],
				["Stock Entry Detail", "is_finished_item", "=", 1],
			],
			fields=[
				"posting_date",
				"`tabStock Entry Detail`.item_name as item_name",
				"`tabStock Entry Detail`.amount as amount",
			],
			limit_page_length=0,
		)
		if _may("Stock Entry")
		else []
	)
	by = defaultdict(float)
	for one in made:
		by[(_month(one.posting_date), one.item_name)] += flt(one.amount)
	hours = (
		frappe.get_list(
			"Job Card",
			filters=_ours({"docstatus": ["<", 2], "workstation": ["is", "set"]}),
			fields=["workstation", {"SUM": "total_time_in_mins", "as": "minutes"}],
			group_by="workstation",
		)
		if _may("Job Card")
		else []
	)
	return {
		"statuses": [{"status": one.status, "orders": one.orders} for one in statuses],
		"made": [
			{"month": month, "item": item, "made": round(worth, 2)}
			for (month, item), worth in sorted(by.items())
		],
		"hours": sorted(
			[
				{"workstation": one.workstation, "hours": round(flt(one.minutes) / 60, 1)}
				for one in hours
				if flt(one.minutes)
			],
			key=lambda one: -one["hours"],
		),
	}


def _plans() -> list[str]:
	"""The company's maintenance plans, which its services hang from."""
	return frappe.get_all("Asset Maintenance", filters=_ours({}), pluck="name")


def _equipment(months: list[date]) -> dict | None:
	"""Equipment's worth by kind, bought against now, its status, and its
	services month by month. Both worths are the company's currency
	(`total_asset_cost`, `value_after_depreciation`)."""
	if not _may("Asset"):
		return None
	assets = frappe.get_list(
		"Asset",
		filters=_ours({"docstatus": 1}),
		fields=["asset_category", "status", "total_asset_cost", "value_after_depreciation"],
		limit_page_length=0,
	)
	kinds = defaultdict(lambda: {"bought": 0.0, "now": 0.0})
	statuses = defaultdict(int)
	for one in assets:
		kinds[one.asset_category]["bought"] += flt(one.total_asset_cost)
		kinds[one.asset_category]["now"] += flt(one.value_after_depreciation)
		statuses[one.status] += 1
	services = []
	if _may("Asset Maintenance Log"):
		logs = frappe.get_list(
			"Asset Maintenance Log",
			filters={
				"due_date": ["between", (months[0], _end(getdate(add_months(months[-1], 2))))],
				"asset_maintenance": ["in", _plans() or [""]],
			},
			fields=["due_date", "maintenance_status"],
			limit_page_length=0,
		)
		count = defaultdict(int)
		for one in logs:
			count[(_month(one.due_date), one.maintenance_status)] += 1
		services = [
			{"month": month, "status": status, "services": n} for (month, status), n in sorted(count.items())
		]
	return {
		"kinds": [
			{"kind": key, "bought": round(one["bought"], 2), "now": round(one["now"], 2)}
			for key, one in kinds.items()
		],
		"statuses": [{"status": key, "assets": n} for key, n in statuses.items()],
		"services": services,
	}
