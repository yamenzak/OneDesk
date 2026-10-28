"""The portal's engine: the frappe-ui app (frontend/portal) served at /portal
by www/portal.py, its tabs, lists, records and account pages, read through
frappe's and erpnext's own contexts and answered as JSON. How each kind of
record is drawn is its module's, in its own portal.py (KINDS, the one_portal
hook; one_portal/AGENTS.md lists the keys)."""

import importlib

import re
from urllib.parse import urlencode

import frappe
from frappe import _, _lt
from frappe.model.document import Document
from frappe.website.utils import get_portal_sidebar_items

OFF = ("/issues", "/material-requests")

TITLES = {"/rfq": "Quote Requests", "/supplier-quotations": "Quotes"}

FORMS = {"addresses": {"button_label": "Save Address"}}

SAID = (_lt("Quote Requests"), _lt("Quotes"), _lt("Save Address"))

PATHS = {"/project": "projects"}

ACCOUNT = (
	("profile", _lt("Profile"), "user"),
	("password", _lt("Password"), "key-round"),
	("your-data", _lt("Your Data"), "shield-check"),
	("apps", _lt("Third Party Apps"), "plug"),
)

COLUMNS = (_lt("Number"), _lt("Status"), _lt("Total"))

PAGE = 20

COUNTED = 100

TONES = {"green": "green", "blue": "blue", "orange": "amber", "yellow": "amber", "red": "red"}

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

_KINDS: dict[str, dict] = {}


def kinds() -> dict[str, dict]:
	"""Every kind of record the portal draws, by doctype, as the module it
	belongs to declares it in its own portal.py (KINDS, named by the
	one_portal hook). Read once a process."""
	if not _KINDS:
		for path in frappe.get_hooks("one_portal"):
			_KINDS.update(importlib.import_module(path).KINDS)
	return _KINDS


def kind_of(doctype: str) -> dict:
	"""What a kind of record's module declares of it, or nothing."""
	return kinds().get(doctype) or {}


def narrowed() -> tuple[str, ...]:
	"""The kinds a record of which can be hidden from some of its party's
	contacts: a customer's or supplier's own documents (`transaction`)."""
	return tuple(doctype for doctype, one in kinds().items() if one.get("transaction"))


def _icon(doctype: str | None) -> str:
	return kind_of(doctype).get("icon") or "file-text"


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
	if doctype not in narrowed():
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
			{"path": path, "title": _(item.get("title")), "icon": _icon(item["reference_doctype"])}
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
	if said := kind_of(doctype).get("said", {}).get(state):
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


def _field(row, field: str):
	return row.get(field) if isinstance(row, dict) else getattr(row, field, None)


def _row(path: str, doctype: str, doc) -> dict | None:
	"""One row of a list, as the app draws it: its name, a line under it, its
	Badge, the figure at its end and where it opens. A kind with a row of
	its own draws it (`row`); a customer's or supplier's document is drawn
	here, with its module's word for its state (`badge`) and figure."""
	declared = kind_of(doctype)
	if declared.get("row"):
		return declared["row"](doc)
	if declared.get("transaction"):
		when = doc.get("transaction_date") or doc.get("posting_date") or doc.modified
		names = list(dict.fromkeys(row.item_name or row.item_code for row in doc.get("items") or []))
		badge = declared["badge"](doc) if declared.get("badge") else None
		tone, word = badge or status(doctype, doc.status, doc.docstatus, doc.get("indicator_color"))
		if declared.get("figure"):
			figure = declared["figure"](doc)
		else:
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
	bill's due date (`owed`), otherwise the date its module names (`ahead`):
	a quotation's last day, an order's delivery. Nothing once it is done,
	ended (`ended`, and erpnext's Expired and Cancelled) or settled."""
	from frappe.utils import date_diff, today

	declared = kind_of(doctype)
	if done or doc.docstatus != 1:
		return {}
	ended = declared.get("ended")
	if ended and doc.status in (*ended, "Expired", "Cancelled"):
		return {}
	if declared.get("settled") and declared["settled"](doc):
		return {}
	if declared.get("owed"):
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
	field, label = declared.get("ahead") or (None, None)
	if not field or not doc.get(field):
		return {}
	return {"text": str(label).format(_date(doc.get(field))), "late": date_diff(today(), doc.get(field)) > 0}


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
	add = kind_of(doctype).get("add")
	return {
		"doctype": doctype,
		"columns": [str(one) for one in kind_of(doctype).get("columns") or COLUMNS],
		"rows": drawn[start : start + PAGE],
		"states": list(states.values()) if len(states) > 1 else [],
		"total": len(found),
		"more": len(drawn) > start + PAGE,
		"add": {"to": add[0], "label": str(add[1])} if add else None,
	}


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
		declared = kind_of(doctype)
		states, say = declared.get("waiting") or ((), None)
		waiting = sum(1 for one in found if _field(one, "status") in states)
		tile = {
			"path": path,
			"title": _(item.get("title")),
			"icon": _icon(doctype),
			"count": f"{COUNTED}+" if len(found) > COUNTED else str(len(found)),
			"waiting": say(waiting) if waiting else "",
		}
		if declared.get("owed"):
			owed = {}
			for one in found:
				if one.docstatus == 1 and flt(one.outstanding_amount) > 0:
					owed[one.currency] = owed.get(one.currency, 0) + flt(one.outstanding_amount)
			tile["figure"] = " + ".join(
				fmt_money(value, currency=currency) for currency, value in owed.items()
			)
			tile["figure_label"] = _("to pay") if owed else ""
		tiles.append(tile)
		if not declared.get("transaction"):
			continue
		ask, button = declared.get("asks") or (lambda doc: False, None)
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
	if not kind_of(doctype).get("transaction") or kind_of(doctype).get("own_page"):
		raise frappe.PermissionError
	return _record(doctype, _opened(doctype, name, order))


def _record(doctype: str, context, pdf: str | None = None) -> dict:
	"""A record's page from erpnext's page context (or one made for a signed
	link, one_portal/share.py, which has its own PDF and no linked records:
	the reader of a link has no portal to open them in)."""
	from erpnext.templates.pages import order
	from frappe.utils import fmt_money, sanitize_html, strip_html

	doc = context.doc
	declared = kind_of(doctype)
	said, facts = set(), []
	for field, label in FACTS:
		value = doc.get(field)
		if not value or str(label) in said:
			continue
		said.add(str(label))
		facts.append({"label": str(label), "value": doc.get_formatted(field)})
	address = doc.get("shipping_address") or doc.get("address_display")
	if address and declared.get("ships"):
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
			label = re.sub(r"\s*@\s*[\d.]+\s*$", "", tax.description or "") or _("Tax")
			totals.append({"label": label, "value": tax.get_formatted("tax_amount")})
	total = (
		"rounded_total"
		if doc.get("rounded_total") and not doc.get("disable_rounded_total")
		else "grand_total"
	)
	totals.append({"label": _("Total"), "value": doc.get_formatted(total), "strong": True})
	if declared.get("owed") and doc.docstatus == 1:
		left = doc.get("outstanding_amount") or 0
		paid = (doc.get(total) or 0) - left
		if paid and left:
			totals.append({"label": _("Paid"), "value": fmt_money(paid, currency=doc.currency)})
			totals.append(
				{"label": _("To pay"), "value": doc.get_formatted("outstanding_amount"), "strong": True}
			)

	tone, word = status(
		doctype, doc.get("status") or doc.get("indicator_title"), doc.docstatus, doc.get("indicator_color")
	)
	badge = declared["badge"](doc) if declared.get("badge") else None
	if badge:
		tone, word = badge
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
	if declared.get("actions"):
		actions += declared["actions"](doc, context)
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
		| (declared["summary"](doc) if declared.get("summary") else {}),
		"answer": bool(declared.get("answer") and declared["answer"](doc)),
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
				"list_rate": row.get_formatted("price_list_rate", doc)
				if row.get("discount_percentage")
				else "",
				"discount": f"{number(row.discount_percentage)}%" if row.get("discount_percentage") else "",
				"amount": row.get_formatted("amount", doc),
			}
			for row in doc.items
		],
		"totals": totals,
		"terms_label": str(declared.get("terms_label") or _("Terms")),
		"terms": sanitize_html(doc.terms) if doc.get("terms") else "",
		"files": [
			{"name": one.file_name, "url": one.file_url} for one in order.get_attachments(doctype, doc.name)
		],
		"actions": actions,
	}


def _called(doctype: str) -> str:
	return str(kind_of(doctype).get("called") or _(doctype))


def _total_field(doc) -> str:
	return (
		"rounded_total"
		if doc.get("rounded_total") and not doc.get("disable_rounded_total")
		else "grand_total"
	)


def _summary(doctype: str, doc, total: str) -> dict:
	"""The figure a record's page leads with: what is left to pay on a bill,
	and when; otherwise its total, and the date that matters next: its state
	once it has ended, else the date its module names (`ahead`)."""
	from frappe.utils import date_diff, getdate, today

	declared = kind_of(doctype)
	if declared.get("owed") and doc.docstatus == 1:
		left = doc.get("outstanding_amount") or 0
		if left <= 0:
			return {"label": _("Paid"), "value": doc.get_formatted(total), "line": _("Paid in full")}
		said = {"label": _("Amount due"), "value": doc.get_formatted("outstanding_amount")}
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
	field, label = declared.get("ahead") or (None, None)
	line = ""
	if doc.status in declared.get("ended", ()):
		line = status(doctype, doc.status)[1]
	elif field and doc.get(field):
		line = str(label).format(_date(doc.get(field)))
	elif doc.get("delivery_date") or doc.get("schedule_date"):
		line = _("Delivery {0}").format(_date(doc.get("delivery_date") or doc.get("schedule_date")))
	elif doc.get("posting_date") and getdate(doc.posting_date):
		line = _date(doc.posting_date)
	return {"label": _("Total"), "value": doc.get_formatted(total), "line": line}


def _steps(doctype: str, doc) -> list[dict]:
	"""Where a record is on its way, as a row of steps its module names, each
	done or not: an order is confirmed, delivered, invoiced and paid."""
	declared = kind_of(doctype)
	if not declared.get("steps") or doc.docstatus != 1:
		return []
	steps = declared["steps"](doc)
	current = next((i for i, (_label, done) in enumerate(steps) if not done), None)
	return [{"label": label, "done": done, "current": i == current} for i, (label, done) in enumerate(steps)]


def owed(doctype: str, field: str, name: str) -> bool:
	"""Whether any bill made from a record still has something to pay."""
	bills = frappe.get_all(
		f"{doctype} Item", filters={field: name, "docstatus": 1}, pluck="parent", distinct=True
	)
	return bool(bills) and bool(
		frappe.db.exists(doctype, {"name": ("in", bills), "outstanding_amount": (">", 0), "docstatus": 1})
	)


def _related(doctype: str, doc) -> list[dict]:
	"""The records before and after this one, as its module chains them
	(`chain`), that the reader has a tab for and that are the same
	customer's or supplier's: the quotation an order came from, its shipments
	and its invoices."""
	before, after = kind_of(doctype).get("chain") or ((), ())
	found = []
	for other, field in before:
		found += [(other, name) for name in dict.fromkeys(row.get(field) for row in doc.items) if name]
	for other, child, field in after:
		names = frappe.get_all(
			child, filters={field: doc.name, "docstatus": 1}, pluck="parent", distinct=True
		)
		found += [(other, name) for name in names]
	paths = {item["reference_doctype"]: path for path, item in _kinds().items()}
	party = doc.get(kind_of(doctype).get("party"))
	out = []
	for other, name in dict.fromkeys(found):
		path = paths.get(other)
		field = kind_of(other).get("party")
		if not path or not field or not frappe.db.exists(other, {"name": name, "docstatus": 1, field: party}):
			continue
		record = frappe.get_doc(other, name)
		if not mine(other, record):
			continue
		if hasattr(record, "set_indicator"):
			record.set_indicator()
		tone, word = status(other, record.status, record.docstatus, record.get("indicator_color"))
		out.append(
			{
				"kind": _called(other),
				"name": name,
				"tone": tone,
				"status": word,
				"figure": record.get_formatted(_total_field(record)),
				"to": f"{path}/{name}",
				"icon": _icon(other),
			}
		)
	return out


def _about(row) -> str:
	from frappe.utils import strip_html

	about = strip_html(row.get("description") or "").strip()
	return about if about and about != (row.item_name or row.item_code) else ""


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


LIGHT_OR_DARK = (
	"<script>(()=>{const m=matchMedia('(prefers-color-scheme: dark)'),"
	"set=()=>document.documentElement.setAttribute('data-theme',m.matches?'dark':'light');"
	"set();m.addEventListener('change',set)})()</script>"
)


def light_or_dark(context):
	"""Every web page in the reader's light or dark, as the desk is."""
	context["head_include"] = (context.get("head_include") or "") + LIGHT_OR_DARK
