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
from frappe.model.document import Document
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
	# A quotation the customer turned down, in their word, not the team's.
	("Quotation", "Lost"): ("gray", _lt("Declined")),
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

#: A kind as one of them is called on the portal, where erpnext's name is
#: written for the workspace: to a supplier, its quotation is a quote.
CALLED = {
	"Request for Quotation": _lt("Quote Request"),
	"Supplier Quotation": _lt("Quote"),
}

#: Kinds a reader pays: once part is paid, their page says what is paid and
#: what is left.
OWED = ("Sales Invoice", "Purchase Invoice")


#: The kinds a record of may be hidden from some of its party's contacts on
#: the portal (`one_portal_hidden`, set on the desk record: `access`).
NARROWED = (
	"Quotation",
	"Sales Order",
	"Delivery Note",
	"Sales Invoice",
	"Request for Quotation",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Invoice",
)


def _contacts_of(user: str | None = None) -> set[str]:
	"""The contacts a reader signs in as."""
	user = user or frappe.session.user
	cache = frappe.local.flags.setdefault("one_portal_contacts", {})
	if user not in cache:
		cache[user] = set(frappe.get_all("Contact", filters={"user": user}, pluck="name"))
	return cache[user]


def _hidden(doctype: str, doc) -> set[str]:
	"""The contacts a record is hidden from on the portal."""
	if isinstance(doc, Document):
		value = doc.get("one_portal_hidden")
	else:
		value = frappe.db.get_value(doctype, _field(doc, "name"), "one_portal_hidden")
	return set(frappe.parse_json(value) or []) if value else set()


def _contact_of(user: str, party_type: str, party: str) -> str | None:
	"""The reader's contact at a customer or supplier."""
	linked = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "link_doctype": party_type, "link_name": party},
		pluck="parent",
	)
	return frappe.db.get_value("Contact", {"user": user, "name": ("in", linked)}, "name") if linked else None


def mine(doctype: str, doc, user: str | None = None) -> bool:
	"""Whether the reader sees a record as far as its own portal contacts go:
	every contact of the customer or supplier does, unless the record was
	hidden from them (`access`)."""
	if doctype not in NARROWED:
		return True
	hidden = _hidden(doctype, doc)
	return not hidden or not (_contacts_of(user) & hidden)


def has_website_permission(doc, ptype: str = "read", user: str | None = None, verbose: bool = False) -> bool:
	"""Beside erpnext's own (hooks.py), which lets every portal user of a
	customer or supplier read all of its records: a contact a record is
	hidden from reads it nowhere, on the portal, erpnext's pages or a PDF."""
	return mine(doc.doctype, doc, user)


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

	if frappe.session.user == "Guest":
		# A signed link's page (one/portal_share.py): nobody signed in, no tabs.
		said = frappe._dict(lang=frappe.local.lang, rtl=is_rtl(), guest=True, me={}, tabs=[], account=[])
		load_translations(said)
		return said
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
		names = list(dict.fromkeys(row.item_name or row.item_code for row in doc.get("items") or []))
		if doctype == "Request for Quotation":
			quoted = _quoted(doc.name)
			tone, word = ("green", _("Quoted")) if quoted else ("amber", _("To quote"))
			figure = _date(doc.get("schedule_date"))
		else:
			tone, word = status(doctype, doc.status, doc.docstatus, doc.get("indicator_color"))
			if doctype == "Quotation" and doc.status == "Open" and _accepted(doc.name):
				tone, word = "blue", _("Accepted")
			total = _total_field(doc)
			figure = doc.get_formatted(total) if doc.get(total) else ""
		return {
			"name": doc.name,
			"title": doc.name,
			"date": _date(when),
			"item": names[0] if names else "",
			"others": len(names) - 1 if names else 0,
			"line": " · ".join(one for one in (_date(when), doc.get("items_preview")) if one),
			"when": _next(doctype, doc, tone == "green"),
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


def _next(doctype: str, doc, done: bool) -> dict:
	"""The date a row of a list looks ahead to, and whether it has passed: a
	bill's due date, a quotation's last day, an order's delivery."""
	from frappe.utils import date_diff, today

	# A quote request's date has its own column, and a quotation answered or
	# ordered looks ahead to nothing.
	if done or doc.docstatus != 1 or doctype == "Request for Quotation":
		return {}
	if doctype in ("Quotation", "Supplier Quotation") and (
		doc.status in ("Ordered", "Partially Ordered", "Lost", "Expired", "Cancelled")
		or (doctype == "Quotation" and _accepted(doc.name))
	):
		return {}
	if doctype in OWED:
		if (doc.get("outstanding_amount") or 0) <= 0 or not doc.get("due_date"):
			return {}
		owed = [row.due_date for row in doc.get("payment_schedule") or [] if (row.outstanding or 0) > 0]
		due = min(owed) if owed else doc.due_date
		late = date_diff(today(), due)
		if late > 0:
			return {
				"text": _("{0} days overdue").format(late) if late != 1 else _("1 day overdue"),
				"late": True,
			}
		return {"text": _("Due {0}").format(_date(due))}
	field = {
		"Quotation": "valid_till",
		"Supplier Quotation": "valid_till",
		"Request for Quotation": "schedule_date",
	}.get(doctype, "delivery_date" if doctype == "Sales Order" else "schedule_date")
	if not doc.get(field):
		return {}
	label = (
		_("Valid until {0}")
		if field == "valid_till"
		else _("Needed by {0}")
		if doctype == "Request for Quotation"
		else _("Delivery {0}")
	)
	return {"text": label.format(_date(doc.get(field))), "late": date_diff(today(), doc.get(field)) > 0}


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
def rows(kind: str, txt: str | None = None, start: int = 0, state: str | None = None) -> dict:
	"""A tab's list, a page at a time, as its kind's own list context gives it
	to the reader, searched by `txt` and narrowed to one `state`: its column
	heads, its rows, how many are in each state, whether there are more, and
	its Add button where it has one."""
	from frappe.www.list import get_list_data_for_context

	doctype = _kind(kind)
	start = frappe.utils.cint(start)
	found = get_list_data_for_context(None, doctype, txt=txt or None, limit=COUNTED)
	# erpnext lists a timesheet once per time entry: each record once.
	found = [one for one in {_field(one, "name"): one for one in found}.values() if mine(doctype, one)]
	drawn = [row for row in (_row(kind, doctype, one) for one in found) if row]
	states = {}
	for row in drawn:
		if row["status"]:
			states.setdefault(row["status"], {"label": row["status"], "tone": row["tone"], "count": 0})[
				"count"
			] += 1
	if state:
		drawn = [row for row in drawn if row["status"] == state]
	add = ADD.get(doctype)
	return {
		"doctype": doctype,
		"columns": [str(one) for one in COLUMNS.get(doctype) or COLUMNS[None]],
		"rows": drawn[start : start + PAGE],
		"states": list(states.values()) if len(states) > 1 else [],
		"total": len(found),
		"more": len(drawn) > start + PAGE,
		"add": {"to": add[0], "label": str(add[1])} if add else None,
	}


#: What on Home asks something of the reader, by kind: whether a record does,
#: and the button it offers.
ASKS = {
	"Sales Invoice": (lambda doc: (doc.get("outstanding_amount") or 0) > 0, _lt("View and Pay")),
	"Purchase Invoice": (lambda doc: False, None),
	"Quotation": (lambda doc: _answerable(doc), _lt("Review")),
	"Request for Quotation": (lambda doc: not _quoted(doc.name), _lt("Answer")),
	"Purchase Order": (lambda doc: doc.status in ("To Receive and Bill", "To Receive"), _lt("View")),
}

#: How many records Home lists under Needs You and Recent.
SHOWN = 5


@frappe.whitelist()
def home() -> dict:
	"""Home: a tile a tab with anything in it (how many, and what is left to
	pay on bills), the records that ask something of the reader (a bill to
	pay, a quotation to review, a request to answer), and the latest records,
	each read the way the tab's own list reads them."""
	from frappe.utils import flt, fmt_money
	from frappe.www.list import get_list_data_for_context

	tiles, asks, recent = [], [], []
	for path, item in _kinds().items():
		doctype = item["reference_doctype"]
		try:
			found = get_list_data_for_context(None, doctype, limit=COUNTED + 1)
		except frappe.PermissionError:
			continue
		found = [one for one in {_field(one, "name"): one for one in found}.values() if mine(doctype, one)]
		if not found:
			continue
		states, say = WAITING.get(doctype, ((), None))
		waiting = sum(1 for one in found if _field(one, "status") in states)
		tile = {
			"path": path,
			"title": _(item.get("title")),
			"icon": ICONS.get(path, "file-text"),
			"count": f"{COUNTED}+" if len(found) > COUNTED else str(len(found)),
			"waiting": say(waiting) if waiting else "",
		}
		if doctype in OWED:
			owed = {}
			for one in found:
				if one.docstatus == 1 and flt(one.outstanding_amount) > 0:
					owed[one.currency] = owed.get(one.currency, 0) + flt(one.outstanding_amount)
			tile["figure"] = " + ".join(
				fmt_money(value, currency=currency) for currency, value in owed.items()
			)
			tile["figure_label"] = _("to pay") if owed else ""
		tiles.append(tile)
		if doctype not in TRANSACTIONS:
			continue
		ask, button = ASKS.get(doctype, (lambda doc: False, None))
		for one in found:
			row = None
			if one.docstatus == 1 and ask(one):
				row = _row(path, doctype, one)
				asks.append({**row, "kind": _called(doctype), "icon": tile["icon"], "button": str(button)})
			recent.append((one.modified, path, doctype, one, tile["icon"], row))
	recent.sort(key=lambda one: one[0], reverse=True)
	latest = []
	for _when, path, doctype, one, icon, row in recent[:SHOWN]:
		row = row or _row(path, doctype, one)
		latest.append({**row, "kind": _called(doctype), "icon": icon})
	# What is late first.
	asks.sort(key=lambda row: not row.get("when", {}).get("late"))
	return {"tiles": tiles, "asks": asks[:SHOWN], "more_asks": max(len(asks) - SHOWN, 0), "recent": latest}


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

	doctype = _kind(kind)
	if doctype not in TRANSACTIONS or doctype == "Request for Quotation":
		raise frappe.PermissionError
	return _record(doctype, _opened(doctype, name, order))


def _record(doctype: str, context, pdf: str | None = None) -> dict:
	"""A record's page from erpnext's page context (or one made for a signed
	link, one/portal_share.py, which has its own PDF and no linked records:
	the reader of a link has no portal to open them in)."""
	from erpnext.templates.pages import order
	from frappe.utils import fmt_money, sanitize_html, strip_html

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
		lines = re.sub(r"\s*<br\s*/?>\s*", "\n", address)
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
	accepted = _accepted(doc.name) if doctype == "Quotation" and doc.status == "Open" else None
	if accepted:
		tone, word = "blue", _("Accepted")
	quoted = doctype == "Supplier Quotation"
	actions = []
	if doc.docstatus == 1:
		actions.append(
			{
				"label": _("Download PDF"),
				"icon": "download",
				"href": pdf
				or "/api/method/frappe.utils.print_format.download_pdf?"
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
		"summary": _summary(doctype, doc, total)
		| ({"line": _("Accepted. We'll confirm your order.")} if accepted else {}),
		"answer": doctype == "Quotation" and _answerable(doc),
		"steps": _steps(doctype, doc),
		"related": [] if pdf else _related(doctype, doc),
		"facts": facts,
		"items": [
			{
				"item": row.item_name or row.item_code,
				"image": row.get("image") or "",
				"about": _about(row),
				"qty": number(row.qty),
				"uom": _(row.get("uom") or row.get("stock_uom") or ""),
				"rate": row.get_formatted("rate", doc),
				# A discount shows as the list rate less it, as on the print.
				"list_rate": row.get_formatted("price_list_rate", doc)
				if row.get("discount_percentage")
				else "",
				"discount": f"{number(row.discount_percentage)}%" if row.get("discount_percentage") else "",
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


#: What follows from what, by kind: the item row's field naming the record
#: before, and the kinds after it with the field on their item rows that names
#: this one.
CHAIN = {
	"Quotation": ((), (("Sales Order", "Sales Order Item", "prevdoc_docname"),)),
	"Sales Order": (
		(("Quotation", "prevdoc_docname"),),
		(
			("Delivery Note", "Delivery Note Item", "against_sales_order"),
			("Sales Invoice", "Sales Invoice Item", "sales_order"),
		),
	),
	"Delivery Note": (
		(("Sales Order", "against_sales_order"),),
		(("Sales Invoice", "Sales Invoice Item", "delivery_note"),),
	),
	"Sales Invoice": ((("Sales Order", "sales_order"), ("Delivery Note", "delivery_note")), ()),
	"Supplier Quotation": ((), (("Purchase Order", "Purchase Order Item", "supplier_quotation"),)),
	"Purchase Order": (
		(("Supplier Quotation", "supplier_quotation"),),
		(("Purchase Invoice", "Purchase Invoice Item", "purchase_order"),),
	),
	"Purchase Invoice": ((("Purchase Order", "purchase_order"),), ()),
}

#: The party a kind belongs to, so a linked record is shown only when it is
#: the same customer's or supplier's.
PARTY = {
	"Quotation": "party_name",
	"Sales Order": "customer",
	"Delivery Note": "customer",
	"Sales Invoice": "customer",
	"Supplier Quotation": "supplier",
	"Purchase Order": "supplier",
	"Purchase Invoice": "supplier",
}


def _called(doctype: str) -> str:
	return str(CALLED.get(doctype) or _(doctype))


def _total_field(doc) -> str:
	return (
		"rounded_total"
		if doc.get("rounded_total") and not doc.get("disable_rounded_total")
		else "grand_total"
	)


def _summary(doctype: str, doc, total: str) -> dict:
	"""The figure a record's page leads with: what is left to pay on a bill,
	and when; otherwise its total, and the date that matters next."""
	from frappe.utils import date_diff, getdate, today

	if doctype in OWED and doc.docstatus == 1:
		left = doc.get("outstanding_amount") or 0
		if left <= 0:
			return {"label": _("Paid"), "value": doc.get_formatted(total), "line": _("Paid in full")}
		said = {"label": _("Amount due"), "value": doc.get_formatted("outstanding_amount")}
		# The first instalment still owed, as erpnext's Overdue reads it, else
		# the bill's own due date.
		owed = [row.due_date for row in doc.get("payment_schedule") or [] if (row.outstanding or 0) > 0]
		due = min(owed) if owed else doc.get("due_date")
		if due:
			late = date_diff(today(), due)
			if late > 0:
				said |= {
					"line": _("{0} days overdue").format(late) if late != 1 else _("1 day overdue"),
					"late": True,
				}
			else:
				said["line"] = _("Due {0}").format(_date(due))
		return said
	line = ""
	if doctype in ("Quotation", "Supplier Quotation") and doc.status in (
		"Ordered",
		"Partially Ordered",
		"Lost",
	):
		line = status(doctype, doc.status)[1]
	elif doctype in ("Quotation", "Supplier Quotation") and doc.get("valid_till"):
		line = _("Valid until {0}").format(_date(doc.valid_till))
	elif doc.get("delivery_date") or doc.get("schedule_date"):
		line = _("Delivery {0}").format(_date(doc.get("delivery_date") or doc.get("schedule_date")))
	elif doc.get("posting_date") and getdate(doc.posting_date):
		line = _date(doc.posting_date)
	return {"label": _("Total"), "value": doc.get_formatted(total), "line": line}


def _steps(doctype: str, doc) -> list[dict]:
	"""Where a record is on its way, as a row of steps, each done or not: an
	order is confirmed, delivered, invoiced and paid."""
	from frappe.utils import flt

	paid = (doc.get("outstanding_amount") or 0) <= 0
	if doctype == "Quotation":
		if doc.status == "Lost":
			steps = [(_("Sent"), True), (_("Declined"), True)]
		else:
			ordered = doc.status == "Ordered"
			steps = [
				(_("Sent"), True),
				(_("Accepted"), ordered or bool(_accepted(doc.name))),
				(_("Ordered"), ordered),
			]
	elif doctype == "Supplier Quotation":
		ordered = _("Partly ordered") if doc.status == "Partially Ordered" else _("Ordered")
		steps = [(_("Sent"), True), (ordered, doc.status == "Ordered")]
	elif doctype == "Sales Order":
		billed = flt(doc.per_billed) >= 100
		steps = [
			(_("Confirmed"), True),
			(_("Delivered"), flt(doc.per_delivered) >= 100),
			(_("Invoiced"), billed),
			(_("Paid"), billed and not _owed("Sales Invoice", "sales_order", doc.name)),
		]
	elif doctype == "Delivery Note":
		steps = [(_("Shipped"), True), (_("Invoiced"), flt(doc.get("per_billed")) >= 100)]
	elif doctype == "Purchase Order":
		billed = flt(doc.per_billed) >= 100
		steps = [
			(_("Ordered"), True),
			(_("Delivered"), flt(doc.per_received) >= 100),
			(_("Invoiced"), billed),
			(_("Paid"), billed and not _owed("Purchase Invoice", "purchase_order", doc.name)),
		]
	elif doctype == "Sales Invoice":
		steps = [(_("Issued"), True), (_("Paid"), paid)]
	elif doctype == "Purchase Invoice":
		steps = [(_("Received"), True), (_("Paid"), paid)]
	else:
		return []
	if doc.docstatus != 1:
		return []
	current = next((i for i, (_label, done) in enumerate(steps) if not done), None)
	return [{"label": label, "done": done, "current": i == current} for i, (label, done) in enumerate(steps)]


def _owed(doctype: str, field: str, name: str) -> bool:
	"""Whether any bill made from a record still has something to pay."""
	bills = frappe.get_all(
		f"{doctype} Item", filters={field: name, "docstatus": 1}, pluck="parent", distinct=True
	)
	return bool(bills) and bool(
		frappe.db.exists(doctype, {"name": ("in", bills), "outstanding_amount": (">", 0), "docstatus": 1})
	)


def _accepted(quotation: str) -> str | None:
	"""The order a quotation was accepted as on the portal, or made into."""
	return frappe.db.get_value(
		"Sales Order Item", {"prevdoc_docname": quotation, "docstatus": ("<", 2)}, "parent"
	)


def _answerable(doc) -> bool:
	"""Whether the customer may still accept or decline a quotation: sent,
	open, not run out (unless the workspace takes orders on those, as
	erpnext's Selling Settings says), and not accepted already."""
	from frappe.utils import getdate, today

	if doc.docstatus != 1 or doc.status not in ("Open", "Replied"):
		return False
	if doc.valid_till and getdate(doc.valid_till) < getdate(today()):
		if not frappe.db.get_single_value(
			"Selling Settings", "allow_sales_order_creation_for_expired_quotation"
		):
			return False
	return not _accepted(doc.name)


def _answer(kind: str, name: str):
	"""A quotation the reader may answer, through erpnext's own page context,
	which checks it is theirs."""
	from erpnext.templates.pages import order

	if _kind(kind) != "Quotation":
		raise frappe.PermissionError
	doc = _opened("Quotation", name, order).doc
	if not _answerable(doc):
		frappe.throw(_("This quotation can't be answered any more."))
	return doc


@frappe.whitelist(methods=["POST"])
def accept_quote(kind: str, name: str, wanted: str, reference: str | None = None) -> str:
	"""The customer accepts a quotation on the portal (`accept`)."""
	from frappe.utils import get_fullname

	doc = _answer(kind, name)
	user = frappe.session.user
	return accept(
		doc, wanted, reference, user, _contact_of(user, "Customer", doc.party_name), get_fullname(user)
	)


def accept(doc, wanted: str, reference: str | None, user: str, contact: str | None, by: str) -> str:
	"""A quotation accepted: erpnext's own mapper makes the order from it, as
	the team would on the desk, with the date they need it by and their
	reference, named for whoever accepted (`contact`). It is kept a draft for
	whoever made the quotation to check and submit, and they are told."""
	from erpnext.selling.doctype.quotation.mapper import make_sales_order
	from frappe.utils import getdate, today

	from onedesk.one_crm import tell

	if not wanted or getdate(wanted) < getdate(today()):
		frappe.throw(_("Choose the date you need it by, today or later."))
	frappe.session.user = "Administrator"
	try:
		order = make_sales_order(doc.name)
		order.contact_person = contact or order.contact_person
		order.delivery_date = wanted
		for row in order.items:
			row.delivery_date = wanted
		if reference and reference.strip():
			order.po_no, order.po_date = reference.strip()[:140], today()
		order.flags.ignore_permissions = True
		order.insert()
		doc.add_comment("Info", _("Accepted on the portal by {0}: order {1}.").format(by, order.name))
	finally:
		frappe.session.user = user
	tell.quotation_accepted(doc, order, user if user != "Guest" else "Administrator", _date(wanted))
	return order.name


@frappe.whitelist(methods=["POST"])
def decline_quote(kind: str, name: str, reason: str | None = None) -> None:
	"""The customer declines a quotation on the portal (`decline`)."""
	from frappe.utils import get_fullname

	user = frappe.session.user
	decline(_answer(kind, name), reason, user, get_fullname(user))


def decline(doc, reason: str | None, user: str, by: str) -> None:
	"""A quotation declined: erpnext's own Set as Lost, with their reason,
	and whoever made it is told."""
	from onedesk.one_crm import tell

	reason = (reason or "").strip()[:1000]
	frappe.session.user = "Administrator"
	try:
		doc.declare_enquiry_lost([], [], detailed_reason=reason or _("Declined on the portal."))
		doc.add_comment("Info", _("Declined on the portal by {0}.").format(by))
	finally:
		frappe.session.user = user
	tell.quotation_declined(doc, user if user != "Guest" else "Administrator", reason)


def _related(doctype: str, doc) -> list[dict]:
	"""The records before and after this one that the reader has a tab for and
	that are the same customer's or supplier's: the quotation an order came
	from, its shipments and its invoices."""
	before, after = CHAIN.get(doctype, ((), ()))
	found = []
	for kind, field in before:
		found += [(kind, name) for name in dict.fromkeys(row.get(field) for row in doc.items) if name]
	for kind, child, field in after:
		names = frappe.get_all(
			child, filters={field: doc.name, "docstatus": 1}, pluck="parent", distinct=True
		)
		found += [(kind, name) for name in names]
	paths = {item["reference_doctype"]: path for path, item in _kinds().items()}
	party = doc.get(PARTY.get(doctype))
	out = []
	for kind, name in dict.fromkeys(found):
		path = paths.get(kind)
		if not path or not frappe.db.exists(kind, {"name": name, "docstatus": 1, PARTY[kind]: party}):
			continue
		other = frappe.get_doc(kind, name)
		if not mine(kind, other):
			continue
		if hasattr(other, "set_indicator"):
			other.set_indicator()
		tone, word = status(kind, other.status, other.docstatus, other.get("indicator_color"))
		out.append(
			{
				"kind": _called(kind),
				"name": name,
				"tone": tone,
				"status": word,
				"figure": other.get_formatted(_total_field(other)),
				"to": f"{path}/{name}",
				"icon": ICONS.get(path, "file-text"),
			}
		)
	return out


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

	if _kind("rfq") != "Request for Quotation":
		raise frappe.PermissionError
	context = _opened("Request for Quotation", name, page)
	if not mine("Request for Quotation", context.doc):
		raise frappe.PermissionError
	return _rfq(context.doc, [one.name for one in context.doc.get("rfq_links") or []])


def _sent(rfq: str, supplier: str) -> list[str]:
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


def _rfq(doc, sent: list[str]) -> dict:
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
		tone, word = status("Supplier Quotation", quote.status, quote.docstatus)
		quotes.append(
			{
				"name": one,
				"date": _date(quote.transaction_date),
				"status": word,
				"tone": tone,
				"total": fmt_money(quote.rounded_total or quote.grand_total, currency=quote.currency),
			}
		)
	facts = [{"label": _("Date"), "value": _date(doc.transaction_date)}]
	if doc.get("schedule_date"):
		facts.append({"label": _("Needed by"), "value": _date(doc.schedule_date)})
	if doc.get("shipping_address_display"):
		lines = re.sub(r"\s*<br\s*/?>\s*", "\n", doc.shipping_address_display)
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


def _quote(rfq: str, rows: str | dict, notes: str | None = None, sending: bool = True, link=None):
	"""The supplier's quote for a request, built the way erpnext's own mapper
	builds it but not saved: the reader is checked to be one of the supplier's
	portal users and the request one sent to that supplier, and only each
	row's rate, quantity and discount come from the page. The taxes are the
	workspace's own (its templates, its Item Tax Templates and Tax Rules by
	the supplier's country), as on any quote it records. Through a signed
	link (one/portal_share.py) the supplier and contact are the link's.
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
		# erpnext's page reads which request it is on from the form.
		frappe.form_dict.doctype, frappe.form_dict.name = "Request for Quotation", rfq
		supplier = get_supplier()
		if (
			not supplier
			or not check_supplier_has_docname_access(supplier)
			or not frappe.db.exists("Portal User", {"parent": supplier, "user": user})
		):
			frappe.throw(_("Not Permitted"), frappe.PermissionError)
		if not mine("Request for Quotation", frappe._dict(name=rfq)):
			frappe.throw(_("Not Permitted"), frappe.PermissionError)
		contact = _contact_of(user, "Supplier", supplier)
	if frappe.db.get_value("Request for Quotation", rfq, "docstatus") != 1:
		frappe.throw(_("This request is closed."))
	# erpnext's own check that the supplier was asked, and its row lookup,
	# which takes the item from the request and only the rate and quantity
	# from the supplier.
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
			"currency": supplier_doc.default_currency
			or frappe.get_cached_value("Company", doc.company, "default_currency"),
			"buying_price_list": supplier_doc.default_price_list
			or frappe.db.get_single_value("Buying Settings", "buying_price_list"),
			# The supplier's own prices: the workspace's pricing rules are
			# for what it sells and buys at its own prices, not for a quote.
			"ignore_pricing_rule": 1,
			# Whoever sent it is its contact.
			"contact_person": contact,
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
	finally:
		frappe.session.user = user
	# A discount is erpnext's own: the supplier's rate is the row's list
	# price and the discount comes off it, after the price list had its say.
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
	quote, _doc, _supplier, user = _quote(rfq, rows, sending=False)
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
			"rate": " + ".join(f"{number(one)}%" for one in rates),
		}
	return {
		"rows": out,
		"taxes": [
			{
				# erpnext writes "VAT 5% @ 5.0" where the account names its rate.
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
	"""The supplier's answer to a quote request (`_quote`), saved as theirs,
	and whoever asked told."""
	return send(*_quote(rfq, rows, notes))


def send(quote, doc, supplier: str, user: str) -> str:
	"""A quote saved as the supplier's, and whoever asked told."""
	frappe.session.user = "Administrator"
	try:
		quote.insert()
	finally:
		frappe.session.user = user
	# Saved with the user switched, the quote is the supplier's all the same;
	# sent through a link, by nobody signed in, it is the workspace's.
	user = user if user != "Guest" else "Administrator"
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
