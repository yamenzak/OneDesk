"""The portal a workspace's customers and suppliers sign in to: a frappe-ui
app (frontend/portal), served at /portal by www/portal.py.

What is listed, and for whom, stays erpnext's and frappe's: the tabs are
Portal Settings by role, a list is the kind's own list context, a record is
erpnext's record page's context, which checks the reader may see it. This
module turns those into what the app draws, formatted as frappe formats them.
"""

import re
from urllib.parse import urlencode

import frappe
from frappe import _, _lt
from frappe.website.utils import get_portal_sidebar_items

#: Portal Settings rows One has no use for: Issue has no place in One, and a
#: Material Request is the workspace's own, not something a customer raises.
OFF = ("/issues", "/material-requests")

#: Portal Settings rows renamed in plain words: erpnext names a supplier's tabs
#: after its doctypes.
TITLES = {"/rfq": "Quote Requests", "/supplier-quotations": "Quotes"}

#: The web forms a portal reader fills in, in plain words: an address's
#: button. frappe's account deletion form is not one of them: a portal
#: reader asks under Your Data (ACCOUNT), as everybody else does.
FORMS = {"addresses": {"button_label": "Save Address"}}

#: The same titles and words, for translation: the records hold the English,
#: and each is translated as it is drawn.
SAID = (_lt("Quote Requests"), _lt("Quotes"), _lt("Save Address"))

#: Where a Portal Settings route lives in the app, where the two differ.
PATHS = {"/project": "projects"}

#: Each tab's Lucide icon.
ICONS = {
	"projects": "folder-kanban",
	"quotations": "file-text",
	"orders": "package",
	"invoices": "receipt",
	"shipments": "truck",
	"addresses": "map-pin",
	"timesheets": "clock",
	"rfq": "inbox",
	"supplier-quotations": "file-pen-line",
	"purchase-orders": "shopping-cart",
	"purchase-invoices": "receipt",
}

#: The reader's own pages, under Account, as (path, title, icon).
ACCOUNT = (
	("profile", _lt("Profile"), "user"),
	("password", _lt("Password"), "key-round"),
	("your-data", _lt("Your Data"), "shield-check"),
	("apps", _lt("Third Party Apps"), "plug"),
)

#: The kinds erpnext lists as transactions, each with a page of its own.
TRANSACTIONS = (
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Delivery Note",
	"Request for Quotation",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Invoice",
)

#: A list's column heads, by kind; any other kind has the first.
COLUMNS = {
	None: (_lt("Number"), _lt("Status"), _lt("Total")),
	"Request for Quotation": (_lt("Number"), _lt("Status"), _lt("Needed by")),
	"Project": (_lt("Project"), _lt("Status"), _lt("Progress")),
	"Timesheet": (_lt("Timesheet"), _lt("Status"), _lt("Hours")),
	"Address": (_lt("Address"), _lt("Type"), _lt("City")),
}

#: A list's button for adding one, where the reader may.
ADD = {"Address": ("addresses/new", _lt("Add Address"))}

#: How many rows a list gives at a time.
PAGE = 20

#: How many of a kind Home counts before it says "100+".
COUNTED = 100

#: The states of a kind that wait on the reader, and how Home says so.
WAITING = {
	"Sales Invoice": (("Unpaid", "Overdue", "Partly Paid"), lambda n: _("{0} to pay").format(n)),
	"Purchase Order": (
		("To Pay", "To Receive and Bill", "To Receive"),
		lambda n: _("{0} to deliver").format(n),
	),
}

#: erpnext's indicator colours, as frappe-ui's Badge themes them.
TONES = {"green": "green", "blue": "blue", "orange": "amber", "yellow": "amber", "red": "red"}

#: How a state reads to the portal's reader where erpnext's word is written
#: for the workspace: a supplier's quote the buyer has yet to take up is, to
#: the supplier, sent.
SAID_TO_READER = {
	("Supplier Quotation", "Draft"): ("blue", _lt("Sent")),
	# A customer's order and shipment, as the customer sees them: erpnext names
	# them by what the workspace still has to do (deliver, bill).
	("Sales Order", "To Deliver and Bill"): ("blue", _lt("Confirmed")),
	("Sales Order", "To Deliver"): ("blue", _lt("Confirmed")),
	("Sales Order", "To Bill"): ("green", _lt("Delivered")),
	("Delivery Note", "To Bill"): ("green", _lt("Delivered")),
	("Delivery Note", "Completed"): ("green", _lt("Delivered")),
	# A supplier's purchase order, as the supplier sees it: what they still
	# have to deliver. An advance is due before they deliver (erpnext's To Pay).
	("Purchase Order", "To Pay"): ("amber", _lt("Awaiting payment")),
	("Purchase Order", "To Receive and Bill"): ("amber", _lt("To deliver")),
	("Purchase Order", "To Receive"): ("amber", _lt("To deliver")),
	("Purchase Order", "To Bill"): ("green", _lt("Delivered")),
}

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


def _path(route: str) -> str:
	return PATHS.get(route, route.strip("/"))


def _kinds() -> dict[str, dict]:
	"""The reader's tabs, from Portal Settings by their roles, by their path."""
	return {
		_path(item.get("route")): item
		for item in get_portal_sidebar_items()
		if item.get("route") and item.get("reference_doctype")
	}


def reads(user: str | None = None) -> bool:
	"""Whether the portal is where this person works: signed in, without a
	desk, with a tab. frappe's own account pages send them here."""
	user = user or frappe.session.user
	if user == "Guest" or frappe.get_cached_value("User", user, "user_type") != "Website User":
		return False
	return bool(_kinds())


def _kind(path: str) -> str:
	"""The doctype a tab lists; refuses one the reader has no tab for."""
	item = _kinds().get(path)
	if not item:
		raise frappe.PermissionError
	return item["reference_doctype"]


def _me() -> dict:
	"""Who is signed in, and the customer or supplier they sign in for."""
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
		"image": frappe.db.get_value("User", user, "user_image"),
		"party": title,
	}


def boot() -> dict:
	"""What the app starts with (www/portal.py): the reader, their tabs, their
	account's pages, and frappe's translations in their language."""
	from frappe.boot import load_translations
	from frappe.utils.jinja_globals import is_rtl

	apps = frappe.db.exists("OAuth Bearer Token", {"user": frappe.session.user})
	said = frappe._dict(
		lang=frappe.local.lang,
		rtl=is_rtl(),
		site_name=frappe.local.site,
		socketio_port=frappe.conf.socketio_port,
		me=_me(),
		tabs=[
			{"path": path, "title": _(item.get("title")), "icon": ICONS.get(path, "file-text")}
			for path, item in _kinds().items()
		],
		account=[
			{"path": path, "title": str(title), "icon": icon}
			for path, title, icon in ACCOUNT
			if path != "apps" or apps
		],
	)
	load_translations(said)
	return said


def _tone(colour: str | None) -> str:
	return TONES.get((colour or "").strip(), "gray")


def status(doctype: str, state: str | None, docstatus: int = 1, colour: str | None = None) -> tuple[str, str]:
	"""A record's state as the portal's Badge says it: its theme and its word."""
	if said := SAID_TO_READER.get((doctype, state)):
		return said[0], str(said[1])
	return _tone(colour or ("blue" if docstatus == 1 else "gray")), _(state or "Submitted")


def number(value) -> str:
	"""A quantity or hours as a person writes them: 10, not 10.00; 2.5, not
	2.500. In the workspace's number format."""
	from frappe.utils import flt, fmt_money

	value = flt(value, 3)
	if value == int(value):
		return fmt_money(value, precision=0)
	return fmt_money(value, precision=len(f"{value}".split(".")[1]))


def _date(value) -> str:
	return frappe.format(value, {"fieldtype": "Date"}) if value else ""


def _quoted(rfq: str) -> bool:
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


def _field(row, field: str):
	return row.get(field) if isinstance(row, dict) else getattr(row, field, None)


def _row(path: str, doctype: str, doc) -> dict | None:
	"""One row of a list, as the app draws it: its name, a line under it, its
	Badge, the figure at its end and where it opens."""
	if doctype in TRANSACTIONS:
		when = doc.get("transaction_date") or doc.get("posting_date") or doc.modified
		line = " · ".join(one for one in (_date(when), doc.get("items_preview")) if one)
		if doctype == "Request for Quotation":
			quoted = _quoted(doc.name)
			tone, word = ("green", _("Quoted")) if quoted else ("amber", _("To quote"))
			figure = _date(doc.get("schedule_date"))
		else:
			tone, word = status(doctype, doc.status, doc.docstatus, doc.get("indicator_color"))
			total = (
				"rounded_total"
				if doc.get("rounded_total") and not doc.get("disable_rounded_total")
				else "grand_total"
			)
			figure = doc.get_formatted(total) if doc.get(total) else ""
		return {
			"name": doc.name,
			"title": doc.name,
			"line": line,
			"tone": tone,
			"status": word,
			"figure": figure,
			"to": f"{path}/{doc.name}",
		}
	if doctype == "Project":
		from onedesk.one_project import portal as projects

		project = frappe.get_doc("Project", doc.name)
		ends = _("Ends {0}").format(_date(doc.expected_end_date)) if doc.get("expected_end_date") else ""
		share = projects.progress(project)[0] if projects.may_see(project) else 0
		return {
			"name": doc.name,
			"title": doc.get("project_name") or doc.name,
			"line": ends,
			"tone": "green" if doc.status == "Completed" else "blue",
			"status": _(doc.status),
			"figure": f"{share}%",
			"to": f"projects/{doc.name}",
		}
	if doctype == "Timesheet":
		sheet = _timesheet(doc.name)
		tone = {"Billed": "green", "Cancelled": "red", "Submitted": "blue"}.get(doc.status, "gray")
		return {
			"name": doc.name,
			"title": doc.name,
			"line": " · ".join(one for one in (sheet["projects"], sheet["activities"]) if one),
			"tone": tone,
			"status": _(doc.status),
			"figure": _("{0} h").format(number(sheet["hours"])),
			"to": f"projects/{sheet['project']}" if sheet["project"] else None,
		}
	if doctype == "Address":
		where = ", ".join(
			one for one in (doc.address_line1, doc.address_line2, doc.state, doc.country) if one
		)
		return {
			"name": doc.name,
			"title": doc.get("address_title") or doc.name,
			"line": where,
			"tone": "gray",
			"status": _(doc.address_type) if doc.get("address_type") else "",
			"figure": doc.get("city") or "",
			"to": f"addresses/{doc.name}",
		}
	meta = frappe.get_meta(doctype)
	shown = [df for df in meta.fields if df.in_list_view][:3]
	return {
		"name": _field(doc, "name"),
		"title": _field(doc, meta.title_field or "name") or _field(doc, "name"),
		"line": " · ".join(
			frappe.utils.strip_html(frappe.format(_field(doc, df.fieldname), df, doc=doc))
			for df in shown
			if _field(doc, df.fieldname)
		),
		"tone": "gray",
		"status": "",
		"figure": "",
		"to": None,
	}


def _timesheet(name: str) -> dict:
	"""A timesheet as the portal lists it: the projects it is for, what was
	done, and its hours."""
	rows = frappe.get_all(
		"Timesheet Detail",
		filters={"parent": name, "parenttype": "Timesheet"},
		fields=["project", "activity_type", "hours", "billing_hours"],
		order_by="idx",
	)
	projects = list(dict.fromkeys(row.project for row in rows if row.project))
	titles = dict(
		frappe.get_all(
			"Project", filters={"name": ("in", projects)}, fields=["name", "project_name"], as_list=True
		)
	)
	return {
		"projects": ", ".join(titles.get(one) or one for one in projects),
		"activities": ", ".join(dict.fromkeys(_(row.activity_type) for row in rows if row.activity_type)),
		"hours": sum(frappe.utils.flt(row.billing_hours or row.hours) for row in rows),
		"project": projects[0] if len(projects) == 1 else None,
	}


@frappe.whitelist()
def rows(kind: str, txt: str | None = None, start: int = 0) -> dict:
	"""A tab's list, a page at a time, as its kind's own list context gives it
	to the reader, searched by `txt`: its column heads, its rows, whether there
	are more, and its Add button where it has one."""
	from frappe.www.list import get_list_data_for_context

	doctype = _kind(kind)
	start = frappe.utils.cint(start)
	found = get_list_data_for_context(None, doctype, txt=txt or None, limit_start=start, limit=PAGE + 1)
	more = len(found) > PAGE
	# erpnext lists a timesheet once per time entry: each record once.
	found = list({_field(one, "name"): one for one in found[:PAGE]}.values())
	add = ADD.get(doctype)
	return {
		"doctype": doctype,
		"columns": [str(one) for one in COLUMNS.get(doctype) or COLUMNS[None]],
		"rows": [row for row in (_row(kind, doctype, one) for one in found) if row],
		"more": more,
		"add": {"to": add[0], "label": str(add[1])} if add else None,
	}


@frappe.whitelist()
def home() -> list[dict]:
	"""What the reader has, a row a tab with anything in it: how many of each
	kind are theirs, read the way the tab's own list reads them, and how many
	wait on them (WAITING)."""
	from frappe.www.list import get_list_data_for_context

	out = []
	for path, item in _kinds().items():
		doctype = item["reference_doctype"]
		try:
			found = get_list_data_for_context(None, doctype, limit=COUNTED + 1)
		except frappe.PermissionError:
			continue
		if not found:
			continue
		found = list({_field(one, "name"): one for one in found}.values())
		states, say = WAITING.get(doctype, ((), None))
		waiting = sum(1 for one in found if _field(one, "status") in states)
		out.append(
			{
				"path": path,
				"title": _(item.get("title")),
				"icon": ICONS.get(path, "file-text"),
				"count": f"{COUNTED}+" if len(found) > COUNTED else str(len(found)),
				"waiting": say(waiting) if waiting else "",
			}
		)
	return out


def _opened(doctype: str, name: str, page) -> frappe._dict:
	"""A record through erpnext's own page context, which reads it, checks the
	reader may see it and says what may be done with it."""
	frappe.form_dict.doctype, frappe.form_dict.name = doctype, name
	context = frappe._dict()
	page.get_context(context)
	return context


@frappe.whitelist()
def record(kind: str, name: str) -> dict:
	"""A quotation, order, invoice, shipment or purchase document's page: its
	Badge, its facts, its items, its totals, its terms and files, and what the
	reader may do with it (Download PDF, Pay, Create Invoice)."""
	from erpnext.templates.pages import order
	from frappe.utils import fmt_money, sanitize_html, strip_html

	doctype = _kind(kind)
	if doctype not in TRANSACTIONS or doctype == "Request for Quotation":
		raise frappe.PermissionError
	context = _opened(doctype, name, order)
	doc = context.doc

	said, facts = set(), []
	for field, label in FACTS:
		value = doc.get(field)
		if not value or str(label) in said:
			continue
		said.add(str(label))
		facts.append({"label": str(label), "value": doc.get_formatted(field)})
	address = doc.get("shipping_address") or doc.get("address_display")
	if address and doctype in ("Sales Order", "Delivery Note", "Quotation"):
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
			# erpnext writes "VAT 5% @ 5.0" where the account names its rate.
			label = re.sub(r"\s*@\s*[\d.]+\s*$", "", tax.description or "") or _("Tax")
			totals.append({"label": label, "value": tax.get_formatted("tax_amount")})
	total = (
		"rounded_total"
		if doc.get("rounded_total") and not doc.get("disable_rounded_total")
		else "grand_total"
	)
	totals.append({"label": _("Total"), "value": doc.get_formatted(total), "strong": True})
	if doctype in OWED and doc.docstatus == 1:
		left = doc.get("outstanding_amount") or 0
		paid = (doc.get(total) or 0) - left
		if paid and left:
			totals.append({"label": _("Paid"), "value": fmt_money(paid, currency=doc.currency)})
			totals.append(
				{"label": _("To pay"), "value": doc.get_formatted("outstanding_amount"), "strong": True}
			)

	# The record's own status, as its list says it, before erpnext's page's
	# indicator, which says Submitted of an ordered quotation.
	tone, word = status(
		doctype, doc.get("status") or doc.get("indicator_title"), doc.docstatus, doc.get("indicator_color")
	)
	quoted = doctype == "Supplier Quotation"
	actions = []
	if doc.docstatus == 1:
		actions.append(
			{
				"label": _("Download PDF"),
				"icon": "download",
				"href": "/api/method/frappe.utils.print_format.download_pdf?"
				+ urlencode({"doctype": doctype, "name": doc.name, "format": context.print_format}),
			}
		)
	if doctype == "Purchase Order" and context.show_make_pi_button:
		actions.append(
			{
				"label": _("Create Invoice"),
				"href": "/api/method/erpnext.buying.doctype.purchase_order.mapper.make_purchase_invoice_from_portal?"
				+ urlencode({"purchase_order_name": doc.name}),
			}
		)
	if context.show_pay_button:
		actions.append(
			{
				"label": _("Pay {0}").format(fmt_money(context.pay_amount, currency=doc.currency)),
				"solid": True,
				"href": "/api/method/erpnext.accounts.doctype.payment_request.payment_request.make_payment_request?"
				+ urlencode({"dn": doc.name, "dt": doctype, "submit_doc": 1, "order_type": "Shopping Cart"}),
			}
		)
	return {
		"name": doc.name,
		"tone": tone,
		"status": word,
		"facts": facts,
		"items": [
			{
				"item": row.item_name or row.item_code,
				"about": _about(row),
				"qty": number(row.qty),
				"uom": _(row.get("uom") or row.get("stock_uom") or ""),
				"rate": row.get_formatted("rate", doc),
				"amount": row.get_formatted("amount", doc),
			}
			for row in doc.items
		],
		"totals": totals,
		"terms_label": _("Notes") if quoted else _("Terms"),
		"terms": sanitize_html(doc.terms) if doc.get("terms") else "",
		"files": [
			{"name": one.file_name, "url": one.file_url} for one in order.get_attachments(doctype, doc.name)
		],
		"actions": actions,
	}


def _about(row) -> str:
	from frappe.utils import strip_html

	about = strip_html(row.get("description") or "").strip()
	return about if about and about != (row.item_name or row.item_code) else ""


@frappe.whitelist()
def rfq(name: str) -> dict:
	"""A quote request's page, through erpnext's own context, which refuses a
	request not sent to the reader's supplier: whether they have answered and
	with what, its facts, the buyer's message and terms, and the rows they
	price, with what the app needs to show amounts as they type."""
	from erpnext.templates.pages import rfq as page
	from frappe.locale import get_number_format
	from frappe.utils import fmt_money, sanitize_html, strip_html

	if _kind("rfq") != "Request for Quotation":
		raise frappe.PermissionError
	context = _opened("Request for Quotation", name, page)
	doc = context.doc
	quotes = []
	for one in doc.get("rfq_links") or []:
		quote = frappe.db.get_value(
			"Supplier Quotation",
			one.name,
			["transaction_date", "status", "docstatus", "grand_total", "currency"],
			as_dict=True,
		)
		tone, word = status("Supplier Quotation", quote.status, quote.docstatus)
		quotes.append(
			{
				"name": one.name,
				"date": _date(quote.transaction_date),
				"status": word,
				"tone": tone,
				"total": fmt_money(quote.grand_total, currency=quote.currency),
			}
		)
	facts = [{"label": _("Date"), "value": _date(doc.transaction_date)}]
	if doc.get("schedule_date"):
		facts.append({"label": _("Needed by"), "value": _date(doc.schedule_date)})
	if doc.get("shipping_address_display"):
		lines = re.sub(r"<br\s*/?>", "\n", doc.shipping_address_display)
		facts.append({"label": _("Ship to"), "value": strip_html(lines).strip(), "lines": True})
	currency = doc.get("currency") or frappe.db.get_default("currency")
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
				"about": _about(row),
				"qty": frappe.utils.flt(row.qty),
				"qty_said": number(row.qty),
				"uom": _(row.uom or ""),
				"needed_by": _date(row.schedule_date)
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


#: The frappe web forms the portal fills in, by the page they are on: the
#: reader's profile (frappe's) and an address (erpnext's).
WEB_FORMS = {"profile": "edit-profile", "addresses": "addresses"}


@frappe.whitelist()
def form(page: str, name: str | None = None) -> dict:
	"""A web form's fields and the record it edits, through frappe's own
	get_form_data, which checks the reader may: the profile is the reader's,
	an address one of theirs or a new one."""
	from frappe.website.doctype.web_form.web_form import get_form_data

	web_form = WEB_FORMS.get(page)
	if not web_form:
		raise frappe.PermissionError
	doctype = frappe.db.get_value("Web Form", web_form, "doc_type")
	if page == "profile":
		name = frappe.session.user
	said = get_form_data(doctype, name, web_form)
	fields = []
	for one in said.web_form.web_form_fields:
		fields.append(
			{
				"fieldname": one.fieldname,
				"fieldtype": one.fieldtype,
				"label": _(one.label) if one.label else "",
				"reqd": one.reqd,
				"options": _choices(one),
			}
		)
	doc = said.get("doc")
	return {
		"web_form": web_form,
		"fields": fields,
		"doc": {one["fieldname"]: doc.get(one["fieldname"]) for one in fields if one["fieldname"]}
		| {"name": doc.name}
		if doc
		else {},
		"title": (doc.get("address_title") or doc.name) if doc and page == "addresses" else "",
	}


def _choices(field) -> list | None:
	"""A select's options, or a link's as frappe's web form found them (a list
	of values or of {value, label}, or a string a line each)."""
	if field.fieldtype not in ("Select", "Autocomplete"):
		return None
	options = field.options or []
	if isinstance(options, str):
		options = (
			frappe.parse_json(options)
			if options.startswith("[")
			else [one for one in options.split("\n") if one]
		)
	if field.fieldtype == "Select":
		return [{"value": one, "label": _(one)} for one in options]
	if not options and field.fieldname == "language":
		# A portal reader may not read Language, so frappe's own form offers
		# none: the languages the workspace has on, as its sign-in page does.
		return [
			{"value": one.name, "label": one.language_name}
			for one in frappe.get_all(
				"Language", filters={"enabled": 1}, fields=["name", "language_name"], order_by="language_name"
			)
		]
	return options


@frappe.whitelist()
def your_data() -> dict:
	"""What Your Data shows (one/privacy.py `state`), its dates said plainly."""
	from frappe.utils import pretty_date

	from onedesk.one import privacy

	said = privacy.state()
	copy, deletion = said["copy"], said["deletion"]
	return {
		"copy": {**copy, "on": pretty_date(copy["on"])} if copy else None,
		"deletion": {**deletion, "on": pretty_date(deletion["on"])} if deletion else None,
		"password": said["password"],
	}


@frappe.whitelist()
def apps() -> list[dict]:
	"""The apps the reader has let in, as frappe's Third Party Apps lists them;
	frappe's delete_client takes one away."""
	from frappe.utils import pretty_date
	from frappe.www.third_party_apps import get_first_login

	return [
		{
			"client": one.client,
			"name": frappe.db.get_value("OAuth Client", one.client, "app_name") or one.client,
			"since": pretty_date(get_first_login(one.client)),
		}
		for one in frappe.get_all(
			"OAuth Bearer Token",
			filters={"user": frappe.session.user},
			fields=["client"],
			distinct=True,
			order_by="creation",
		)
	]


@frappe.whitelist(methods=["POST"])
def send_quote(rfq: str, rows: str | dict, notes: str | None = None) -> str:
	"""The supplier's answer to a quote request: a rate (and the quantity they
	can supply) for each row they price, and their notes. Everything else is
	read from the request itself, never from the page."""
	from erpnext.buying.doctype.request_for_quotation.mapper import (
		add_items,
		get_quotable_rfq,
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
	if frappe.db.get_value("Request for Quotation", rfq, "docstatus") != 1:
		frappe.throw(_("This request is closed."))
	# erpnext's own check that the supplier was asked, and its row lookup,
	# which takes the item from the request and only the rate and quantity
	# from the supplier.
	doc = get_quotable_rfq(rfq, supplier)
	answered = frappe.parse_json(rows) or {}
	items = []
	for row in doc.items:
		given = answered.get(row.name) or {}
		rate, qty = flt(given.get("rate")), flt(given.get("qty"))
		if rate > 0 and qty > 0:
			items.append({"name": row.name, "idx": row.idx, "rate": rate, "qty": qty})
	if not items:
		frappe.throw(_("Add a rate for at least one item."))
	validate_existing_supplier_quotation(supplier, doc.name)

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
	add_items(quote, supplier, doc, items)
	# erpnext's rows leave out the project each request line is for, and an
	# order made from the quote is then refused against the material request
	# it came from. The quote names it as the request does.
	projects = {row.name: row.get("project_name") for row in doc.items}
	for row in quote.items:
		row.project = row.get("project") or projects.get(row.request_for_quotation_item)
	quote.flags.ignore_permissions = True
	frappe.session.user = "Administrator"
	try:
		quote.run_method("set_missing_values")
		quote.insert()
	finally:
		frappe.session.user = user
	# Saved with the user switched, the quote is the supplier's all the same.
	quote.db_set({"owner": user, "modified_by": user}, update_modified=False)

	from onedesk.one import tell

	tell.quote_received(doc, quote, user, supplier)
	return quote.name


#: Who a contact's login may be a portal user of.
PARTIES = ("Customer", "Supplier")


def invited(doc, method=None) -> None:
	"""Contact on_update: a contact's login is a portal user of each customer
	and supplier the contact is for, which is what erpnext's lists read, and
	holds the Customer or Supplier role its tabs are shown by (Portal
	Settings). erpnext gives the role only when its System Manager adds the
	row, and nobody on a workspace is one (one/roles.py), so both are added
	here: the row by itself, not by saving the whole customer, whose own
	rules (a workspace's server scripts) are not this contact's to meet."""
	if not doc.user or frappe.db.get_value("User", doc.user, "user_type") != "Website User":
		return
	wanted = set()
	for link in doc.links or []:
		if link.link_doctype not in PARTIES:
			continue
		wanted.add(link.link_doctype)
		where = {"parenttype": link.link_doctype, "parent": link.link_name, "parentfield": "portal_users"}
		if frappe.db.exists("Portal User", {**where, "user": doc.user}):
			continue
		row = frappe.get_doc({"doctype": "Portal User", **where, "user": doc.user})
		row.idx = frappe.db.count("Portal User", where) + 1
		row.db_insert()
	user = frappe.get_doc("User", doc.user)
	missing = wanted - {one.role for one in user.roles}
	if missing:
		user.flags.ignore_permissions = True
		user.add_roles(*sorted(missing))


def settle() -> None:
	"""Turn off the Portal Settings rows One has no use for (OFF), name the
	supplier's tabs plainly (TITLES), and put frappe's and erpnext's forms in
	plain words (FORMS). An administrator who turns one back on, or words a
	form their own way, keeps it until the next install."""
	for route in OFF:
		frappe.db.set_value("Portal Menu Item", {"parent": "Portal Settings", "route": route}, "enabled", 0)
	for route, title in TITLES.items():
		frappe.db.set_value("Portal Menu Item", {"parent": "Portal Settings", "route": route}, "title", title)
	for form, words in FORMS.items():
		if frappe.db.exists("Web Form", form):
			frappe.db.set_value("Web Form", form, words)
	frappe.cache.delete_key("portal_menu_items")


#: frappe's website stylesheet carries frappe-ui's dark values under
#: [data-theme=dark], which nothing on the website sets: this sets it from the
#: reader's own light or dark, before anything is drawn.
LIGHT_OR_DARK = (
	"<script>(()=>{const m=matchMedia('(prefers-color-scheme: dark)'),"
	"set=()=>document.documentElement.setAttribute('data-theme',m.matches?'dark':'light');"
	"set();m.addEventListener('change',set)})()</script>"
)


def light_or_dark(context):
	"""Every web page in the reader's light or dark, as the desk is."""
	context["head_include"] = (context.get("head_include") or "") + LIGHT_OR_DARK
