"""What OneAI may tell the sender of a message about the workspace's records:
what the portal shows that person (one/portal.py), and only when the
receiving server confirmed the sender's address (`verified`), since a From
line is free to write. Used by a rule's OneAI reply (rules._drafted)."""

import re

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

RECENT = 5

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


def records(sender: str, text: str = "") -> list[dict]:
	"""What the portal shows the sender, as the portal's rows, leaving out a
	record hidden from that contact (portal.mine): the records the message
	names when it names any of theirs, and otherwise, for each customer or
	supplier they are a contact of, the latest few of each kind the portal
	lists."""
	kinds = shown_kinds()
	named = set(NAMED.findall(text or ""))
	said = _of(sender, kinds, named, only_named=bool(named))
	return said or (_of(sender, kinds, named, only_named=False) if named else said)


def _of(sender: str, kinds: set, named: set, only_named: bool) -> list[dict]:
	"""`records` for one choice: only the named ones, or the latest too."""
	from onedesk.one import portal

	said = []
	for party_type, party, contact in parties_of(sender):
		for doctype, field in PARTY.items():
			if doctype not in kinds or (party_type == "Customer") != (field != "supplier"):
				continue
			filters = {field: party, "docstatus": 1}
			if doctype == "Quotation":
				filters["quotation_to"] = "Customer"
			names = (
				[]
				if only_named
				else frappe.get_all(doctype, filters=filters, pluck="name", order_by="modified desc", limit=RECENT)
			)
			if named:
				names += frappe.get_all(doctype, filters={**filters, "name": ("in", list(named))}, pluck="name")
			for name in dict.fromkeys(names):
				doc = frappe.get_doc(doctype, name)
				if contact in portal._hidden(doctype, doc):
					continue
				row = portal._row("", doctype, doc)
				if doctype in portal.OWED and 0 < (doc.get("outstanding_amount") or 0) < (doc.get("grand_total") or 0):
					row["owed"] = doc.get_formatted("outstanding_amount")
				said.append({"party": party, "doctype": doctype, **row})
	return said


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
	lines = [
		" · ".join(
			one
			for one in (
				f"{row['doctype']} {row['name']} for {row['party']}",
				row.get("date"),
				row.get("status"),
				row.get("figure"),
				f"{row['owed']} still to pay" if row.get("owed") else "",
				(row.get("when") or {}).get("text"),
				row.get("item") + (f" and {row['others']} more" if row.get("others") else "") if row.get("item") else "",
			)
			if one
		)
		for row in rows
	]
	return (
		"These are the sender's own records, as the workspace's portal shows them. Mention only the ones "
		"the message asks about, and bring up no other: not an overdue invoice when they asked about a "
		"delivery. Say nothing else about the workspace's records, and invent no number, date or amount.\n"
		+ "\n".join(f"- {one}" for one in lines)
	)
