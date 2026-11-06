"""What OneInventory shows on the portal, read by OnePortal's engine
(one_portal/portal.py) through the one_portal hook: a customer's shipments,
and a supplier's quote requests, which they price and send there, their
quotes and their purchase orders. Each entry of KINDS is one kind of record,
in the keys one_portal/AGENTS.md lists."""

import re

import frappe
from frappe import _, _lt

from onedesk.one_portal import portal as engine


def _bought_steps(doc) -> list[tuple[str, bool]]:
	from frappe.utils import flt

	billed = flt(doc.per_billed) >= 100
	return [
		(_("Ordered"), True),
		(_("Delivered"), flt(doc.per_received) >= 100),
		(_("Invoiced"), billed),
		(_("Paid"), billed and not engine.owed("Purchase Invoice", "purchase_order", doc.name)),
	]


def _shipped_steps(doc) -> list[tuple[str, bool]]:
	from frappe.utils import flt

	return [(_("Shipped"), True), (_("Invoiced"), flt(doc.get("per_billed")) >= 100)]


def _quote_steps(doc) -> list[tuple[str, bool]]:
	ordered = _("Partly ordered") if doc.status == "Partially Ordered" else _("Ordered")
	return [(_("Sent"), True), (ordered, doc.status == "Ordered")]


def _create_invoice(doc, context) -> list[dict]:
	"""erpnext's own button for a supplier to bill a purchase order."""
	from urllib.parse import urlencode

	if not context.show_make_pi_button:
		return []
	return [
		{
			"label": _("Create Invoice"),
			"href": "/api/method/erpnext.buying.doctype.purchase_order.mapper.make_purchase_invoice_from_portal?"
			+ urlencode({"purchase_order_name": doc.name}),
		}
	]


KINDS = {
	"Delivery Note": {
		"transaction": True,
		"party": "customer",
		"icon": "truck",
		"said": {
			"To Bill": ("green", _lt("Delivered")),
			"Completed": ("green", _lt("Delivered")),
		},
		"chain": (
			(("Sales Order", "against_sales_order"),),
			(("Sales Invoice", "Sales Invoice Item", "delivery_note"),),
		),
		"steps": _shipped_steps,
		"ships": True,
	},
	"Request for Quotation": {
		"transaction": True,
		"own_page": True,
		"icon": "inbox",
		"called": _lt("Quote Request"),
		"columns": (_lt("Number"), _lt("Status"), _lt("Needed by")),
		"badge": lambda doc: ("green", _("Quoted")) if quoted(doc.name) else ("amber", _("To quote")),
		"figure": lambda doc: engine._date(doc.get("schedule_date")),
		"asks": (lambda doc: not quoted(doc.name), _lt("Answer")),
	},
	"Supplier Quotation": {
		"transaction": True,
		"party": "supplier",
		"icon": "file-pen-line",
		"called": _lt("Quote"),
		"said": {"Draft": ("blue", _lt("Sent"))},
		"chain": ((), (("Purchase Order", "Purchase Order Item", "supplier_quotation"),)),
		"ahead": ("valid_till", _lt("Valid until {0}")),
		"ended": ("Ordered", "Partially Ordered", "Lost"),
		"steps": _quote_steps,
		"terms_label": _lt("Notes"),
	},
	"Purchase Order": {
		"transaction": True,
		"party": "supplier",
		"icon": "shopping-cart",
		"said": {
			"To Pay": ("amber", _lt("Awaiting payment")),
			"To Receive and Bill": ("amber", _lt("To deliver")),
			"To Receive": ("amber", _lt("To deliver")),
			"To Bill": ("green", _lt("Delivered")),
		},
		"chain": (
			(("Supplier Quotation", "supplier_quotation"),),
			(("Purchase Invoice", "Purchase Invoice Item", "purchase_order"),),
		),
		"ahead": ("schedule_date", _lt("Delivery {0}")),
		"waiting": (
			("To Pay", "To Receive and Bill", "To Receive"),
			lambda n: _("{0} to deliver").format(n),
		),
		"asks": (lambda doc: doc.status in ("To Receive and Bill", "To Receive"), _lt("View")),
		"steps": _bought_steps,
		"actions": _create_invoice,
	},
}


def quoted(rfq: str) -> bool:
	"""Whether the reader's supplier has quoted for a request."""
	from erpnext.controllers.website_list_for_contact import get_customers_suppliers

	_customers, suppliers = get_customers_suppliers("Request for Quotation Supplier", frappe.session.user)
	if not suppliers:
		return False
	return bool(
		frappe.db.sql(
			"""select 1 from `tabSupplier Quotation` sq join `tabSupplier Quotation Item` sqi
			on sqi.parent = sq.name where sqi.request_for_quotation = %s and sq.supplier in %s
			and sq.docstatus < 2 limit 1""",
			(rfq, tuple(suppliers)),
		)
	)


@frappe.whitelist()
def rfq(name: str) -> dict:
	"""A quote request's page, through erpnext's own context, which refuses a
	request not sent to the reader's supplier: whether they have answered and
	with what, its facts, the buyer's message and terms, and the rows they
	price, with what the app needs to show amounts as they type."""
	from erpnext.templates.pages import rfq as page

	if engine._kind("rfq") != "Request for Quotation":
		raise frappe.PermissionError
	context = engine._opened("Request for Quotation", name, page)
	if not engine.mine("Request for Quotation", context.doc):
		raise frappe.PermissionError
	return rfq_page(context.doc, [one.name for one in context.doc.get("rfq_links") or []])


def sent(rfq: str, supplier: str) -> list[str]:
	"""The quotes a supplier sent for a request, as erpnext's page finds them."""
	return frappe.get_all(
		"Supplier Quotation",
		filters={
			"supplier": supplier,
			"docstatus": ("<", 2),
			"name": (
				"in",
				frappe.get_all(
					"Supplier Quotation Item", filters={"request_for_quotation": rfq}, pluck="parent"
				),
			),
		},
		pluck="name",
	)


def currency_for(doc, supplier: str | None) -> str:
	"""What a supplier quotes a request in: their own currency, else the
	company's."""
	return (supplier and frappe.get_cached_value("Supplier", supplier, "default_currency")) or frappe.get_cached_value(
		"Company", doc.company, "default_currency"
	)


def rfq_page(doc, sent: list[str], supplier: str | None = None) -> dict:
	"""A quote request's page for one supplier, with the quotes they sent."""
	from frappe.locale import get_number_format
	from frappe.utils import fmt_money, sanitize_html, strip_html

	quotes = []
	for one in sent:
		quote = frappe.db.get_value(
			"Supplier Quotation",
			one,
			["transaction_date", "status", "docstatus", "grand_total", "rounded_total", "currency"],
			as_dict=True,
		)
		tone, word = engine.status("Supplier Quotation", quote.status, quote.docstatus)
		quotes.append(
			{
				"name": one,
				"date": engine._date(quote.transaction_date),
				"status": word,
				"tone": tone,
				"total": fmt_money(quote.rounded_total or quote.grand_total, currency=quote.currency),
			}
		)
	facts = [{"label": _("Date"), "value": engine._date(doc.transaction_date)}]
	if doc.get("schedule_date"):
		facts.append({"label": _("Needed by"), "value": engine._date(doc.schedule_date)})
	if doc.get("shipping_address_display"):
		lines = re.sub(r"\s*<br\s*/?>\s*", "\n", doc.shipping_address_display)
		facts.append({"label": _("Ship to"), "value": strip_html(lines).strip(), "lines": True})
	currency = currency_for(doc, supplier or doc.get("supplier"))
	said = get_number_format()
	symbol = frappe.db.get_value("Currency", currency, "symbol") or currency
	return {
		"name": doc.name,
		"quoted": bool(quotes),
		"tone": "green" if quotes else "amber",
		"status": _("Quoted") if quotes else _("To quote"),
		"open": doc.docstatus == 1,
		"quotes": quotes,
		"facts": facts,
		"message": sanitize_html(doc.message_for_supplier) if doc.get("message_for_supplier") else "",
		"terms": sanitize_html(doc.terms) if doc.get("terms") else "",
		"rows": [
			{
				"name": row.name,
				"item": row.item_name or row.item_code,
				"about": engine._about(row),
				"qty": frappe.utils.flt(row.qty),
				"qty_said": engine.number(row.qty),
				"uom": _(row.uom or ""),
				"needed_by": engine._date(row.schedule_date)
				if row.schedule_date and row.schedule_date != doc.get("schedule_date")
				else "",
			}
			for row in doc.items
		],
		"money": {
			"symbol": symbol,
			"on_right": bool(frappe.db.get_value("Currency", currency, "symbol_on_right")),
			"decimal": said.decimal_separator,
			"group": said.thousands_separator,
			"precision": frappe.utils.cint(frappe.db.get_default("currency_precision") or said.precision),
		},
	}


def priced(rfq: str, rows: str | dict, notes: str | None = None, sending: bool = True, link=None):
	"""The supplier's quote for a request, built the way erpnext's own mapper
	builds it but not saved: the reader is checked to be one of the supplier's
	portal users and the request one sent to that supplier, and only each
	row's rate, quantity and discount come from the page. The taxes are the
	workspace's own (its templates, its Item Tax Templates and Tax Rules by
	the supplier's country), as on any quote it records. Through a signed
	link (one_portal/share.py) the supplier and contact are the link's.
	Returns the quote, the request, the supplier and the reader."""
	from erpnext.buying.doctype.request_for_quotation.mapper import (
		add_items,
		get_quotable_rfq,
		validate_existing_supplier_quotation,
	)
	from erpnext.templates.pages.rfq import check_supplier_has_docname_access, get_supplier
	from frappe.utils import flt

	user = frappe.session.user
	if link:
		supplier, contact = link.party, link.contact
	else:
		frappe.form_dict.doctype, frappe.form_dict.name = "Request for Quotation", rfq
		supplier = get_supplier()
		if (
			not supplier
			or not check_supplier_has_docname_access(supplier)
			or not frappe.db.exists("Portal User", {"parent": supplier, "user": user})
		):
			frappe.throw(_("Not Permitted"), frappe.PermissionError)
		if not engine.mine("Request for Quotation", frappe._dict(name=rfq)):
			frappe.throw(_("Not Permitted"), frappe.PermissionError)
		contact = engine._contact_of(user, "Supplier", supplier)
	if frappe.db.get_value("Request for Quotation", rfq, "docstatus") != 1:
		frappe.throw(_("This request is closed."))
	doc = get_quotable_rfq(rfq, supplier)
	answered = frappe.parse_json(rows) or {}
	items, off = [], {}
	for row in doc.items:
		given = answered.get(row.name) or {}
		rate, qty = flt(given.get("rate")), flt(given.get("qty"))
		if rate > 0 and qty > 0:
			items.append({"name": row.name, "idx": row.idx, "rate": rate, "qty": qty})
			off[row.name] = (rate, min(max(flt(given.get("discount")), 0), 100))
	if not items:
		if sending:
			frappe.throw(_("Add a rate for at least one item."))
		return None, doc, supplier, user
	if sending:
		validate_existing_supplier_quotation(supplier, doc.name)

	supplier_doc = frappe.get_cached_doc("Supplier", supplier)
	quote = frappe.get_doc(
		{
			"doctype": "Supplier Quotation",
			"supplier": supplier,
			"company": doc.company,
			"currency": currency_for(doc, supplier),
			"buying_price_list": supplier_doc.default_price_list
			or frappe.db.get_single_value("Buying Settings", "buying_price_list"),
			"ignore_pricing_rule": 1,
			"contact_person": contact,
			"terms": notes or "",
		}
	)
	add_items(quote, supplier, doc, items)
	projects = {row.name: row.get("project_name") for row in doc.items}
	for row in quote.items:
		row.project = row.get("project") or projects.get(row.request_for_quotation_item)
	quote.flags.ignore_permissions = True
	frappe.session.user = "Administrator"
	try:
		quote.run_method("set_missing_values")
	finally:
		frappe.session.user = user
	for row in quote.items:
		rate, discount = off[row.request_for_quotation_item]
		row.price_list_rate = rate
		row.discount_percentage = discount
		row.discount_amount = flt(rate * discount / 100, row.precision("discount_amount"))
		row.rate = flt(rate - row.discount_amount, row.precision("rate"))
	return quote, doc, supplier, user


@frappe.whitelist()
def quote_preview(rfq: str, rows: str | dict) -> dict:
	"""What the supplier's quote comes to as they price it, as erpnext will
	reckon it once sent: each row's discount, net amount and tax, the taxes
	and the grand total, every value as frappe formats it."""
	quote, _doc, _supplier, user = priced(rfq, rows, sending=False)
	return reckon(quote, user)


def reckon(quote, user: str) -> dict:
	"""A quote's rows, taxes and totals as erpnext reckons them, unsaved."""
	from frappe.utils import flt, fmt_money

	if not quote:
		return {"rows": {}, "taxes": [], "net": "", "total": ""}
	frappe.session.user = "Administrator"
	try:
		quote.calculate_taxes_and_totals()
	finally:
		frappe.session.user = user
	taxed = {}
	for one in quote.get("_item_wise_tax_details") or []:
		taxed.setdefault(one.item.request_for_quotation_item, []).append(one)

	def money(value) -> str:
		return fmt_money(value, currency=quote.currency)

	out = {}
	for row in quote.items:
		tax = taxed.get(row.request_for_quotation_item, [])
		rates = sorted({flt(one.rate) for one in tax if flt(one.rate)})
		out[row.request_for_quotation_item] = {
			"net": money(row.net_amount),
			"discount": money(row.discount_amount * row.qty) if row.discount_amount else "",
			"tax": money(sum(flt(one.amount) for one in tax)),
			"rate": " + ".join(f"{engine.number(one)}%" for one in rates),
		}
	return {
		"rows": out,
		"taxes": [
			{
				"label": re.sub(r"\s*@\s*[\d.]+\s*$", "", tax.description or "") or _("Tax"),
				"value": money(tax.tax_amount),
			}
			for tax in quote.get("taxes") or []
			if tax.tax_amount
		],
		"net": money(quote.net_total),
		"total": money(quote.rounded_total or quote.grand_total),
	}


@frappe.whitelist(methods=["POST"])
def send_quote(rfq: str, rows: str | dict, notes: str | None = None) -> str:
	"""The supplier's answer to a quote request (`priced`), saved as theirs,
	and whoever asked told."""
	return send(*priced(rfq, rows, notes))


def send(quote, doc, supplier: str, user: str) -> str:
	"""A quote saved as the supplier's, and whoever asked told."""
	frappe.session.user = "Administrator"
	try:
		quote.insert()
	finally:
		frappe.session.user = user
	user = user if user != "Guest" else "Administrator"
	quote.db_set({"owner": user, "modified_by": user}, update_modified=False)

	from onedesk.one_inventory import tell

	tell.quote_received(doc, quote, user, supplier)
	return quote.name
