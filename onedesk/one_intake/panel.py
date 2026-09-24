"""The Intake panel: what OneAI read in a file or a message, beside it.

Asked for by OneCloud's preview and OneMail's reading pane. It answers only
somebody who may open the file or the message itself, and a party is shown
as a link only to somebody who may open that record.
"""

import hashlib

import frappe
from frappe import _

from onedesk.one_storage import namespace as ns

FACTS = ("number", "issued_on", "gross", "paid_how", "iban", "payment_reference", "valid_until", "document_type", "issuing_country")


@frappe.whitelist()
def for_file(name: str) -> dict | None:
	item = ns.row(name)
	if not item or item.get("is_folder") or not ns.may(item):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	key = frappe.db.get_value("File", name, "content_hash")
	held = frappe.db.get_value("Reading", {"key": key}, "name") if key else None
	return described(held) if held else None


@frappe.whitelist()
def for_message(name: str) -> dict | None:
	comm = frappe.get_doc("Communication", name)
	comm.check_permission("read")
	key = "mail-" + hashlib.md5((comm.message_id or comm.name).encode()).hexdigest()
	held = frappe.db.get_value("Reading", {"key": key}, "name")
	if not held:
		return None
	said = described(held)
	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Communication", "attached_to_name": name, "is_folder": 0},
		fields=["file_name", "content_hash"],
	)
	said["attachments"] = [
		{"file": one.file_name, **described(found, brief=True)}
		for one in files
		if one.content_hash and (found := frappe.db.get_value("Reading", {"key": one.content_hash}, "name"))
	]
	return said


def described(name: str, brief: bool = False) -> dict:
	"""A Reading as the panel draws it."""
	doc = frappe.get_doc("Reading", name)
	out = {
		"state": doc.state,
		"verdict": doc.verdict,
		"kind": doc.kind,
		"title": doc.title,
		"summary": doc.summary,
		"unsure": doc.unsure,
		"sensitivity": doc.sensitivity,
		"how": doc.how,
		"read_by_ai": bool(doc.model or doc.understood_on),
	}
	if brief:
		return out
	meta = frappe.get_meta("Reading")
	out["facts"] = [
		{"label": _(meta.get_label(field)), "value": doc.get(field), "field": field, "currency": doc.currency}
		for field in FACTS
		if doc.get(field)
	]
	out["parties"] = [_party(row) for row in doc.parties]
	out["dates"] = [{"date": row.date, "what": _(row.what), "about": row.about, "found": row.found} for row in doc.dates]
	out["asks"] = [{"what": _(row.what), "detail": row.detail, "by": row.by_date} for row in doc.asks]
	out["dropped"] = [line for line in (doc.dropped or "").splitlines() if line]
	out["parts"] = [
		{"part": part.part, **described(part.name, brief=True)}
		for part in frappe.get_all("Reading", filters={"part_of": name}, fields=["name", "part"], order_by="creation")
	]
	return out


def _party(row) -> dict:
	said = {"role": _(row.role), "name": row.party_name or row.email, "ours": row.ours, "score": row.score}
	if row.matched_doctype and row.matched_name and frappe.has_permission(row.matched_doctype, "read", row.matched_name):
		said["record"] = [row.matched_doctype, row.matched_name]
	return said
