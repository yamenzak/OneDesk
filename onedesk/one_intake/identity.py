"""Who is who: every identifier a record carries, and the record an identifier
belongs to.

Frappe, ERPNext and HRMS hold identity in a dozen places: a Contact's emails
and phones, a Supplier's tax id and website, an Employee's passport, a Bank
Account's IBAN, an Address's email. Going from an identifier to its record
was a query per field per doctype. The Identifier table is that in one
place, kept up on every save, so "who is DE123456789?" is one lookup.

Rows are Dynamic Links to their record, so Frappe's rename and merge carry
them along (`rename_dynamic_links`). There is no unique index for the same
reason: a merge would trip it half way. `renamed` tidies the doubles after.
"""

import frappe
from frappe import _

from onedesk.one_intake import identifiers as ids

#: How much one matching identifier says, alone. Two together say more.
WEIGHT = {
	ids.IBAN: 0.99,
	ids.VAT: 0.99,
	ids.TAX: 0.95,
	ids.REGISTER: 0.95,
	ids.DOCUMENT: 0.95,
	ids.EMAIL: 0.9,
	ids.PHONE: 0.75,
	ids.DOMAIN: 0.6,
}

#: A match this sure, this far ahead of the next, is taken as certain.
CERTAIN, AHEAD = 0.9, 0.2

#: Where each record keeps what says who it is: (kind, field) on the record,
#: and (kind, table, field) in a child table.
FIELDS = {
	"Contact": [(ids.EMAIL, "email_ids", "email_id"), (ids.PHONE, "phone_nos", "phone")],
	"Customer": [("Tax ID", "tax_id"), (ids.WEBSITE, "website"), (ids.EMAIL, "email_id"), (ids.PHONE, "mobile_no")],
	"Supplier": [("Tax ID", "tax_id"), (ids.WEBSITE, "website"), (ids.EMAIL, "email_id"), (ids.PHONE, "mobile_no")],
	"Lead": [
		(ids.EMAIL, "email_id"),
		(ids.PHONE, "phone"),
		(ids.PHONE, "mobile_no"),
		(ids.PHONE, "whatsapp_no"),
		(ids.WEBSITE, "website"),
	],
	"Prospect": [(ids.WEBSITE, "website")],
	"Employee": [
		(ids.EMAIL, "personal_email"),
		(ids.EMAIL, "company_email"),
		(ids.PHONE, "cell_number"),
		(ids.IBAN, "iban"),
		(ids.IBAN, "bank_ac_no"),
		(ids.DOCUMENT, "passport_number"),
		(ids.DOCUMENT, "one_documents", "number"),
	],
	"Job Applicant": [(ids.EMAIL, "email_id"), (ids.PHONE, "phone_number")],
	"Company": [("Tax ID", "tax_id"), (ids.EMAIL, "email"), (ids.PHONE, "phone_no"), (ids.WEBSITE, "website")],
	"Bank Account": [(ids.IBAN, "iban"), (ids.IBAN, "bank_account_no")],
	"Address": [(ids.EMAIL, "email_id"), (ids.PHONE, "phone")],
}

#: What a record's identifiers belong to when it is not itself somebody:
#: a Bank Account's IBAN is its party's, an Address's email its parties'.
ELSEWHERE = ("Bank Account", "Address")

#: Records flagged when they arrive holding what another of their kind holds.
FLAGGED = ("Contact", "Customer", "Supplier")


def country() -> str:
	"""The workspace's country, as two letters, for reading national numbers."""
	code = frappe.db.get_value("Country", frappe.db.get_default("country"), "code") if frappe.db.get_default("country") else None
	return (code or "de").upper()


def said(doc) -> list[tuple[str, str]]:
	"""The (kind, raw value) pairs a record carries."""
	out = []
	meta = frappe.get_meta(doc.doctype)
	for spec in FIELDS.get(doc.doctype, []):
		if len(spec) == 3:
			kind, table, field = spec
			if meta.has_field(table):
				out += [(kind, row.get(field)) for row in doc.get(table) or []]
		else:
			kind, field = spec
			if meta.has_field(field):
				out.append((kind, doc.get(field)))
	return [(kind, raw) for kind, raw in out if raw]


def owners(doc) -> list[tuple[str, str]]:
	"""Whose identifiers these are."""
	if doc.doctype == "Bank Account":
		if doc.get("is_company_account") and doc.get("company"):
			return [("Company", doc.company)]
		return [(doc.party_type, doc.party)] if doc.get("party_type") and doc.get("party") else []
	if doc.doctype == "Address":
		return [(row.link_doctype, row.link_name) for row in doc.get("links") or [] if row.link_doctype and row.link_name]
	return [(doc.doctype, doc.name)]


def origin_of(doctype: str, name: str) -> str:
	return f"{doctype}/{name}"


# ------------------------------------------------------------------ keeping it up


def remember(doc, method=None) -> None:
	"""on_update of every doctype in FIELDS: its identifiers, as they are now."""
	if doc.doctype not in FIELDS or frappe.flags.in_install:
		return
	origin = origin_of(doc.doctype, doc.name)
	frappe.db.delete("Identifier", {"origin": origin})
	pairs = ids.found(said(doc), country())
	for doctype, name in owners(doc):
		for kind, value in pairs:
			_add(kind, value, doctype, name, origin)


def _add(kind: str, value: str, doctype: str, name: str, origin: str) -> None:
	frappe.get_doc(
		{"doctype": "Identifier", "kind": kind, "value": value, "for_doctype": doctype, "for_name": name, "origin": origin}
	).insert(ignore_permissions=True, ignore_links=True)


def learn(kind: str, raw: str, doctype: str, name: str, origin: str) -> str | None:
	"""Keep an identifier a document taught us about a record. Returns the
	canonical value, or None when it was not a valid one of its kind."""
	value = ids.canonical(kind, raw, country())
	if value and not frappe.db.exists("Identifier", {"kind": kind, "value": value, "for_doctype": doctype, "for_name": name}):
		_add(kind, value, doctype, name, origin)
	return value


def forget(doc, method=None) -> None:
	"""on_trash: what it said, and what was known about it."""
	if doc.doctype not in FIELDS:
		return
	frappe.db.delete("Identifier", {"origin": origin_of(doc.doctype, doc.name)})
	frappe.db.delete("Identifier", {"for_doctype": doc.doctype, "for_name": doc.name})


def renamed(doc, method=None, old=None, new=None, merge=False) -> None:
	"""after_rename: Frappe moved the rows that name the record; the rows it
	told us itself are moved here, and the doubles a merge makes are folded."""
	if doc.doctype not in FIELDS:
		return
	frappe.db.set_value("Identifier", {"origin": origin_of(doc.doctype, old)}, "origin", origin_of(doc.doctype, new))
	seen = set()
	for row in frappe.get_all(
		"Identifier",
		filters={"for_doctype": doc.doctype, "for_name": new},
		fields=["name", "kind", "value"],
		order_by="creation asc",
	):
		if (row.kind, row.value) in seen:
			frappe.db.delete("Identifier", row.name)
		seen.add((row.kind, row.value))


def remember_all() -> None:
	"""Every record's identifiers, once: run in the background by a patch,
	and safe to run again."""
	for doctype in FIELDS:
		if not frappe.db.table_exists(doctype):
			continue
		for name in frappe.get_all(doctype, pluck="name", limit=20000):
			try:
				remember(frappe.get_doc(doctype, name))
			except Exception:
				frappe.log_error(title=f"Intake could not read who {doctype} {name} is")
		frappe.db.commit()


# ------------------------------------------------------------------ asking


def holders(kind: str, value: str) -> list[tuple[str, str]]:
	rows = frappe.get_all("Identifier", filters={"kind": kind, "value": value}, fields=["for_doctype", "for_name"])
	return list(dict.fromkeys((row.for_doctype, row.for_name) for row in rows))


def who(raw: str) -> list[dict]:
	"""Whatever the value is (an email, an IBAN, a VAT id, a phone number),
	the records that hold it."""
	out = []
	for kind in ids.KINDS:
		value = ids.canonical(kind, raw, country())
		if value:
			out += [{"kind": kind, "value": value, "doctype": d, "name": n} for d, n in holders(kind, value)]
	return out


def entities(doctype: str, name: str) -> list[tuple[str, str]]:
	"""What a holder stands for: a Contact stands for the parties it is linked
	to, and for itself when it is linked to none."""
	if doctype != "Contact":
		return [(doctype, name)]
	links = frappe.get_all(
		"Dynamic Link",
		filters={"parenttype": "Contact", "parent": name},
		fields=["link_doctype", "link_name"],
	)
	return [(one.link_doctype, one.link_name) for one in links] or [(doctype, name)]


def match(pairs: list[tuple[str, str]]) -> list[dict]:
	"""The records these canonical identifiers point at, surest first, each
	with what it was matched on. A value held by several entities says less
	about each, and a strong one held by several says it is ambiguous."""
	scores: dict[tuple, dict] = {}
	for kind, value in pairs:
		found = {entity for holder in holders(kind, value) for entity in entities(*holder)}
		if not found:
			continue
		weight = WEIGHT.get(kind, 0.5) / (1 if len(found) == 1 else len(found) + 1)
		for entity in found:
			held = scores.setdefault(entity, {"doctype": entity[0], "name": entity[1], "score": 0.0, "on": []})
			held["score"] = 1 - (1 - held["score"]) * (1 - weight)
			held["on"].append(kind)
	return sorted(scores.values(), key=lambda one: one["score"], reverse=True)


def certain(found: list[dict]) -> dict | None:
	"""The one match sure enough to act on without asking, if there is one."""
	if not found or found[0]["score"] < CERTAIN:
		return None
	if len(found) > 1 and found[0]["score"] - found[1]["score"] < AHEAD:
		return None
	return found[0]


def ours(pairs: list[tuple[str, str]]) -> str | None:
	"""Whether these identifiers are the workspace's own ("company") or a
	colleague's ("colleague"): our own name is on every letter we receive,
	and must never become a supplier."""
	for kind, value in pairs:
		held = holders(kind, value)
		if any(doctype == "Company" for doctype, _name in held):
			return "company"
		if kind == ids.EMAIL:
			if frappe.db.exists("Email Account", {"email_id": value}):
				return "company"
			if frappe.db.get_value("User", {"name": value, "user_type": "System User", "enabled": 1}):
				return "colleague"
		if kind == ids.DOMAIN and value in _our_domains():
			return "company"
	return None


def _our_domains() -> set[str]:
	"""The domains of the workspace's own mailboxes, leaving out mail
	providers and the shared mail domain every workspace has an address on."""
	shared = frappe.conf.get("one_mail_domain")
	found = {ids.organisation_domain(one) for one in frappe.get_all("Email Account", pluck="email_id") if one}
	return {one for one in found if one and one != shared}


# ------------------------------------------------------------------ duplicates


def flag(doc, method=None) -> None:
	"""after_insert of a Contact, Customer or Supplier: one holding an email or
	a strong identifier another of its kind already holds is marked as a
	possible duplicate, with Merge beside it, the way OneCRM marks a Lead."""
	if doc.doctype not in FLAGGED or not doc.meta.has_field("one_duplicate_of"):
		return
	for kind, value in ids.found(said(doc), country()):
		if kind not in ids.STRONG and kind != ids.EMAIL:
			continue
		for doctype, name in holders(kind, value):
			if doctype == doc.doctype and name != doc.name:
				doc.db_set({"one_duplicate_type": doctype, "one_duplicate_of": name, "one_duplicate_on": kind}, update_modified=False)
				return


def fold(doctype: str, name: str, into: str) -> str:
	"""Merge one record into another with Frappe's own rename, after filling
	every field the kept one has empty from the other: a merge moves links,
	not values, and the kept record's own values are never overwritten."""
	gone, kept = frappe.get_doc(doctype, name), frappe.get_doc(doctype, into)
	changed = False
	for df in kept.meta.fields:
		if df.fieldtype in frappe.model.no_value_fields or df.fieldtype in frappe.model.table_fields:
			continue
		if df.fieldname.startswith("one_duplicate") or df.no_copy or df.read_only:
			continue
		if not kept.get(df.fieldname) and gone.get(df.fieldname):
			kept.set(df.fieldname, gone.get(df.fieldname))
			changed = True
	if changed:
		kept.save()
	frappe.rename_doc(doctype, name, into, merge=True)
	return into


@frappe.whitelist(methods=["POST"])
def merge(doctype: str, name: str, into: str) -> str:
	"""Merge a possible duplicate into the record it duplicates."""
	if doctype not in FLAGGED:
		frappe.throw(_("Only a contact, a customer or a supplier is merged here."))
	if name == into:
		frappe.throw(_("A record cannot be merged into itself."))
	for one in (name, into):
		frappe.get_doc(doctype, one).check_permission("write")
	frappe.get_doc(doctype, name).check_permission("delete")
	return fold(doctype, name, into)


@frappe.whitelist(methods=["POST"])
def not_duplicate(doctype: str, name: str) -> None:
	if doctype not in FLAGGED:
		frappe.throw(_("Only a contact, a customer or a supplier is marked here."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	doc.db_set({"one_duplicate_type": None, "one_duplicate_of": None, "one_duplicate_on": None})
