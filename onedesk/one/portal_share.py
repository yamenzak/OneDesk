"""Who sees a record on the portal, and signed links to it: the desk's
Portal dialog (public/js/portal_share.js) and the link's page
(frontend/portal, /portal/l/<token>), which answers once, then reads. See
One's Help, The Portal (one/docs/the-portal.md)."""

import json
from urllib.parse import quote

import frappe
from frappe import _, _lt
from frappe.utils import add_days, get_datetime, get_url, getdate, now_datetime, pretty_date

from onedesk.one import portal
from onedesk.one.doctype.portal_link.portal_link import hashed

DAYS = 30

ANSWERS = {
	"Quotation": _lt("Review the quotation"),
	"Request for Quotation": _lt("Answer the quote request"),
}

GONE = _lt("This link no longer works. Ask whoever sent it for a new one.")


def _record(doctype: str, name: str, ptype: str = "read"):
	if doctype not in portal.NARROWED:
		raise frappe.PermissionError
	doc = frappe.get_doc(doctype, name)
	doc.check_permission(ptype)
	return doc


def _parties(doc) -> list[tuple[str, str, str]]:
	"""The customers or suppliers a record is for: (type, name, as said)."""
	if doc.doctype == "Request for Quotation":
		return [("Supplier", row.supplier, row.supplier_name or row.supplier) for row in doc.suppliers]
	if doc.doctype == "Quotation":
		if doc.quotation_to != "Customer":
			return []
		return [("Customer", doc.party_name, doc.customer_name or doc.party_name)]
	field = portal.PARTY[doc.doctype]
	party_type = "Supplier" if field == "supplier" else "Customer"
	return [(party_type, doc.get(field), doc.get(f"{field}_name") or doc.get(field))]


def _contacts(party_type: str, party: str) -> list:
	names = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "link_doctype": party_type, "link_name": party},
		pluck="parent",
	)
	if not names:
		return []
	return frappe.get_all(
		"Contact",
		filters={"name": ("in", names)},
		fields=["name", "full_name", "email_id", "user"],
		order_by="full_name",
	)


def _state(link) -> str:
	if link.disabled:
		return "revoked"
	if link.expires_on and get_datetime(link.expires_on) < now_datetime():
		return "expired"
	if link.used_on:
		return "answered"
	return "open"


def _links(doc) -> list[dict]:
	out = []
	for name in frappe.get_all(
		"Portal Link",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
		pluck="name",
		order_by="creation desc",
	):
		link = frappe.get_doc("Portal Link", name)
		state = _state(link)
		out.append(
			{
				"name": link.name,
				"who": frappe.db.get_value("Contact", link.contact, "full_name")
				if link.contact
				else link.email,
				"email": link.email,
				"party": link.party,
				"state": state,
				"made": pretty_date(link.creation),
				"opened": link.opened or 0,
				"last_opened": pretty_date(link.last_opened) if link.last_opened else "",
				"expires": portal._date(link.expires_on),
				"used_by": link.used_by or "",
				"used_on": pretty_date(link.used_on) if link.used_on else "",
				"url": _url(link.get_password("token")) if state in ("open", "answered") else "",
			}
		)
	return out


def _url(token: str) -> str:
	return get_url(f"/portal/l/{token}")


@frappe.whitelist()
def access(doctype: str, name: str) -> dict:
	"""The record's Portal dialog: each of its customer's or supplier's
	contacts with a portal login and whether they see it, the contacts a link
	may go to, and its links."""
	doc = _record(doctype, name)
	hidden = portal._hidden(doctype, doc)
	groups = []
	for party_type, party, said in _parties(doc):
		people, reachable = [], []
		for one in _contacts(party_type, party):
			if one.email_id:
				reachable.append(
					{"contact": one.name, "name": one.full_name or one.email_id, "email": one.email_id}
				)
			if not one.user or frappe.db.get_value("User", one.user, "user_type") != "Website User":
				continue
			people.append(
				{
					"contact": one.name,
					"name": one.full_name or one.email_id,
					"email": one.email_id,
					"user": one.user,
					"sees": one.name not in hidden,
				}
			)
		groups.append(
			{"party_type": party_type, "party": party, "said": said, "people": people, "reachable": reachable}
		)
	return {
		"groups": groups,
		"may": bool(frappe.has_permission(doctype, "write", doc)),
		"answers": str(ANSWERS[doctype]) if doctype in ANSWERS else "",
		"until": portal._date(_until(doc)),
		"links": _links(doc),
	}


@frappe.whitelist(methods=["POST"])
def set_access(doctype: str, name: str, hidden: str | list) -> dict:
	"""Hide a record from some of its party's portal contacts, or show it to
	them again. Only who it is hidden from is kept: everybody else, and a
	contact added later, sees it."""
	doc = _record(doctype, name, "write")
	hidden = set(frappe.parse_json(hidden) or [])
	theirs = {one.name for party_type, party, _said in _parties(doc) for one in _contacts(party_type, party)}
	if hidden - theirs:
		frappe.throw(_("Only the record's own contacts can be hidden from."))
	before = portal._hidden(doctype, doc)
	doc.db_set("one_portal_hidden", json.dumps(sorted(hidden)) if hidden else None, update_modified=False)
	if hidden != before:

		def names(contacts) -> str:
			return ", ".join(
				frappe.db.get_value("Contact", one, "full_name") or one for one in sorted(contacts)
			)

		said = []
		if hidden - before:
			said.append(_("hidden on the portal from {0}").format(names(hidden - before)))
		if before - hidden:
			said.append(_("shown on the portal to {0} again").format(names(before - hidden)))
		doc.add_comment("Info", "; ".join(said))
	return access(doctype, name)


@frappe.whitelist(methods=["POST"])
def make_link(
	doctype: str,
	name: str,
	contact: str | None = None,
	email: str | None = None,
	party: str | None = None,
	expires_on: str | None = None,
	send: int = 0,
) -> dict:
	"""A signed link to the record for one person: a contact of its customer
	or supplier, or an address. It opens until it expires (a quotation's own
	last day, or a month), and answers once; one open link per person.
	Mailed to them when `send`."""
	doc = _record(doctype, name, "write")
	parties = _parties(doc)
	if not parties:
		frappe.throw(_("This record has no customer or supplier to send it to."))
	if contact:
		linked = {
			(one.link_doctype, one.link_name)
			for one in frappe.get_all(
				"Dynamic Link",
				filters={"parenttype": "Contact", "parent": contact},
				fields=["link_doctype", "link_name"],
			)
		}
		found = [(party_type, one) for party_type, one, _said in parties if (party_type, one) in linked]
		if not found:
			frappe.throw(_("{0} isn't a contact of this record's customer or supplier.").format(contact))
		party_type, party = found[0]
		email = email or frappe.db.get_value("Contact", contact, "email_id")
	else:
		match = [(party_type, one) for party_type, one, _said in parties if not party or one == party]
		if len(match) != 1:
			frappe.throw(_("Choose who at which supplier the link is for."))
		party_type, party = match[0]
	email = (email or "").strip().lower()
	if not frappe.utils.validate_email_address(email):
		frappe.throw(_("A link needs an email address to go to."))
	for name in frappe.get_all(
		"Portal Link",
		filters={"reference_doctype": doctype, "reference_name": doc.name, "email": email, "disabled": 0},
		pluck="name",
	):
		link = frappe.get_doc("Portal Link", name)
		if _state(link) == "open" and not expires_on:
			url = _url(link.get_password("token"))
			if frappe.utils.cint(send):
				_mail(link, url, doc)
			return {"url": url, "links": _links(doc)}
	until = get_datetime(expires_on) if expires_on else _until(doc)
	if until < now_datetime():
		frappe.throw(_("Choose a day that hasn't passed."))
	link = frappe.get_doc(
		{
			"doctype": "Portal Link",
			"reference_doctype": doctype,
			"reference_name": doc.name,
			"party_type": party_type,
			"party": party,
			"contact": contact,
			"email": email,
			"expires_on": until,
		}
	).insert(ignore_permissions=True)
	url = _url(link.flags.token)
	if frappe.utils.cint(send):
		_mail(link, url, doc)
	doc.add_comment("Info", _("made a portal link for {0}").format(email))
	return {"url": url, "links": _links(doc)}


def _until(doc):
	"""A month from now, or a quotation's own last day if that is sooner."""
	until = get_datetime(add_days(now_datetime(), DAYS))
	if doc.doctype == "Quotation" and doc.get("valid_till"):
		last = get_datetime(f"{getdate(doc.valid_till)} 23:59:59")
		if now_datetime() < last < until:
			until = last
	return until


def _link(name: str):
	link = frappe.get_doc("Portal Link", name)
	_record(link.reference_doctype, link.reference_name, "write")
	return link


@frappe.whitelist(methods=["POST"])
def revoke_link(name: str) -> list[dict]:
	"""The link stops opening at once."""
	link = _link(name)
	link.db_set("disabled", 1)
	doc = frappe.get_doc(link.reference_doctype, link.reference_name)
	doc.add_comment("Info", _("revoked the portal link for {0}").format(link.email))
	return _links(doc)


@frappe.whitelist(methods=["POST"])
def rotate_link(name: str, send: int = 0) -> dict:
	"""A new link in place of one that may have gone further than meant: the
	old stops opening, the new is for the same person until the same day."""
	old = _link(name)
	old.db_set("disabled", 1)
	return make_link(
		old.reference_doctype,
		old.reference_name,
		contact=old.contact,
		email=old.email,
		party=old.party,
		expires_on=str(max(get_datetime(old.expires_on), add_days(now_datetime(), 1))),
		send=send,
	)


@frappe.whitelist(methods=["POST"])
def mail_link(name: str) -> None:
	"""Mail the link again to whoever it is for."""
	link = _link(name)
	if _state(link) != "open":
		frappe.throw(_("Only a link that still opens can be sent."))
	_mail(link, _url(link.get_password("token")), frappe.get_doc(link.reference_doctype, link.reference_name))


def _mail(link, url: str, doc) -> None:
	from onedesk.one import tell
	from onedesk.one.privacy_public import workspace

	tell.portal_link(
		link.email,
		by=frappe.utils.get_fullname(),
		what=_("{0} {1}").format(portal._called(doc.doctype), doc.name),
		workspace=workspace(),
		link=url,
		button=str(ANSWERS[doc.doctype]) if doc.doctype in ANSWERS else _("Open {0}").format(doc.name),
		until=portal._date(link.expires_on),
	)


def _live(token: str | None):
	"""The link a token names, if it still opens, else refused in one word
	whatever the reason, so a guess learns nothing."""
	name = None
	if token and len(token) <= 80:
		name = frappe.db.get_value("Portal Link", {"token_hash": hashed(token), "disabled": 0}, "name")
	link = frappe.get_doc("Portal Link", name) if name else None
	if (
		not link
		or (link.expires_on and get_datetime(link.expires_on) < now_datetime())
		or frappe.db.get_value(link.reference_doctype, link.reference_name, "docstatus") != 1
	):
		frappe.throw(str(GONE), frappe.PermissionError)
	return link


def _print_format(doctype: str) -> str:
	return frappe.get_meta(doctype).default_print_format or "Standard"


@frappe.whitelist(allow_guest=True, methods=["POST"])
def link_view(token: str) -> dict:
	"""The record a link opens, as the portal's own page draws it, with what
	the reader may still do: answer once, then read."""
	from onedesk.one.privacy_public import workspace

	link = _live(token)
	doc = frappe.get_doc(link.reference_doctype, link.reference_name)
	link.db_set({"opened": (link.opened or 0) + 1, "last_opened": now_datetime()}, update_modified=False)
	if doc.doctype == "Request for Quotation":
		page = portal._rfq(doc, portal._sent(doc.name, link.party))
		page["open"] = page["open"] and not link.used_on
		kind = "rfq"
	else:
		context = frappe._dict(
			doc=doc, print_format=_print_format(doc.doctype), show_pay_button=False, show_make_pi_button=False
		)
		page = portal._record(
			doc.doctype, context, pdf=f"/api/method/onedesk.one.portal_share.link_pdf?token={quote(token)}"
		)
		page["answer"] = bool(page.get("answer")) and not link.used_on
		kind = "record"
	return {
		"kind": kind,
		"page": page,
		"title": portal._called(doc.doctype),
		"party": frappe.db.get_value(link.party_type, link.party, f"{link.party_type.lower()}_name")
		or link.party,
		"workspace": workspace(),
		"answered": {"by": link.used_by, "on": pretty_date(link.used_on)} if link.used_on else None,
	}


def _answering(token: str, doctype: str, by: str | None):
	link = _live(token)
	if link.reference_doctype != doctype:
		raise frappe.PermissionError
	if link.used_on:
		frappe.throw(_("This link has been answered already."))
	by = (by or "").strip()[:140]
	if not by:
		frappe.throw(_("Write your name, so we know who answered."))
	return (
		link,
		frappe.get_doc(doctype, link.reference_name),
		_("{0} ({1}), through a link").format(by, link.email),
	)


def _answered(link, by: str) -> None:
	link.db_set({"used_on": now_datetime(), "used_by": by.strip()[:140]}, update_modified=False)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def link_accept(token: str, wanted: str, reference: str | None = None, by: str | None = None) -> str:
	"""A quotation accepted through its link (one/portal.py `accept`)."""
	link, doc, said = _answering(token, "Quotation", by)
	if not portal._answerable(doc):
		frappe.throw(_("This quotation can no longer be answered."))
	order = portal.accept(doc, wanted, reference, "Guest", link.contact, said)
	_answered(link, by)
	return order


@frappe.whitelist(allow_guest=True, methods=["POST"])
def link_decline(token: str, reason: str | None = None, by: str | None = None) -> None:
	"""A quotation declined through its link (one/portal.py `decline`)."""
	link, doc, said = _answering(token, "Quotation", by)
	if not portal._answerable(doc):
		frappe.throw(_("This quotation can no longer be answered."))
	portal.decline(doc, reason, "Guest", said)
	_answered(link, by)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def link_preview(token: str, rows: str | dict) -> dict:
	"""What a quote priced through its link comes to (one/portal.py `reckon`)."""
	link = _live(token)
	if link.reference_doctype != "Request for Quotation":
		raise frappe.PermissionError
	quote_, _doc, _supplier, user = portal._quote(link.reference_name, rows, sending=False, link=link)
	return portal.reckon(quote_, user)


@frappe.whitelist(allow_guest=True, methods=["POST"])
def link_send(token: str, rows: str | dict, notes: str | None = None, by: str | None = None) -> str:
	"""A quote sent through its link, as the link's supplier's (one/portal.py
	`send`)."""
	link, _doc, said = _answering(token, "Request for Quotation", by)
	sent = portal.send(*portal._quote(link.reference_name, rows, notes, link=link))
	frappe.get_doc("Supplier Quotation", sent).add_comment("Info", _("Sent by {0}.").format(said))
	_answered(link, by)
	return sent


@frappe.whitelist(allow_guest=True, methods=["GET"])
def link_pdf(token: str) -> None:
	"""The record's printed copy, through its link."""
	from frappe.utils.print_format import download_pdf

	link = _live(token)
	frappe.flags.ignore_print_permissions = True
	download_pdf(link.reference_doctype, link.reference_name, _print_format(link.reference_doctype))
