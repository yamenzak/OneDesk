"""What OneAI may tell the sender of a message about the workspace's records:
what the portal shows that person (one/portal.py), and only when the
receiving server confirmed the sender's address (`verified`), since a From
line is free to write. Used by a rule's OneAI reply (rules._drafted)."""

import re
from typing import Annotated

import frappe

PARTY = {
	"Quotation": "party_name",
	"Sales Order": "customer",
	"Sales Invoice": "customer",
	"Delivery Note": "customer",
	"Supplier Quotation": "supplier",
	"Purchase Order": "supplier",
	"Purchase Invoice": "supplier",
}

DIGEST = 10

MOST = 50

OPEN = {
	"Quotation": {"status": ("in", ("Open", "Replied", "Partially Ordered"))},
	"Sales Order": {"status": ("not in", ("Completed", "Closed", "Cancelled"))},
	"Sales Invoice": {"outstanding_amount": (">", 0)},
	"Delivery Note": {"status": ("not in", ("Completed", "Closed", "Cancelled", "Return Issued"))},
	"Supplier Quotation": {"status": ("in", ("Submitted",))},
	"Purchase Order": {"status": ("not in", ("Completed", "Closed", "Cancelled"))},
	"Purchase Invoice": {"outstanding_amount": (">", 0)},
}

NAMED = re.compile(r"\b[A-Z][A-Z0-9]*(?:[-/.][A-Z0-9]+)+\b")


def verified(headers, sender: str) -> bool:
	"""Whether the server that received a message confirmed its sender: the
	topmost Authentication-Results (or ARC-Authentication-Results), which is
	that server's own since each server adds above what it got, says DMARC
	passed, or DKIM or SPF passed for the sender's own domain. A DMARC fail
	is a fail whatever else passed. Pure."""
	domain = (sender or "").rsplit("@", 1)[-1].strip().lower()
	if not domain or headers is None:
		return False
	said = next(
		(str(value) for name, value in headers.items() if name.lower() in ("authentication-results", "arc-authentication-results")),
		None,
	)
	if not said:
		return False
	results = _results(said)
	if any(method == "dmarc" and result == "fail" for method, result, _ in results):
		return False
	for method, result, props in results:
		if result != "pass":
			continue
		if method == "dmarc" and _aligned(props.get("header.from") or domain, domain):
			return True
		if method == "dkim" and _aligned(props.get("header.d") or props.get("header.i", "").lstrip("@").rsplit("@", 1)[-1], domain):
			return True
		if method == "spf" and _aligned((props.get("smtp.mailfrom") or "").rsplit("@", 1)[-1], domain):
			return True
	return False


def _results(said: str) -> list[tuple[str, str, dict]]:
	"""An Authentication-Results value as (method, result, properties), the
	server's name before the first semicolon left out. Pure."""
	said = re.sub(r"\([^)]*\)", " ", said)
	found = []
	for part in said.split(";")[1:]:
		words = part.split()
		if not words or "=" not in words[0]:
			continue
		method, result = words[0].lower().split("=", 1)
		props = dict(one.lower().split("=", 1) for one in words[1:] if "=" in one)
		found.append((method, result, props))
	return found


def _aligned(found: str, domain: str) -> bool:
	"""Relaxed alignment: one domain is the other or under it. Pure."""
	found = (found or "").strip().strip(".").lower()
	return bool(found) and (found == domain or domain.endswith("." + found) or found.endswith("." + domain))


def parties_of(sender: str) -> list[tuple[str, str, str]]:
	"""(party type, party, contact) for each customer or supplier the
	sender's address is a contact of."""
	contacts = frappe.get_all("Contact Email", filters={"email_id": (sender or "").strip().lower()}, pluck="parent")
	if not contacts:
		return []
	links = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "parent": ("in", contacts), "link_doctype": ("in", ("Customer", "Supplier"))},
		fields=["link_doctype", "link_name", "parent"],
	)
	return list(dict.fromkeys((one.link_doctype, one.link_name, one.parent) for one in links))


def shown_kinds() -> set[str]:
	"""The records the portal lists at all (Portal Settings)."""
	settings = frappe.get_cached_doc("Portal Settings")
	return {
		one.reference_doctype
		for one in (settings.get("menu") or []) + (settings.get("custom_menu") or [])
		if one.enabled and one.reference_doctype in PARTY
	}


def _scope(doctype: str, filters: dict | None, contact_of: dict) -> list:
	"""(doctype, party filter) pairs a sender may see: the portal's kinds, on
	the side (customer or supplier) of each party they are a contact of."""
	pairs = []
	for party_type, party in contact_of:
		for kind, field in PARTY.items():
			if (doctype and kind != doctype) or kind not in shown_kinds():
				continue
			if (party_type == "Customer") != (field != "supplier"):
				continue
			said = {field: party, "docstatus": 1, **(filters or {})}
			if kind == "Quotation":
				said["quotation_to"] = "Customer"
			pairs.append((kind, party, said))
	return pairs


def _rows(sender: str, doctype: str | None = None, filters: dict | None = None, limit: int = MOST, text: str = "") -> list[dict]:
	"""The portal's rows of the sender's records, newest first, a record
	hidden from their contact left out (portal.mine): what is still open
	(OPEN), the latest of the rest, and any `text` names."""
	from onedesk.one import portal

	contacts = {(t, p): c for t, p, c in parties_of(sender)}
	named = set(NAMED.findall(text or ""))
	said = []
	for kind, party, where in _scope(doctype, filters, contacts):
		names = frappe.get_all(kind, filters={**where, **OPEN.get(kind, {})}, pluck="name", order_by="modified desc", limit=limit)
		names += frappe.get_all(kind, filters=where, pluck="name", order_by="modified desc", limit=limit)
		if named:
			names += frappe.get_all(kind, filters={**where, "name": ("in", list(named))}, pluck="name")
		for name in dict.fromkeys(names):
			doc = frappe.get_doc(kind, name)
			if contacts[(_party_type(kind), party)] in portal._hidden(kind, doc):
				continue
			row = portal._row("", kind, doc)
			if kind in portal.OWED and 0 < (doc.get("outstanding_amount") or 0) < (doc.get("grand_total") or 0):
				row["owed"] = doc.get_formatted("outstanding_amount")
			said.append({"party": party, "doctype": kind, **row})
	return said


def _party_type(doctype: str) -> str:
	return "Supplier" if PARTY[doctype] == "supplier" else "Customer"


def records(sender: str, text: str = "") -> list[dict]:
	"""Everything the portal shows the sender, as its rows: for each customer
	or supplier they are a contact of, every record still open and the latest
	DIGEST of the rest of each kind, and any the message names."""
	return _rows(sender, limit=DIGEST, text=text)


def _line(row: dict) -> str:
	"""One record, short: what OneAI is handed for each of them."""
	return " · ".join(
		one
		for one in (
			row["name"],
			row.get("date"),
			row.get("status"),
			row.get("figure"),
			f"{row['owed']} to pay" if row.get("owed") else "",
			(row.get("when") or {}).get("text"),
			row.get("item") + (f" +{row['others']}" if row.get("others") else "") if row.get("item") else "",
		)
		if one
	)


def digest(rows: list[dict]) -> str:
	"""The sender's records, grouped by whom they are for and by kind, a line
	each."""
	out, last = [], None
	for row in rows:
		if (row["party"], row["doctype"]) != last:
			if not last or last[0] != row["party"]:
				out.append(f"{row['party']}:")
			out.append(f"  {row['doctype']}:")
			last = (row["party"], row["doctype"])
		out.append(f"    {_line(row)}")
	return "\n".join(out)


def _sender() -> str:
	said = frappe.flags.get("one_mail_sender")
	if not said:
		frappe.throw("This is only for a reply to a verified sender.")
	return said


def their_records(
	doctype: Annotated[str, "One of: " + ", ".join(PARTY) + "."],
	status: Annotated[str, "Only those in this state, as the list says it, such as Overdue or To Deliver."] | None = None,
	limit: Annotated[int, "At most this many, newest first."] = 50,
) -> list[dict]:
	"""More of the sender's own records of one kind than the list you were
	given: older ones, or all in one state. Only what the sender sees on the
	workspace's portal."""
	if doctype not in PARTY:
		frappe.throw(f"Only these: {', '.join(PARTY)}.")
	rows = _rows(_sender(), doctype=doctype, limit=min(int(limit or 50), 200))
	return [_line(row) for row in rows if not status or (row.get("status") or "").lower() == status.lower()]


def their_record(
	doctype: Annotated[str, "One of: " + ", ".join(PARTY) + "."],
	name: Annotated[str, "Its id, as the list says it."],
) -> dict:
	"""One of the sender's own records in full, as their portal page shows
	it: its state, its steps (ordered, delivered, invoiced, paid), its
	facts, its items with quantities and prices, and its totals and what is
	left to pay."""
	from onedesk.one import portal

	sender = _sender()
	contacts = {(t, p): c for t, p, c in parties_of(sender)}
	doc = frappe.get_doc(doctype, name) if doctype in PARTY and frappe.db.exists(doctype, name) else None
	key = (_party_type(doctype), doc.get(PARTY[doctype])) if doc else None
	if not doc or doc.docstatus != 1 or key not in contacts or doctype not in shown_kinds():
		frappe.throw("That is not one of the sender's records.")
	if contacts[key] in portal._hidden(doctype, doc):
		frappe.throw("That is not one of the sender's records.")
	said = portal._record(doctype, frappe._dict(doc=doc, print_format="Standard"), pdf="-")
	return {key: said[key] for key in ("name", "status", "summary", "steps", "facts", "items", "totals")}


TOOLS = (their_records, their_record)


def told(comm) -> str:
	"""The part of OneAI's question that says what it may tell the sender."""
	if not comm.get("one_verified"):
		return (
			"The sender's address could not be confirmed, so say nothing about any order, invoice, "
			"delivery or other record, and invent none."
		)
	rows = records(comm.sender, f"{comm.subject or ''}\n{frappe.utils.strip_html_tags(comm.content or '')}")
	if not rows:
		return "Nothing is known about this sender's records. Say nothing about orders, invoices or deliveries, and invent none."
	return (
		"These are the sender's own records, as the workspace's portal shows them: everything still open, "
		"and the latest of the rest. Work out which ones the message is about, even when it names none, "
		"and mention only those: not an overdue invoice when they asked about a delivery. To see one in "
		"full (its items, prices, steps and what is left to pay) call their_record; for older ones, "
		"their_records. Say nothing else about the workspace's records, and invent no number, date or "
		"amount.\n" + digest(rows)
	)
