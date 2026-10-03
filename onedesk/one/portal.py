"""The portal a workspace's customers and suppliers sign in to.

Frappe draws it: Portal Settings lists what each role sees (erpnext's
Quotations, Orders and Invoices for a customer; Requests for Quotation and
Purchase Orders for a supplier), frappe's `portal` page lists a kind of
record through the kind's own `get_list_context`, and a row template draws
each row. One's look replaces the templates only (www/portal.html and the row
templates under templates/includes); what is listed, and for whom, stays
erpnext's and frappe's.

The page's Python is frappe's own when it lists a kind of record (its
ListPage asks for frappe's module by name), so what the template needs beyond
frappe's context comes from the Jinja methods here.
"""

import re

import frappe
from frappe import _, _lt
from frappe.website.utils import get_portal_sidebar_items

#: Portal Settings rows One has no use for: Issue has no place in One, and a
#: Material Request is the workspace's own, not something a customer raises.
OFF = ("/issues", "/material-requests")

#: Portal Settings rows renamed in plain words: erpnext names a supplier's tabs
#: after its doctypes.
TITLES = {"/rfq": "Quote Requests", "/supplier-quotations": "Quotes"}

#: The same titles, for translation: the rows hold the English, and a tab's
#: title is translated as it is drawn.
SAID = (_lt("Quote Requests"), _lt("Quotes"))

#: erpnext's indicator colours, as frappe-ui's Badge themes them.
TONES = {"green": "green", "blue": "blue", "orange": "amber", "yellow": "amber", "red": "red"}

#: Each tab's Lucide icon (frappe's sprite, on every web page).
ICONS = {
	"/project": "folder-kanban",
	"/quotations": "file-text",
	"/orders": "package",
	"/invoices": "receipt",
	"/shipments": "truck",
	"/addresses": "map-pin",
	"/timesheets": "clock",
	"/rfq": "inbox",
	"/supplier-quotations": "file-pen-line",
	"/purchase-orders": "shopping-cart",
	"/purchase-invoices": "receipt",
}

#: A list's columns, by the row template that draws it, as frappe-ui's
#: ListView heads them.
COLUMNS = {
	"templates/includes/transaction_row.html": (_lt("Number"), _lt("Status"), _lt("Total")),
	"templates/includes/projects/project_row.html": (_lt("Project"), _lt("Status"), _lt("Progress")),
	"templates/includes/timesheet/timesheet_row.html": (_lt("Timesheet"), _lt("Status"), _lt("Hours")),
}

#: How many of a kind the home counts before it says "100+".
COUNTED = 100

#: The states of a kind that wait on the reader, and how the home says so.
WAITING = {
	"Sales Invoice": (("Unpaid", "Overdue", "Partly Paid"), lambda n: _("{0} to pay").format(n)),
	"Purchase Order": (("To Receive and Bill", "To Receive"), lambda n: _("{0} to deliver").format(n)),
}


def one_portal_tabs() -> list[dict]:
	"""The portal's tabs, from Portal Settings by the reader's roles, the one
	being read marked."""
	request = getattr(frappe.local, "request", None)
	here = "/" + (request.path.strip("/").split("/")[0] if request else "")
	return [
		{
			"title": _(item.get("title")),
			"route": item.get("route"),
			"icon": ICONS.get(item.get("route"), "file-text"),
			"current": item.get("route") == here,
		}
		for item in get_portal_sidebar_items()
		if item.get("route")
	]


def one_portal_me() -> dict:
	"""Who is signed in, for the head's avatar and its menu, and the customer
	or supplier they sign in for, which the sidebar's header names."""
	user = frappe.session.user
	name = frappe.utils.get_fullname(user) or user
	party = frappe.db.get_value(
		"Portal User", {"user": user, "parenttype": ("in", PARTIES)}, ["parenttype", "parent"], as_dict=True
	)
	title = ""
	if party:
		field = "customer_name" if party.parenttype == "Customer" else "supplier_name"
		title = frappe.db.get_value(party.parenttype, party.parent, field) or party.parent
	return {
		"name": name,
		"email": user,
		"initials": "".join(w[0] for w in name.split()[:2]).upper(),
		"party": title,
	}


def one_portal_columns(row_template: str | None) -> list[str]:
	"""A list's column heads (COLUMNS), or none for a kind One has no row of
	its own for."""
	return [str(one) for one in COLUMNS.get(row_template or "", ())]


def one_portal_tone(colour: str | None) -> str:
	"""The pill an erpnext indicator colour is drawn as."""
	return TONES.get((colour or "").strip(), "gray")


#: How a state reads to the portal's reader where erpnext's word is written
#: for the workspace: a supplier's quote the buyer has yet to take up is, to
#: the supplier, sent.
SAID_TO_READER = {("Supplier Quotation", "Draft"): ("blue", _lt("Sent"))}


def one_portal_status(doctype: str, status: str | None, docstatus: int = 1, colour: str | None = None):
	"""A record's state as the portal's Badge says it: its tone and its word."""
	if said := SAID_TO_READER.get((doctype, status)):
		return said[0], str(said[1])
	tone = one_portal_tone(colour or ("blue" if docstatus == 1 else "gray"))
	return tone, _(status or "Submitted")


def one_portal_quoted(rfq: str) -> bool:
	"""Whether the reader's supplier has quoted for a request (the list's
	badge, as the request's own page says it)."""
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


def one_portal_home() -> list[dict]:
	"""What the reader has, a row a tab with anything in it: how many of each
	kind are theirs, read the way the tab's own list reads them, and how many
	wait on them (WAITING)."""
	from frappe.www.list import get_list_data_for_context

	rows = []
	for item in get_portal_sidebar_items():
		doctype = item.get("reference_doctype")
		if not doctype:
			continue
		try:
			found = get_list_data_for_context(None, doctype, limit=COUNTED + 1)
		except frappe.PermissionError:
			continue
		if not found:
			continue
		states, say = WAITING.get(doctype, ((), None))
		waiting = sum(
			1
			for one in found
			if (one.get("status") if isinstance(one, dict) else getattr(one, "status", None)) in states
		)
		rows.append(
			{
				"title": _(item.get("title")),
				"route": item.get("route"),
				"icon": ICONS.get(item.get("route"), "file-text"),
				"count": f"{COUNTED}+" if len(found) > COUNTED else str(len(found)),
				"waiting": say(waiting) if waiting else "",
			}
		)
	return rows


#: A record page's facts, in order: the field, and how the page names it.
#: Only those the record has are said.
FACTS = (
	("transaction_date", _lt("Date")),
	("posting_date", _lt("Date")),
	("valid_till", _lt("Valid until")),
	("delivery_date", _lt("Delivery")),
	("schedule_date", _lt("Delivery")),
	("due_date", _lt("Due")),
	("po_no", _lt("Your reference")),
	("bill_no", _lt("Your reference")),
)

#: Kinds a reader pays: once part is paid, their page says what is paid and
#: what is left.
OWED = ("Sales Invoice", "Purchase Invoice")


def one_portal_record(doc) -> dict:
	"""What a record's page shows beyond its items (www/order.html): its
	status as a Badge, its facts (FACTS), where it goes, its totals and its
	terms."""
	from frappe.utils import fmt_money, global_date_format, sanitize_html, strip_html

	said, facts = set(), []
	for field, label in FACTS:
		value = doc.get(field)
		if not value or str(label) in said:
			continue
		said.add(str(label))
		dated = doc.meta.get_field(field) and doc.meta.get_field(field).fieldtype == "Date"
		facts.append({"label": str(label), "value": global_date_format(value) if dated else str(value)})
	address = doc.get("shipping_address") or doc.get("address_display")
	if address and doc.doctype in ("Sales Order", "Delivery Note", "Quotation"):
		lines = re.sub(r"<br\s*/?>", "\n", address)
		facts.append({"label": _("Ship to"), "value": strip_html(lines).strip(), "lines": True})

	totals = []
	if doc.get("taxes") or doc.get("discount_amount"):
		totals.append({"label": _("Subtotal"), "value": doc.get_formatted("total")})
	if doc.get("discount_amount"):
		totals.append(
			{"label": _("Discount"), "value": fmt_money(-doc.discount_amount, currency=doc.currency)}
		)
	for tax in doc.get("taxes") or []:
		if tax.tax_amount:
			totals.append({"label": tax.description, "value": tax.get_formatted("tax_amount")})
	total = (
		"rounded_total"
		if doc.get("rounded_total") and not doc.get("disable_rounded_total")
		else "grand_total"
	)
	totals.append({"label": _("Total"), "value": doc.get_formatted(total), "strong": True})
	if doc.doctype in OWED and doc.docstatus == 1:
		left = doc.get("outstanding_amount") or 0
		paid = (doc.get(total) or 0) - left
		if paid and left:
			totals.append({"label": _("Paid"), "value": fmt_money(paid, currency=doc.currency)})
			totals.append(
				{"label": _("To pay"), "value": doc.get_formatted("outstanding_amount"), "strong": True}
			)

	tone, status = one_portal_status(
		doc.doctype,
		doc.get("indicator_title") or doc.get("status"),
		doc.docstatus,
		doc.get("indicator_color"),
	)
	return {
		"tone": tone,
		"status": status,
		"facts": facts,
		"totals": totals,
		"terms": sanitize_html(doc.terms) if doc.get("terms") else "",
	}


def one_portal_rfq(doc) -> dict:
	"""What a quote request's page shows (www/rfq.html), after erpnext's own
	context has found the reader's supplier and their quotes (rfq_links):
	whether they have answered, its facts, the buyer's message and terms, and
	the rows they price."""
	from frappe.utils import fmt_money, global_date_format, sanitize_html, strip_html

	quotes = []
	for one in doc.get("rfq_links") or []:
		quote = frappe.db.get_value(
			"Supplier Quotation", one.name, ["transaction_date", "status", "docstatus"], as_dict=True
		)
		tone, status = one_portal_status("Supplier Quotation", quote.status, quote.docstatus)
		quotes.append(
			{
				"name": one.name,
				"date": global_date_format(quote.transaction_date),
				"status": status,
				"tone": tone,
			}
		)
	facts = [{"label": _("Date"), "value": global_date_format(doc.transaction_date)}]
	if doc.get("schedule_date"):
		facts.append({"label": _("Needed by"), "value": global_date_format(doc.schedule_date)})
	if doc.get("shipping_address_display"):
		lines = re.sub(r"<br\s*/?>", "\n", doc.shipping_address_display)
		facts.append({"label": _("Ship to"), "value": strip_html(lines).strip(), "lines": True})
	rows = []
	for row in doc.items:
		about = strip_html(row.description or "").strip()
		rows.append(
			{
				"name": row.name,
				"item": row.item_name or row.item_code,
				"about": about if about and about != (row.item_name or row.item_code) else "",
				"qty": int(row.qty) if row.qty == int(row.qty) else row.qty,
				"qty_said": frappe.format_value(row.qty, {"fieldtype": "Float"}),
				"uom": _(row.uom or ""),
				"needed_by": global_date_format(row.schedule_date)
				if row.schedule_date and row.schedule_date != doc.get("schedule_date")
				else "",
			}
		)
	return {
		"quoted": bool(quotes),
		"tone": "green" if quotes else "amber",
		"status": _("Quoted") if quotes else _("To quote"),
		"quotes": quotes,
		"facts": facts,
		"message": sanitize_html(doc.message_for_supplier) if doc.get("message_for_supplier") else "",
		"terms": sanitize_html(doc.terms) if doc.get("terms") else "",
		"rows": rows,
		"zero": fmt_money(0, currency=doc.get("currency")),
	}


@frappe.whitelist(methods=["POST"])
def send_quote(rfq: str, rows: str | dict, notes: str | None = None) -> str:
	"""The supplier's answer to a quote request: a rate (and the quantity they
	can supply) for each row they price, and their notes. Everything else is
	read from the request itself, never from the page.

	erpnext's own mapper (create_supplier_quotation) cannot finish for a
	portal user: filling the quote's defaults reads each Item, which a
	supplier may not. So its steps are taken here: the reader is checked to be
	one of the supplier's portal users, the request to be one sent to that
	supplier, and then, as frappe's web form does for a save it has already
	authorized, the quote is made with the session's user switched, owned by
	the supplier's user."""
	from erpnext.buying.doctype.request_for_quotation.mapper import (
		add_items,
		validate_existing_supplier_quotation,
	)
	from erpnext.templates.pages.rfq import check_supplier_has_docname_access, get_supplier
	from frappe.utils import flt

	user = frappe.session.user
	# erpnext's page reads which request it is on from the form.
	frappe.form_dict.doctype, frappe.form_dict.name = "Request for Quotation", rfq
	supplier = get_supplier()
	if (
		not supplier
		or not check_supplier_has_docname_access(supplier)
		or not frappe.db.exists("Portal User", {"parent": supplier, "user": user})
	):
		frappe.throw(_("Not Permitted"), frappe.PermissionError)
	doc = frappe.get_doc("Request for Quotation", rfq)
	if doc.docstatus != 1:
		frappe.throw(_("This request is closed."))
	answered = frappe.parse_json(rows) or {}
	items = []
	for row in doc.items:
		given = answered.get(row.name) or {}
		rate, qty = flt(given.get("rate")), flt(given.get("qty"))
		if rate <= 0 or qty <= 0:
			continue
		item = row.as_dict()
		item.update({"rate": rate, "qty": qty, "stock_qty": qty * flt(row.conversion_factor or 1)})
		items.append(item)
	if not items:
		frappe.throw(_("Add a rate for at least one item."))
	validate_existing_supplier_quotation(supplier, items)

	supplier_doc = frappe.get_cached_doc("Supplier", supplier)
	quote = frappe.get_doc(
		{
			"doctype": "Supplier Quotation",
			"supplier": supplier,
			"company": doc.company,
			"currency": supplier_doc.default_currency
			or frappe.get_cached_value("Company", doc.company, "default_currency"),
			"buying_price_list": supplier_doc.default_price_list
			or frappe.db.get_single_value("Buying Settings", "buying_price_list"),
			"terms": notes or "",
		}
	)
	add_items(quote, supplier, items)
	quote.flags.ignore_permissions = True
	frappe.session.user = "Administrator"
	try:
		quote.run_method("set_missing_values")
		quote.insert()
	finally:
		frappe.session.user = user
	# Saved with the user switched, the quote is the supplier's all the same.
	quote.db_set({"owner": user, "modified_by": user}, update_modified=False)

	from onedesk.one import notify

	notify.notify(
		"Quote Received",
		doc.owner,
		record=("Supplier Quotation", quote.name),
		sender=user,
		supplier=quote.supplier_name or supplier,
		request=doc.name,
		total=quote.get_formatted("grand_total"),
		items=", ".join(row.item_name or row.item_code for row in quote.items),
	)
	return quote.name


#: Who a contact's login may be a portal user of.
PARTIES = ("Customer", "Supplier")


def invited(doc, method=None) -> None:
	"""Contact on_update: a contact's login is a portal user of each customer
	and supplier the contact is for, which is what erpnext's lists read. Its
	own Invite as User makes the login and stops there."""
	if not doc.user or frappe.db.get_value("User", doc.user, "user_type") != "Website User":
		return
	for link in doc.links or []:
		if link.link_doctype not in PARTIES:
			continue
		if frappe.db.exists(
			"Portal User", {"parenttype": link.link_doctype, "parent": link.link_name, "user": doc.user}
		):
			continue
		party = frappe.get_doc(link.link_doctype, link.link_name)
		party.append("portal_users", {"user": doc.user})
		party.flags.ignore_permissions = True
		party.save()


def settle() -> None:
	"""Turn off the Portal Settings rows One has no use for (OFF) and name the
	supplier's tabs plainly (TITLES). An administrator who turns one back on
	keeps it until the next install."""
	for route in OFF:
		frappe.db.set_value("Portal Menu Item", {"parent": "Portal Settings", "route": route}, "enabled", 0)
	for route, title in TITLES.items():
		frappe.db.set_value("Portal Menu Item", {"parent": "Portal Settings", "route": route}, "title", title)
	frappe.cache.delete_key("portal_menu_items")
