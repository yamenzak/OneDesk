"""The Intake panel: what OneAI read in a file or a message, beside it.

Asked for by OneCloud's preview and OneMail's reading pane. It answers only
somebody who may open the file or the message itself, and a party is shown
as a link only to somebody who may open that record.
"""

import hashlib
import json

import frappe
from frappe import _

from onedesk.one_storage import namespace as ns

FACTS = ("number", "issued_on", "gross", "paid_how", "iban", "payment_reference", "valid_until", "document_type", "issuing_country")


@frappe.whitelist()
def for_file(name: str) -> dict | None:
	item = ns.row(name)
	if not item or item.get("is_folder") or not ns.may(item):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	key, own = frappe.db.get_value("File", name, ["content_hash", "one_reading"])
	held = own or (frappe.db.get_value("Reading", {"key": key}, "name") if key else None)
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
		"name": doc.name,
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
	out["actions"] = actions_of(name)
	out["may_decide"] = _may_decide(doc)
	out["matter"] = matter_of(doc)
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


# ------------------------------------------------------------------ what OneAI did


def actions_of(reading: str) -> list[dict]:
	"""What OneAI did or proposes with a document and its parts, as the
	reader may know it: a record they may not open is named by its type only."""
	names = [reading, *frappe.get_all("Reading", filters={"part_of": reading}, pluck="name")]
	rows = frappe.get_all(
		"Intake Action",
		filters={"reading": ["in", names], "level": ["in", ("Done", "Proposed", "Refused")]},
		fields=["name", "kind", "level", "target_doctype", "target_name", "why", "after", "before"],
		order_by="creation asc",
	)
	out = []
	for row in rows:
		if row.kind == "Create" and row.target_doctype == "File" and row.level == "Done":
			continue
		said = said_of(row)
		if said:
			out.append({"name": row.name, "level": row.level, "said": said, "change": change_of(row), "why": row.why, "record": _record(row)})
	return out


def said_of(row) -> str:
	after = json.loads(row.after or "{}")
	record = f"{_(row.target_doctype)} {row.target_name or ''}".strip()
	if row.kind == "Create":
		return _("Make {0}").format(_(row.target_doctype)) if row.level == "Proposed" else _("Made {0}").format(record)
	if row.kind == "Update":
		if row.level == "Proposed":
			return _("Change {0}").format(record) if change_of(row) else _("Fill in {0}").format(record)
		return _("Changed {0}").format(record) if change_of(row) else _("Filled in {0}").format(record)
	if row.kind == "Add":
		return _("Add to {0}").format(record) if row.level == "Proposed" else _("Added to {0}").format(record)
	if row.kind == "Link":
		return _("Linked to {0}").format(record)
	if row.kind == "Attach":
		return _("Filed with {0}").format(record)
	if row.kind == "Rename":
		return _("Named it {0}").format(after.get("file_name") or "")
	if row.kind == "Move":
		if row.target_doctype == "File":
			return _("Moved it to {0}").format(" / ".join(_folder_path(after.get("folder"))))
		return _("Moved it to {0}").format(frappe.db.get_value("Mail Folder", after.get("mail_folder"), "label") or "")
	if row.kind == "Tag":
		return _("Tagged it {0}").format(", ".join(after.get("tags") or [])) if after.get("tags") else ""
	if row.kind == "Comment":
		return _("Commented on {0}").format(record)
	return ""


def change_of(row) -> list[dict]:
	"""What a proposed change would write over, field by field."""
	if row.kind != "Update":
		return []
	before, after = json.loads(row.before or "{}"), json.loads(row.after or "{}")
	meta = frappe.get_meta(row.target_doctype)
	return [
		{"field": _(meta.get_label(key)), "from": before.get(key), "to": value}
		for key, value in after.items()
		if key != "name" and before.get(key) not in (None, "") and str(before.get(key)) != str(value)
	]


def _record(row) -> list | None:
	if row.target_doctype in ("File", "Communication") or not row.target_name:
		return None
	if frappe.db.exists(row.target_doctype, row.target_name) and frappe.has_permission(row.target_doctype, "read", row.target_name):
		return [row.target_doctype, row.target_name]
	return None


def _folder_path(folder: str | None) -> list[str]:
	from onedesk.one_storage import namespace as ns

	chain = ns.chain(folder)[:2] if folder else []
	return [frappe.db.get_value("File", at, "file_name") for at in reversed(chain)]


def matter_of(doc) -> dict | None:
	"""The matter a later document belongs to, and what it changes there."""
	if not doc.get("matter") or doc.matter == doc.name:
		return None
	head = frappe.db.get_value("Reading", doc.matter, ["name", "title", "kind", "number"], as_dict=True)
	if not head:
		return None
	return {
		"title": head.title or head.number or head.kind,
		"document": document_of(head.name),
		"change": _(doc.change) if doc.change else None,
		"copy": bool(doc.copy_of),
	}


def _may_decide(doc) -> bool:
	from onedesk.one.roles import administers

	return bool(doc.on_behalf_of) and (frappe.session.user == doc.on_behalf_of or administers())


def document_of(reading: str) -> dict | None:
	"""The document a record was made from, for its banner."""
	from onedesk.one_intake import search

	doc = frappe.db.get_value("Reading", reading, ["name", "title", "source_doctype", "source_name", "part_of"], as_dict=True)
	if not doc:
		return None
	own = frappe.db.get_value("File", {"one_reading": reading}, ["name", "file_name", "folder", "attached_to_doctype", "attached_to_name"], as_dict=True)
	if own:
		return {"label": own.file_name, "route": search._file_route(own)}
	if doc.source_doctype == "File":
		file = frappe.db.get_value("File", doc.source_name, ["name", "file_name", "folder", "attached_to_doctype", "attached_to_name"], as_dict=True)
		if file:
			if file.attached_to_doctype == "Communication":
				return _message(file.attached_to_name, file.file_name)
			return {"label": file.file_name, "route": search._file_route(file)}
	if doc.source_doctype == "Communication":
		return _message(doc.source_name, doc.title)
	return {"label": doc.title, "route": None}


def _message(name: str, label: str) -> dict:
	thread, account = frappe.db.get_value("Communication", name, ["one_thread", "email_account"]) or (None, None)
	return {"label": label, "route": f"/app/onemail?box={account}&thread={thread or name}"}
