"""Quotes (page/quotes, frontend/src/inventory/quotes): asking suppliers for prices,
their answers and the comparison, as one page. Every change is ERPNext's own
mapper: a request for quotation from a material request, a supplier's quote
from the request, and a purchase order from a quote. How it works is in the
module's AGENTS.md.
"""

import erpnext
import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, today

MOST = 40
SOON = 7


@frappe.whitelist()
def read(view: str = "asked", search: str | None = None, request: str | None = None) -> dict:
	"""The figures, and the requests, quotes or comparison one tab shows."""
	said = {
		"can": {
			"ask": bool(frappe.has_permission("Request for Quotation", "create")),
			"quote": bool(frappe.has_permission("Supplier Quotation", "create")),
			"order": bool(frappe.has_permission("Purchase Order", "create")),
		},
		"figures": figures(),
		"asked": [],
		"quotes": [],
		"compare": None,
		"requests": [],
	}
	if view == "quotes":
		said["quotes"] = quotes(search=search)
	elif view == "compare":
		said["requests"] = [{"name": one["name"], "label": one["what"]} for one in asked() if one["answered"]]
		chosen = request or next((one["name"] for one in said["requests"]), None)
		said["compare"] = compare(chosen) if chosen else None
	else:
		said["asked"] = asked(search=search)
	return said


def figures() -> dict:
	"""Suppliers still to answer, quotes waiting for a decision, quotes
	still in draft, and live quotes running out within a week."""
	out = {"waiting": None, "to_decide": None, "drafts": None, "expiring": None}
	company = erpnext.get_default_company()
	if frappe.has_permission("Request for Quotation", "read"):
		open_requests = frappe.get_list(
			"Request for Quotation",
			filters={"docstatus": 1, "status": ["!=", "Cancelled"], "company": company},
			pluck="name",
		)
		out["waiting"] = (
			frappe.db.count("Request for Quotation Supplier", {"parent": ["in", open_requests], "quote_status": "Pending"})
			if open_requests
			else 0
		)
	if frappe.has_permission("Supplier Quotation", "read"):
		live = frappe.get_list(
			"Supplier Quotation",
			filters={"docstatus": 1, "status": "Submitted", "company": company},
			fields=["valid_till", "status"],
		)
		live = [one for one in live if not _expired(one)]
		soon = add_days(today(), SOON)
		out.update(
			to_decide=len(live),
			drafts=len(frappe.get_list("Supplier Quotation", filters={"docstatus": 0, "company": company}, pluck="name")),
			expiring=sum(1 for one in live if one.valid_till and getdate(today()) <= getdate(one.valid_till) <= getdate(soon)),
		)
	return out


def asked(search: str | None = None) -> list[dict]:
	"""Requests for quotation, newest first, each with what it asks for,
	from which material request, and each supplier asked with whether and
	how they answered."""
	if not frappe.has_permission("Request for Quotation", "read"):
		return []
	filters = {"docstatus": ["<", 2], "company": erpnext.get_default_company()}
	if search:
		filters["name"] = ["like", f"%{search}%"]
	found = frappe.get_list(
		"Request for Quotation",
		filters=filters,
		fields=["name", "transaction_date", "schedule_date", "status", "docstatus"],
		order_by="transaction_date desc, creation desc",
		limit=MOST,
	)
	names = [one.name for one in found] or [""]
	items: dict = {}
	for row in frappe.get_all(
		"Request for Quotation Item",
		filters={"parent": ["in", names]},
		fields=["parent", "item_code", "item_name", "qty", "uom", "material_request", "project_name"],
		order_by="idx",
	):
		items.setdefault(row.parent, []).append(row)
	suppliers: dict = {}
	for row in frappe.get_all(
		"Request for Quotation Supplier",
		filters={"parent": ["in", names]},
		fields=["parent", "supplier", "supplier_name", "quote_status"],
		order_by="idx",
	):
		suppliers.setdefault(row.parent, []).append(row)
	answers = _answers(names)
	out = []
	for one in found:
		lines = items.get(one.name, [])
		who = [
			{
				"supplier": row.supplier,
				"name": row.supplier_name or row.supplier,
				"quote": answers.get((one.name, row.supplier), {}).get("name"),
				"status": answers.get((one.name, row.supplier), {}).get("status"),
				"answered": (one.name, row.supplier) in answers,
			}
			for row in suppliers.get(one.name, [])
		]
		out.append(
			{
				"name": one.name,
				"date": str(one.transaction_date) if one.transaction_date else None,
				"wanted": str(one.schedule_date) if one.schedule_date else None,
				"draft": one.docstatus == 0,
				"what": _what(lines),
				"lines": len(lines),
				"requests": list(dict.fromkeys(row.material_request for row in lines if row.material_request)),
				"project": _project(next((row.project_name for row in lines if row.project_name), None)),
				"suppliers": who,
				"answered": sum(1 for row in who if row["answered"]),
				"ordered": any(row["status"] in ("Ordered", "Partially Ordered") for row in who),
			}
		)
	return out


def _answers(requests: list) -> dict:
	"""Each supplier's quote for each request, {(request, supplier): quote},
	the newest when there are several."""
	rows = frappe.get_all(
		"Supplier Quotation Item",
		filters={"request_for_quotation": ["in", requests], "docstatus": ["<", 2]},
		fields=["parent", "request_for_quotation"],
		distinct=True,
	)
	if not rows:
		return {}
	quoted = {
		one.name: one
		for one in frappe.get_all(
			"Supplier Quotation",
			filters={
				"name": ["in", [row.parent for row in rows]],
				"docstatus": ["<", 2],
				"company": erpnext.get_default_company(),
			},
			fields=["name", "supplier", "status", "creation"],
			order_by="creation asc",
		)
	}
	out = {}
	for row in rows:
		quote = quoted.get(row.parent)
		if quote:
			out[(row.request_for_quotation, quote.supplier)] = quote
	return out


def _what(lines: list) -> str:
	"""What a request asks for, in a few words: the first item, and how many
	more."""
	if not lines:
		return ""
	first = lines[0].item_name or lines[0].item_code
	return first if len(lines) == 1 else _("{0} and {1} more").format(first, len(lines) - 1)


def quotes(search: str | None = None) -> list[dict]:
	"""Suppliers' quotes, newest first, each with its total in its own money
	and the company's, until when it holds, the request it answers and the
	orders made from it."""
	if not frappe.has_permission("Supplier Quotation", "read"):
		return []
	or_filters = {"name": ["like", f"%{search}%"], "supplier_name": ["like", f"%{search}%"]} if search else None
	found = frappe.get_list(
		"Supplier Quotation",
		filters={"docstatus": ["<", 2], "company": erpnext.get_default_company()},
		or_filters=or_filters,
		fields=[
			"name",
			"supplier",
			"supplier_name",
			"status",
			"docstatus",
			"currency",
			"grand_total",
			"base_grand_total",
			"valid_till",
			"transaction_date",
		],
		order_by="transaction_date desc, creation desc",
		limit=MOST,
	)
	names = [one.name for one in found] or [""]
	requests: dict = {}
	for row in frappe.get_all(
		"Supplier Quotation Item",
		filters={"parent": ["in", names], "request_for_quotation": ["is", "set"]},
		fields=["parent", "request_for_quotation"],
		distinct=True,
	):
		requests.setdefault(row.parent, row.request_for_quotation)
	orders: dict = {}
	for row in frappe.get_all(
		"Purchase Order Item",
		filters={"supplier_quotation": ["in", names], "docstatus": ["<", 2]},
		fields=["supplier_quotation", "parent"],
		distinct=True,
	):
		orders.setdefault(row.supplier_quotation, []).append(row.parent)
	soon = getdate(add_days(today(), SOON))
	return [
		{
			**one,
			"grand_total": flt(one.grand_total),
			"base_grand_total": flt(one.base_grand_total),
			"valid_till": str(one.valid_till) if one.valid_till else None,
			"transaction_date": str(one.transaction_date) if one.transaction_date else None,
			"status": "Expired" if _expired(one) else one.status,
			"expiring": one.status == "Submitted" and not _expired(one) and bool(one.valid_till) and getdate(one.valid_till) <= soon,
			"request": requests.get(one.name),
			"orders": orders.get(one.name, []),
		}
		for one in found
	]


def compare(request: str) -> dict | None:
	"""A request's quotes side by side: each supplier asked, with their quote
	and its total, and each line with every supplier's rate in their own
	money and the company's, so a quote in euros compares. The cheapest live
	rate on each line is marked, and an expired quote is never cheapest. A
	line ordered already, from whichever quote, says so, and `cheapest_on`
	counts only the lines still to order."""
	if not frappe.has_permission("Request for Quotation", "read") or not frappe.db.exists("Request for Quotation", request):
		return None
	if not frappe.has_permission("Request for Quotation", "read", doc=request):
		return None
	rfq = frappe.get_doc("Request for Quotation", request)
	answers = _answers([request]) if frappe.has_permission("Supplier Quotation", "read") else {}
	quoted = {
		one.name: one
		for one in frappe.get_all(
			"Supplier Quotation",
			filters={"name": ["in", [one.name for one in answers.values()] or [""]]},
			fields=["name", "supplier", "currency", "grand_total", "base_grand_total", "valid_till", "status", "docstatus"],
		)
	}
	rates: dict = {}
	for row in frappe.get_all(
		"Supplier Quotation Item",
		filters={"parent": ["in", list(quoted) or [""]], "request_for_quotation": request},
		fields=["parent", "item_code", "rate", "base_rate", "lead_time_days", "ordered_qty"],
	):
		rates[(row.parent, row.item_code)] = row
	ordered: dict = {}
	for row in rates.values():
		ordered[row.item_code] = ordered.get(row.item_code, 0) + flt(row.ordered_qty)
	suppliers = []
	for row in rfq.suppliers:
		quote = quoted.get((answers.get((request, row.supplier)) or {}).get("name"))
		suppliers.append(
			{
				"supplier": row.supplier,
				"name": row.supplier_name or row.supplier,
				"quote": quote.name if quote else None,
				"currency": quote.currency if quote else None,
				"total": flt(quote.grand_total) if quote else None,
				"base_total": flt(quote.base_grand_total) if quote else None,
				"valid_till": str(quote.valid_till) if quote and quote.valid_till else None,
				"status": quote.status if quote else None,
				"draft": bool(quote) and quote.docstatus == 0,
				"expired": bool(quote) and _expired(quote),
				"cheapest_on": 0,
			}
		)
	by_supplier = {one["supplier"]: one for one in suppliers}
	lines = []
	for item in rfq.items:
		offers = {}
		for one in suppliers:
			row = rates.get((one["quote"], item.item_code)) if one["quote"] else None
			if row:
				offers[one["supplier"]] = {
					"rate": flt(row.rate),
					"base_rate": flt(row.base_rate),
					"days": row.lead_time_days or None,
				}
		live = [(offer["base_rate"], supplier) for supplier, offer in offers.items() if not by_supplier[supplier]["expired"]]
		cheapest = min(live)[1] if live else None
		done = flt(ordered.get(item.item_code)) >= flt(item.stock_qty or item.qty)
		if cheapest and not done:
			by_supplier[cheapest]["cheapest_on"] += 1
		lines.append(
			{
				"item": item.item_code,
				"name": item.item_name or item.item_code,
				"qty": flt(item.qty),
				"uom": item.uom,
				"offers": offers,
				"cheapest": cheapest,
				"ordered": done,
			}
		)
	return {
		"name": rfq.name,
		"date": str(rfq.transaction_date) if rfq.transaction_date else None,
		"draft": rfq.docstatus == 0,
		"currency": frappe.get_cached_value("Company", rfq.company, "default_currency"),
		"requests": list(dict.fromkeys(row.material_request for row in rfq.items if row.material_request)),
		"suppliers": suppliers,
		"lines": lines,
	}


@frappe.whitelist(methods=["POST"])
def ask(request: str, suppliers: list | str, message: str | None = None, send: bool | int = 0) -> str:
	"""A request for quotation for what a material request still needs,
	asking each supplier named, made by ERPNext's own mapper. Sent, it is
	submitted and each supplier is mailed a link, as its form's Send Email
	does. Otherwise it is left a draft."""
	from erpnext.stock.doctype.material_request.mapper import make_request_for_quotation

	frappe.has_permission("Request for Quotation", "create", throw=True)
	frappe.has_permission("Material Request", "read", doc=request, throw=True)
	named = [one for one in dict.fromkeys(frappe.parse_json(suppliers) if isinstance(suppliers, str) else suppliers or []) if one]
	if not named:
		frappe.throw(_("Choose the suppliers to ask."))
	rfq = make_request_for_quotation(request)
	if not rfq.items:
		frappe.throw(_("Everything on {0} is ordered already.").format(request))
	rfq.transaction_date = today()
	if message:
		rfq.message_for_supplier = message
	rfq.set("suppliers", [])
	for one in named:
		rfq.append("suppliers", {"supplier": one, "send_email": 1})
	rfq.insert()
	if frappe.utils.cint(send):
		rfq.submit()
		from erpnext.buying.doctype.request_for_quotation.request_for_quotation import send_supplier_emails

		send_supplier_emails(rfq.name)
	return rfq.name


@frappe.whitelist(methods=["POST"])
def order_cheapest(request: str) -> list[str]:
	"""A draft purchase order to each supplier for the lines they are
	cheapest on, each made from their quote by ERPNext's own mapper, so the
	order carries the quote, the request and what is already ordered from
	it. Nothing is submitted."""
	from erpnext.buying.doctype.supplier_quotation.mapper import make_purchase_order

	frappe.has_permission("Purchase Order", "create", throw=True)
	said = compare(request)
	if not said:
		frappe.throw(_("No request for quotation the reader may see is {0}.").format(request))
	made = []
	for one in said["suppliers"]:
		if not one["quote"] or one["draft"] or one["expired"] or not one["cheapest_on"]:
			continue
		cheapest = {line["item"] for line in said["lines"] if line["cheapest"] == one["supplier"] and not line["ordered"]}
		rows = frappe.get_all(
			"Supplier Quotation Item",
			filters={"parent": one["quote"], "item_code": ["in", list(cheapest)], "request_for_quotation": request},
			pluck="name",
		)
		order = make_purchase_order(one["quote"], args={"filtered_children": rows})
		order.items = [row for row in order.items if flt(row.qty) > 0]
		if not order.items:
			continue
		for row in order.items:
			if not row.schedule_date or getdate(row.schedule_date) < getdate(today()):
				row.schedule_date = today()
		order.schedule_date = min(row.schedule_date for row in order.items)
		order.insert()
		made.append(order.name)
	if not made:
		frappe.throw(_("Everything quoted on {0} is ordered already.").format(request))
	return made


def _project(name: str | None) -> str | None:
	"""A project by its own name, as its page says it."""
	return (frappe.db.get_value("Project", name, "project_name") or name) if name else None


def _expired(quote) -> bool:
	"""ERPNext marks a quote Expired overnight; one whose day passed since is
	expired already."""
	return quote.status == "Expired" or (
		quote.status in ("Submitted", "Partially Ordered")
		and bool(quote.valid_till)
		and getdate(quote.valid_till) < getdate(today())
	)
